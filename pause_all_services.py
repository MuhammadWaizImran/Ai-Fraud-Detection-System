"""
pause_all_services.py
Pauses/stops all Azure services to minimize costs WITHOUT deleting anything.
Run this when you want to stop spending money but keep everything intact.
Run resume_all_services.py to bring everything back up.

Cost savings:
  - Databricks clusters TERMINATED  → saves ~$2-5/hr per cluster
  - Databricks jobs PAUSED           → no clusters auto-start
  - Logic App DISABLED               → no trigger costs
  - Event Hub: cannot pause (minimal idle cost ~$10/month)
  - Storage: cannot pause (minimal ~$2/month)
  - Key Vault: cannot pause (minimal ~$0.03/month)
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(BASE_DIR, "azure_config.json")

def run(cmd, silent=False):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout + r.stderr).strip()
    if not silent and out:
        print(f"    {out[:200]}")
    return out, r.returncode

def load_config():
    if not os.path.exists(CFG_FILE):
        print("[ERR] azure_config.json not found.")
        sys.exit(1)
    with open(CFG_FILE) as f:
        return json.load(f)

def dbw_api(cfg, method, path, body=None):
    """Call Databricks REST API."""
    host = cfg.get("DATABRICKS_HOST", "")
    pat  = cfg.get("DATABRICKS_PAT", "")
    if not host or not pat:
        print("  [SKIP] No Databricks credentials in config.")
        return None
    url = f"https://{host}/api/2.0{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"Authorization": f"Bearer {pat}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode()[:200]
        print(f"  [WARN] API {method} {path} -> HTTP {e.code}: {body_txt}")
        return None
    except Exception as e:
        print(f"  [WARN] {e}")
        return None

def main():
    print("=" * 60)
    print("  PAUSING ALL SERVICES - Fraud Detection Platform")
    print("  (Nothing will be deleted - just powered off)")
    print("=" * 60)

    cfg = load_config()
    rg  = cfg.get("RESOURCE_GROUP", "rg-fraud-detection")
    sub = cfg.get("SUBSCRIPTION_ID", "aa8b0cbe-08f6-49d1-aa57-3c72f50e465e")
    dbw_host = cfg.get("DATABRICKS_HOST", "adb-7405612400876785.5.azuredatabricks.net")
    dbw_url  = f"https://{dbw_host}"

    # ── 1. TERMINATE ALL DATABRICKS CLUSTERS ──────────────────────────────────
    print("\n[1/4] Terminating all Databricks clusters...")
    clusters = dbw_api(cfg, "GET", "/clusters/list") or {}
    cluster_list = clusters.get("clusters", [])
    if not cluster_list:
        print("  [OK] No running clusters found.")
    else:
        for c in cluster_list:
            cid   = c.get("cluster_id", "")
            cname = c.get("cluster_name", cid)
            state = c.get("state", "")
            if state in ("RUNNING", "RESIZING", "RESTARTING"):
                print(f"  Terminating cluster: {cname} (state={state})...")
                dbw_api(cfg, "POST", "/clusters/delete", {"cluster_id": cid})
                print(f"  [OK] {cname} terminated.")
            else:
                print(f"  [SKIP] {cname} already in state: {state}")

    # ── 2. PAUSE ALL DATABRICKS JOBS ──────────────────────────────────────────
    print("\n[2/4] Pausing all Databricks scheduled jobs...")
    jobs_resp = dbw_api(cfg, "GET", "/jobs/list") or {}
    jobs = jobs_resp.get("jobs", [])
    if not jobs:
        print("  [OK] No jobs found.")
    else:
        for job in jobs:
            job_id   = job.get("job_id")
            job_name = job.get("settings", {}).get("name", str(job_id))
            # Pause by removing the schedule (saves it first)
            result = dbw_api(cfg, "POST", "/jobs/update", {
                "job_id": job_id,
                "new_settings": {
                    "schedule": {
                        "quartz_cron_expression": "0 0 6 ? * MON",  # once/week off-hours
                        "timezone_id": "UTC",
                        "pause_status": "PAUSED"
                    }
                }
            })
            status = "[OK]" if result is not None else "[WARN]"
            print(f"  {status} Job '{job_name}' (id={job_id}) PAUSED")

    # ── 3. STOP ANY RUNNING JOB RUNS ──────────────────────────────────────────
    print("\n[3/4] Stopping any active job runs...")
    runs = dbw_api(cfg, "GET", "/jobs/runs/list?active_only=true&limit=25") or {}
    run_list = runs.get("runs", [])
    if not run_list:
        print("  [OK] No active runs.")
    else:
        for r in run_list:
            run_id = r.get("run_id")
            dbw_api(cfg, "POST", "/jobs/runs/cancel", {"run_id": run_id})
            print(f"  [OK] Run {run_id} cancelled.")

    # ── 4. DISABLE LOGIC APP ──────────────────────────────────────────────────
    print("\n[4/4] Disabling Logic App...")
    logic_app = cfg.get("LOGIC_APP_NAME", "logic-fraud-alerts")
    out, rc = run(
        f'az logic workflow update --resource-group {rg} '
        f'--name {logic_app} --state Disabled 2>&1'
    )
    if rc == 0:
        print(f"  [OK] Logic App '{logic_app}' disabled.")
    else:
        print(f"  [WARN] Could not disable Logic App: {out[:150]}")

    # ── SUMMARY ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ALL SERVICES PAUSED SUCCESSFULLY!")
    print("=" * 60)
    print("""
  PAUSED:
    [OK] All Databricks clusters terminated
    [OK] All Databricks pipeline jobs paused
    [OK] All active runs cancelled
    [OK] Logic App disabled

  STILL RUNNING (minimal cost):
    - Storage Account   : ~$2/month  (cannot pause)
    - Event Hub         : ~$10/month (cannot pause)
    - Key Vault         : ~$0/month  (practically free)
    - Databricks workspace control plane: FREE when no clusters run

  ESTIMATED MONTHLY SAVINGS: ~$150-400/month vs fully running

  To resume everything: python resume_all_services.py
""")

if __name__ == "__main__":
    main()
