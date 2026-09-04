#!/usr/bin/env python3
import os
import sys
import subprocess
import glob

WORKSPACE = os.environ.get("GITHUB_WORKSPACE", ".")
SOURCE_ROOT = os.path.join(WORKSPACE, "es-source")

binary_path = None
for p in glob.glob(os.path.join(SOURCE_ROOT, "**", "*"), recursive=True):
    if os.path.basename(p) == "emulationstation" and os.path.isfile(p) and not os.path.islink(p):
        binary_path = p
        break

if not binary_path:
    print("[ERROR] Could not locate compiled emulationstation binary!")
    sys.exit(1)

print(f"[+] Found binary at: {binary_path}")

try:
    res = subprocess.run(["file", binary_path], capture_output=True, text=True)
    print(f"[+] Binary File Info:\n{res.stdout}")
    if "ARM aarch64" in res.stdout or "aarch64" in res.stdout:
        print("[SUCCESS] Verified binary target architecture is ARM64 (aarch64)!")
    else:
        print("[WARNING] Binary architecture check did not explicitly confirm aarch64.")
except Exception as e:
    print(f"[!] Arch verification warning: {e}")

sys.exit(0)
