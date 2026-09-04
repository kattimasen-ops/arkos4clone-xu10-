#!/usr/bin/env python3
import os
import re
import sys

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

def get_source_root():
    """Return the source directory from CLI arg, ENV, or default."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    env_dir = os.environ.get("ES_SOURCE_DIR")
    if env_dir:
        return env_dir
    # Fallback to ./es-source
    if os.path.isdir("es-source"):
        return "es-source"
    # Fallback to /tmp/es-source
    if os.path.isdir("/tmp/es-source"):
        return "/tmp/es-source"
    print("[!] Could not locate ES source directory.", file=sys.stderr)
    sys.exit(1)

def patch_joystick_menu():
    source_root = get_source_root()
    search_dir = os.path.join(source_root, "es-app", "src", "guis")

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
