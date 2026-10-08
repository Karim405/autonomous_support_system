"""
Unified System Launcher:
Options:
  --ui       Launch the Streamlit Web Application (Customer Portal & Supervisor Dashboard)
  --api      Launch the FastAPI Backend Server
  --test     Run all verification test suites (Phase 1 & End-to-End Workflow)
"""

import sys
import os
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    parser = argparse.ArgumentParser(description="Autonomous Customer Operations Hub Launcher")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit Web App")
    parser.add_argument("--api", action="store_true", help="Launch FastAPI Server")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")

    args = parser.parse_args()

    if args.test:
        print(" Running Test Suites...")
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "tests", "test_phase1.py")])
        subprocess.run([sys.executable, os.path.join(BASE_DIR, "tests", "test_full_workflow.py")])

    elif args.api:
        print(" Starting FastAPI Server on http://127.0.0.1:8000 ...")
        subprocess.run([sys.executable, "-m", "uvicorn", "api.app:app", "--host", "127.0.0.1", "--port", "8000", "--reload"])

    elif args.ui or len(sys.argv) == 1:
        print(" Launching Streamlit Web Portal...")
        ui_path = os.path.join(BASE_DIR, "web_ui", "app_ui.py")
        subprocess.run([sys.executable, "-m", "streamlit", "run", ui_path])

if __name__ == "__main__":
    main()
