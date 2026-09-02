"""
START_EVERYTHING.py
====================
ONE-CLICK LAUNCHER — Starts the entire FINRA AI Fraud Detection Platform
Runs all components in parallel:
  1. Live Order Simulator (CoinGecko real prices → Event Hubs)
  2. Real-Time AI Scoring Engine (3-Model Ensemble → live_feed.jsonl)
  3. Streamlit Dashboard (http://localhost:8501)
  4. Opens browser automatically
"""

import os, sys, time, subprocess, threading, webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║         FINRA AI FRAUD DETECTION PLATFORM v3.0               ║
║         End-to-End Real-Time Live Launch                      ║
╠══════════════════════════════════════════════════════════════╣
║  Architecture:                                                ║
║  CoinGecko → Event Hubs → AI Engine → Dashboard              ║
║                                                               ║
║  Models: XGBoost (60%) + IsoForest (20%) + Autoencoder (20%) ║
║  Latency: < 2ms per order                                     ║
╚══════════════════════════════════════════════════════════════╝
"""
print(BANNER)

processes = []

def run_process(name, cmd, cwd, delay=0):
    if delay:
        time.sleep(delay)
    print(f"[STARTING] {name}...")
    proc = subprocess.Popen(
        cmd, cwd=cwd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace"
    )
    processes.append((name, proc))
    print(f"[OK] {name} started (PID={proc.pid})")
    return proc

def stream_output(name, proc, prefix_color=""):
    """Stream process output to console."""
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  [{name}] {line}")

def open_browser(delay=6):
    time.sleep(delay)
    print("\n  Opening dashboard in browser...")
    webbrowser.open("http://localhost:8501")

print("=" * 65)
print("[STEP 1] Starting Real-Time AI Scoring Engine...")
print("=" * 65)
engine_proc = subprocess.Popen(
    [sys.executable, "realtime_scoring_engine.py"],
    cwd=BASE_DIR,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding="utf-8", errors="replace"
)
processes.append(("Scoring Engine", engine_proc))

# Stream scoring engine output
def stream_engine():
    for line in engine_proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  [ENGINE] {line}")
threading.Thread(target=stream_engine, daemon=True).start()

# Wait for engine to load models
print("  Waiting for models to load (3 seconds)...")
time.sleep(3)

print("\n" + "=" * 65)
print("[STEP 2] Starting Live Order Simulator...")
print("=" * 65)
sim_proc = subprocess.Popen(
    [sys.executable, "live_order_simulator.py"],
    cwd=BASE_DIR,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding="utf-8", errors="replace"
)
processes.append(("Order Simulator", sim_proc))

def stream_sim():
    for line in sim_proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  [SIMULATOR] {line}")
threading.Thread(target=stream_sim, daemon=True).start()

print("\n" + "=" * 65)
print("[STEP 3] Starting Streamlit Dashboard...")
print("=" * 65)

# Kill any existing streamlit
subprocess.run("taskkill /f /im streamlit.exe 2>nul", shell=True, capture_output=True)
time.sleep(1)

dash_proc = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
     "--server.port=8501", "--server.headless=true",
     "--server.fileWatcherType=none",
     "--theme.base=dark"],
    cwd=BASE_DIR,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding="utf-8", errors="replace"
)
processes.append(("Dashboard", dash_proc))

def stream_dash():
    for line in dash_proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  [DASHBOARD] {line}")
threading.Thread(target=stream_dash, daemon=True).start()

# Auto-open browser
threading.Thread(target=open_browser, args=(7,), daemon=True).start()

print("""
╔══════════════════════════════════════════════════════════════╗
║                  ALL SYSTEMS LIVE!                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  DASHBOARD:  http://localhost:8501                            ║
║                                                               ║
║  Real-time feed refreshes every 2 seconds                     ║
║  Navigate to "Live Feed" page for real-time terminal          ║
║                                                               ║
║  Press Ctrl+C to stop all processes                           ║
╚══════════════════════════════════════════════════════════════╝
""")

try:
    while True:
        # Check if any process died unexpectedly
        for name, proc in processes:
            if proc.poll() is not None:
                print(f"\n  [WARN] {name} stopped unexpectedly (code={proc.returncode})")
        time.sleep(5)
except KeyboardInterrupt:
    print("\n\n  Shutting down all processes...")
    for name, proc in processes:
        print(f"  Stopping {name}...")
        proc.terminate()
    print("  All stopped. Goodbye!")
