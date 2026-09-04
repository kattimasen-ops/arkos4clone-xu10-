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
    ("PULSE GREEN", "pulse_green"),
]

# How close (in characters) an anchor string like "flow"/"rainbow" must be
# to an actual "JoystickLED" mention to be considered part of that same
# option list. Stock ES also uses words like "flow" and "rainbow" for
# unrelated settings (e.g. transition styles) elsewhere in the same big
# GuiMenu.cpp-style file - without this proximity check, a plain
# whole-file search can land on the wrong dropdown entirely.
MAX_ANCHOR_DISTANCE = 2000

ANCHOR_PATTERN = re.compile(r'"(flow|rainbow|breathing_white|static_white)"')


def get_source_root():
    """Return the source directory from CLI arg, ENV, or default."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    env_dir = os.environ.get("ES_SOURCE_DIR")
    if env_dir:
        return env_dir
    if os.path.isdir("es-source"):
        return "es-source"
    if os.path.isdir("/tmp/es-source"):
        return "/tmp/es-source"
    print("[!] Could not locate ES source directory.", file=sys.stderr)
    sys.exit(1)


def closest_anchor(content, joystick_spans):
    """Return the ANCHOR_PATTERN match closest to any JoystickLED mention,
    within MAX_ANCHOR_DISTANCE characters, or None if nothing qualifies."""
    best_match = None
    best_distance = None
    for m in ANCHOR_PATTERN.finditer(content):
        distance = min(abs(m.start() - js) for js in joystick_spans)
        if distance <= MAX_ANCHOR_DISTANCE and (best_distance is None or distance < best_distance):
            best_match = m
            best_distance = distance
    return best_match


def patch_joystick_menu():
    source_root = get_source_root()
    search_dir = os.path.join(source_root, "es-app", "src", "guis")

    if not os.path.exists(search_dir):
        print(f"[!] Directory {search_dir} not found. Skipping C++ patch.")
        return

    patched_any = False
    for root, _, files in os.walk(search_dir):
        for file in files:
            if not (file.endswith(".cpp") or file.endswith(".h")):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            joystick_spans = [m.start() for m in re.finditer(r"JoystickLED", content)]
            if not joystick_spans:
                continue

            print(f"[*] Found Joystick LED reference in: {filepath}")
            file_changed = False

            for label, mode_key in NEW_MODES:
                if mode_key in content:
                    continue

                match = closest_anchor(content, joystick_spans)
                if match is None:
                    print(f"  ! No anchor within {MAX_ANCHOR_DISTANCE} chars of JoystickLED "
                          f"for [{mode_key}] in {filepath} - skipped rather than guessing.")
                    continue

                insert_at = match.end()
                content = content[:insert_at] + f', "{mode_key}"' + content[insert_at:]
                file_changed = True
                print(f"  + Added UI option: {label} [{mode_key}]")

            if file_changed:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                patched_any = True

    if patched_any:
        print("[SUCCESS] All stock modes preserved and new modes appended to menu.")
    else:
        print("[*] Joystick LED menu options verified (no changes made).")


if __name__ == "__main__":
    patch_joystick_menu()
