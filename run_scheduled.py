#!/usr/bin/env python3
"""Backward compatibility wrapper for src.automation.job_executor"""
import sys
from src.automation.job_executor import run_job
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_scheduled.py <job_name>")
        sys.exit(1)
    success = run_job(sys.argv[1])
    sys.exit(0 if success else 1)
