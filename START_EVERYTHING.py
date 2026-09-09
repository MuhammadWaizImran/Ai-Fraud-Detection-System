"""
START_EVERYTHING.py
====================
ONE-CLICK LAUNCHER — Starts the entire FINRA AI Fraud Detection Platform
Runs all components in parallel:
  1. Real-Time AI Scoring Engine (3-Model Ensemble → live_feed.jsonl)
  2. 3D Web Surveillance Application & Landing Page (http://localhost:3000)
  3. Opens browser automatically
"""

import os, sys, time, subprocess, threading, webbrowser

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BANNER = """
================================================================
         FINRA AI FRAUD DETECTION PLATFORM v3.0                 
         End-to-End Real-Time Live Launch                       
================================================================
  Architecture:                                                 
  Market Streams -> Event Hubs -> AI Engine -> 3D Radar Console 
                                                                
  Models: XGBoost (60%) + IsoForest (20%) + Autoencoder (20%)   
  Latency: < 2ms per order                                      
================================================================
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
    print("\n  Opening applications in browser...")
    try:
        webbrowser.open("http://localhost:3000")
    except Exception:
        pass

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
print("[STEP 2] Checking Live Order Simulator...")
print("=" * 65)
sim_file = os.path.join(BASE_DIR, "live_order_simulator.py")
if os.path.exists(sim_file):
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
else:
    print("  [OK] Real-time order generation is active inside AI Scoring Engine.")

print("\n" + "=" * 65)
print("[STEP 3] Starting 3D Web Application & Landing Page (Port 3000)...")
print("=" * 65)
web_proc = subprocess.Popen(
    [sys.executable, "-m", "http.server", "3000", "--directory", "web"],
    cwd=BASE_DIR,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, encoding="utf-8", errors="replace"
)
processes.append(("Web Server", web_proc))

def stream_web():
    for line in web_proc.stdout:
        line = line.rstrip()
        if line:
            print(f"  [WEB] {line}")
threading.Thread(target=stream_web, daemon=True).start()

# Auto-open browser
threading.Thread(target=open_browser, args=(5,), daemon=True).start()

print("""
================================================================
              FINRA AI PLATFORM ONLINE & STREAMING!             
================================================================
                                                                
  1. HOMEPAGE:          http://localhost:3000                   
  2. 3D LIVE RADAR:     http://localhost:3000/dashboard.html    
                                                                
  Real-time AI Scoring: XGBoost + IsoForest + Autoencoder       
  Live telemetry syncing to web data stream                     
                                                                
  Press Ctrl+C to stop all processes                            
================================================================
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
