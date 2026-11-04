#!/usr/bin/env python3
"""The eval inputs in skills/premiere-pro-projects/evals/files/ are exactly what
tools/premiere-pro/build_eval_files.py builds from the steps."""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.exit(subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'tools', 'premiere-pro', 'build_eval_files.py'), '--check']).returncode)
