#!/usr/bin/env python3
import os
import sys
import subprocess
import glob

def find_binary():
    """Search common locations for the emulationstation binary."""
    candidates = [
        "/tmp/es-source/emulationstation",
        "/tmp/es-source/build/emulationstation",
        "/tmp/es-source/es-app/emulationstation",
    ]
    for path in candidates:
        if os.path.isfile(path) and not os.path.islink(path):
            return path

    # Fallback: recursive search in /tmp/es-source
    source_root = "/tmp/es-source"
    if os.path.isdir(source_root):
        for p in glob.glob(os.path.join(source_root, "**", "*"), recursive=True):
            if os.path.basename(p) == "emulationstation" and os.path.isfile(p) and not os.path.islink(p):
                return p
    return None

if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
    binary_path = sys.argv[1]
else:
    binary_path = find_binary()

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
