#!/usr/bin/env python3
"""Run every test in the repo: tests/check_links.py, then each skill's tests in tests/<name>/.

  python3 -I tests/run_all.py            # everything; exit 1 if anything fails
  python3 -I tests/run_all.py premiere   # only test files whose path contains this
"""
import glob, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    pick = sys.argv[1] if len(sys.argv) > 1 else ''
    files = [os.path.join(HERE, 'check_links.py')] + sorted(glob.glob(os.path.join(HERE, '*', '*.py')))
    files = [f for f in files if pick in os.path.relpath(f, HERE) and not os.path.basename(f).startswith('_')]
    failed = []
    for f in files:
        rel = os.path.relpath(f, os.path.dirname(HERE))
        print(f'== {rel}', flush=True)
        t = time.time()
        r = subprocess.run([sys.executable, '-I', f])
        print(f"   {'ok' if r.returncode == 0 else 'FAILED'} ({time.time() - t:.1f} s)\n", flush=True)
        if r.returncode:
            failed.append(rel)
    print(f"{len(files) - len(failed)}/{len(files)} test files passed" + (': failed ' + ', '.join(failed) if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
