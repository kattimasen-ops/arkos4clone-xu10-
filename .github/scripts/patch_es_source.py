#!/usr/bin/env python3
import os
import re

# New custom modes to add alongside all stock options
NEW_MODES = [
    ("RAINBOW WAVE", "rainbow_wave"),
    ("BATTERY STATUS", "battery_status"),
    ("FIRE", "fire"),
    ("POLICE", "police"),
    ("DISCO", "disco"),
    ("PULSE RED", "pulse_red"),
    ("PULSE BLUE", "pulse_blue"),
    ("PULSE GREEN", "pulse_green")
]

def patch_joystick_menu():
    print("[*] Scanning C++ files for Joystick LED menu configuration...")
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

                # Look for the Joystick LED option list definition in ES
                if "JoystickLED" in content or "joystick_led" in content or "Joystick LED" in content:
                    print(f"[*] Found Joystick LED reference in: {filepath}")
                    
                    for label, mode_key in NEW_MODES:
                        if mode_key not in content:
                            # Inject new options before the closing of the dropdown population vector
                            pattern = r'("flow"|"rainbow"|"breathing_white"|"static_white")'
                            replacement = r'\1, "' + mode_key + '"'
                            if re.search(pattern, content):
                                content = re.sub(pattern, replacement, content, count=1)
                                patched = True
                                print(f"  + Added UI option: {label} [{mode_key}]")

                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)

    if patched:
        print("[SUCCESS] All stock modes preserved and new modes appended to menu.")
    else:
        print("[*] Joystick LED menu options verified.")

if __name__ == "__main__":
    patch_joystick_menu()
