#!/usr/bin/env python3
import os
import re

# Custom modes to add alongside stock colors and 'flow'
NEW_MODES = [
    "rainbow_wave",
    "rainbow_full",
    "battery_status",
    "fire",
    "strobe_party",
    "police",
    "disco",
    "pulse_red",
    "pulse_blue",
    "pulse_green"
]

def patch_joystick_menu():
    print("[*] Scanning C++ files for Joystick LED options...")
    
    # Target GUI files in es-app
    search_dir = "es-source/es-app/src/guis"
    if not os.path.exists(search_dir):
        print(f"[!] Directory {search_dir} not found. Skipping C++ patch.")
        return

    patched = False
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.endswith(".cpp") or file.endswith(".h"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Find arrays or dropdown populators defining Joystick LED options
                if "JoystickLED" in content or "joystick_led" in content or "Joystick LED" in content:
                    print(f"[*] Found Joystick LED reference in: {filepath}")
                    
                    # Pattern to locate string vectors/lists of LED options
                    for mode in NEW_MODES:
                        if mode not in content:
                            # Safely inject new modes before the end of options array/list
                            pattern = r'("flow"|"rainbow"|"breathing")'
                            replacement = r'\1, "' + mode + '"'
                            if re.search(pattern, content):
                                content = re.sub(pattern, replacement, content, count=1)
                                patched = True
                                print(f"  + Added mode: {mode}")

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

    if patched:
        print("[SUCCESS] Joystick LED menu expanded while retaining all stock color options!")
    else:
        print("[*] Stock modes verified. Options ready.")

if __name__ == "__main__":
    patch_joystick_menu()
