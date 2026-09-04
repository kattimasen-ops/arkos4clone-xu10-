#!/usr/bin/env python3
import glob
import os
import subprocess
import sys

SOURCE_ROOT = "es-source"[cite: 2]

CUSTOM_MODES = [
    "rainbow_wave", "strobe_party", "color_fade", "battery_status",
    "fire", "police", "disco", "rainbow_chase",
    "solid_gradient", "wave", "rainbow_full"
][cite: 2]

def find_binary():
    candidates = [][cite: 2]
    for p in glob.glob(os.path.join(SOURCE_ROOT, "**", "*"), recursive=True):[cite: 2]
        name = os.path.basename(p).lower()[cite: 2]
        if "emulationstation" in name and os.path.isfile(p) and os.access(p, os.X_OK):[cite: 2]
            candidates.append(p)[cite: 2]
    if not candidates:
        print("[!] Kein ausführbares EmulationStation-Binary gefunden.")[cite: 2]
        sys.exit(1)[cite: 2]
    return max(candidates, key=os.path.getsize)[cite: 2]

def main():
    binary_path = find_binary()[cite: 2]
    print(f"[+] Prüfe Binary: {binary_path}")[cite: 2]

    out = subprocess.run(["strings", binary_path], capture_output=True, text=True).stdout[cite: 2]

    checks = {
        "OTA Update": "OTA Update" in out or "runOtaUpdateScript" in out,[cite: 2]
        "update_check.sh": "update_check.sh" in out,[cite: 2]
    }
    for mode in CUSTOM_MODES:
        checks[f"LED-Modus: {mode}"] = mode in out[cite: 2]

    print("==================================================")[cite: 2]
    print("      BINARY STRING VERIFICATION")[cite: 2]
    print("==================================================")[cite: 2]
    missing = [][cite: 2]
    for label, ok in checks.items():
        print(f"  - {label}: {'AVAILABLE' if ok else 'MISSING'}")[cite: 2]
        if not ok:
            missing.append(label)[cite: 2]

    if missing:
        print(f"[!] {len(missing)} Prüfung(en) fehlgeschlagen.")[cite: 2]
        sys.exit(1)[cite: 2]

    print("[OK] Alle OTA- und LED-Strings im Binary bestätigt.")[cite: 2]

if __name__ == "__main__":
    main()[cite: 2]
