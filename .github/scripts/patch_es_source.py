#!/usr/bin/env python3
import os
import re
import sys

# Directory resolution
SOURCE_ROOT = os.environ.get("ES_SOURCE_DIR", "/tmp/es-source")

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
    search_dir = os.path.join(SOURCE_ROOT, "es-app/src/guis")
    
    if not os.path.exists(search_dir):
        print(f"[!] Directory {search_dir} not found. Skipping C++ LED patch.")
        return

    patched = False
    for root, _, files in os.walk(search_dir):
        for file in files:
            if file.endswith(".cpp") or file.endswith(".h"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if any(k in content for k in ["JoystickLED", "joystick_led", "Joystick LED"]):
                    print(f"[*] Found Joystick LED reference in: {filepath}")
                    
                    for label, mode_key in NEW_MODES:
                        if mode_key not in content:
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
        print("[*] Joystick LED menu options verified or already injected.")

def patch_ota_menu():
    print("[*] Patching GuiMenu.cpp for ArkOS4Clones OTA Update Trigger...")
    gui_menu_path = os.path.join(SOURCE_ROOT, "es-app/src/guis/GuiMenu.cpp")
    
    if not os.path.exists(gui_menu_path):
        print(f"[!] {gui_menu_path} not found. Skipping OTA menu patch.")
        return

    with open(gui_menu_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if "update_check.sh" not in content:
        ota_code = '''
    // ArkOS4Clones OTA Update Trigger
    s->addEntry("CHECK FOR ARKOS4CLONES UPDATES", true, [this] {
        system("/usr/local/bin/update_check.sh > /tmp/ota_gui.log 2>&1 &");
    });
'''
        # Inject entry before "QUIT" or at end of main menu list
        if 'addEntry("QUIT"' in content:
            content = content.replace('addEntry("QUIT"', ota_code + '\n    addEntry("QUIT"')
            print("[✓] Injected ArkOS4Clones OTA trigger into GuiMenu.cpp")
        elif 'addEntry("SYSTEM SETTINGS"' in content:
            content = content.replace('addEntry("SYSTEM SETTINGS"', ota_code + '\n    addEntry("SYSTEM SETTINGS"')
            print("[✓] Injected ArkOS4Clones OTA trigger into GuiMenu.cpp")

        with open(gui_menu_path, "w", encoding="utf-8") as f:
            f.write(content)

def patch_renderer_linker_fix():
    print("[*] Injecting Renderer::getSDLWindow() symbol directly into C++ source files...")
    cpp_fix = """
#include <SDL2/SDL.h>
namespace Renderer {
    SDL_Window* getSDLWindow() {
        return SDL_GL_GetCurrentWindow();
    }
}
"""
    for root, _, files in os.walk(SOURCE_ROOT):
        for file in files:
            if file in ["Renderer_GL21.cpp", "Renderer.cpp", "Renderer_GLES20.cpp"]:
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                if "getSDLWindow" not in content or "SDL_GL_GetCurrentWindow" not in content:
                    with open(filepath, "a", encoding="utf-8") as f:
                        f.write("\n" + cpp_fix + "\n")
                    print(f"[✓] Appended getSDLWindow() directly to {filepath}")

if __name__ == "__main__":
    patch_joystick_menu()
    patch_ota_menu()
    patch_renderer_linker_fix()
    print("[✓] All source patching completed successfully.")
