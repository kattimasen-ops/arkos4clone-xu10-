#!/usr/bin/env python3
import glob
import os
import subprocess
import sys

SOURCE_ROOT = "es-source"

CUSTOM_MODES = [
    "rainbow_wave", "strobe_party", "color_fade", "battery_status",
    "fire", "police", "disco", "rainbow_chase",
    "solid_gradient", "wave", "rainbow_full"
]
STOCK_MODES = ["static", "rainbow", "breathing"]

def find_binary():
    candidates = []
    for p in glob.glob(os.path.join(SOURCE_ROOT, "**", "*"), recursive=True):
        name = os.path.basename(p).lower()
        if "emulationstation" in name and os.path.isfile(p) and os.access(p, os.X_OK):
            candidates.append(p)
    if not candidates:
        print("[!] Kein ausführbares EmulationStation-Binary gefunden.")
        sys.exit(1)
    return max(candidates, key=os.path.getsize)

def main():
    binary_path = find_binary()
    print(f"[+] Prüfe Binary: {binary_path}")

    out = subprocess.run(["strings", binary_path], capture_output=True, text=True).stdout

    checks = {
        "OTA Update": "OTA Update" in out or "runOtaUpdateScript" in out,
        "update_check.sh": "update_check.sh" in out,
    }
    for mode in CUSTOM_MODES:
        checks[f"LED-Modus: {mode}"] = mode in out

    print("==================================================")
    print("      BINARY STRING VERIFICATION")
    print("==================================================")
    missing = []
    for label, ok in checks.items():
        print(f"  - {label}: {'AVAILABLE' if ok else 'MISSING'}")
        if not ok:
            missing.append(label)

    if missing:
        print(f"[!] {len(missing)} Prüfung(en) fehlgeschlagen.")
        sys.exit(1)

    print("[OK] Alle OTA- und LED-Strings im Binary bestätigt.")

if __name__ == "__main__":
    main()
