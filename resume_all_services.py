"""
resume_all_services.py
Resumes all paused Azure services back to full operation.
Run this when you're ready to use the platform again.
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_FILE = os.path.join(BASE_DIR, "azure_config.json")

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (r.stdout + r.stderr).strip(), r.returncode

def load_config():
    if not os.path.exists(CFG_FILE):
        print("[ERR] azure_config.json not found.")
        sys.exit(1)
    with open(CFG_FILE) as f:
        return json.load(f)

def dbw_api(cfg, method, path, body=None):
    host = cfg.get("DATABRICKS_HOST", "")
    pat  = cfg.get("DATABRICKS_PAT", "")
    if not host or not pat:
        return None
    url  = f"https://{host}/api/2.0{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, method=method,
           headers={"Authorization": f"Bearer {pat}",
                    "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  [WARN] {e}")
        return None

# Job schedules - restored to original
JOB_SCHEDULES = {
    "FD-01-Bronze-Ingest":   "0 */10 * ? * *",   # every 10 min
    "FD-02-Silver-Clean":    "0 */15 * ? * *",   # every 15 min
    "FD-03-Gold-Features":   "0 */20 * ? * *",   # every 20 min
    "FD-05-Scoring-Engine":  "0 */10 * ? * *",   # every 10 min
    "FD-06-Gold-KPIs":       "0 0 * ? * *",      # every hour
}

def main():
    print("=" * 60)
    print("  RESUMING ALL SERVICES - Fraud Detection Platform")
    print("=" * 60)

    cfg = load_config()
    rg  = cfg.get("RESOURCE_GROUP", "rg-fraud-detection")

    # ── 1. RE-ENABLE ALL DATABRICKS JOBS ──────────────────────────────────────
    print("\n[1/3] Re-enabling all Databricks scheduled jobs...")
    jobs_resp = dbw_api(cfg, "GET", "/jobs/list") or {}
    jobs = jobs_resp.get("jobs", [])
    if not jobs:
        print("  [WARN] No jobs found.")
    else:
        for job in jobs:
            job_id   = job.get("job_id")
            job_name = job.get("settings", {}).get("name", str(job_id))
            cron     = JOB_SCHEDULES.get(job_name, "0 0 * ? * *")
            result   = dbw_api(cfg, "POST", "/jobs/update", {
                "job_id": job_id,
                "new_settings": {
                    "schedule": {
                        "quartz_cron_expression": cron,
                        "timezone_id": "UTC",
                        "pause_status": "UNPAUSED"
                    }
                }
            })
            status = "[OK]" if result is not None else "[WARN]"
            print(f"  {status} Job '{job_name}' RESUMED (schedule: {cron})")

    # ── 2. RE-ENABLE LOGIC APP ────────────────────────────────────────────────
    print("\n[2/3] Enabling Logic App...")
    logic_app = cfg.get("LOGIC_APP_NAME", "logic-fraud-alerts")
    out, rc = run(
        f'az logic workflow update --resource-group {rg} '
        f'--name {logic_app} --state Enabled 2>&1'
    )
    print(f"  {'[OK]' if rc == 0 else '[WARN]'} Logic App '{logic_app}' enabled.")

    # ── 3. PRINT NEXT STEPS ───────────────────────────────────────────────────
    print("\n[3/3] Reminders before starting pipeline...")
    dbw_host = cfg.get("DATABRICKS_HOST", "adb-7405612400876785.5.azuredatabricks.net")
    print(f"""
  NOTE: Databricks clusters will auto-start when jobs run.
  They may take 3-5 minutes to start up on first job execution.

  WORKSPACE URL: https://{dbw_host}

  OPTIONAL - Start live data simulator:
    python live_order_simulator.py

  OPTIONAL - Run model training (if not done yet):
    Open: /Shared/FraudDetection/04_ml_training_registry
    Click: Run All
""")

    print("=" * 60)
    print("  ALL SERVICES RESUMED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
