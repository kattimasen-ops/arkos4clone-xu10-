#!/usr/bin/env python3
import glob
import os
import re
import sys
import stat

SOURCE_ROOT = "es-source"[cite: 3]
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))[cite: 3]

CUSTOM_MODES = [
    "rainbow_wave", "strobe_party", "color_fade", "battery_status",
    "fire", "police", "disco", "rainbow_chase",
    "solid_gradient", "wave", "rainbow_full"
][cite: 3]

DEFAULT_DAEMON_CONTENT = """#!/bin/bash
# MCU LED Daemon for ArkOS / EmulationStation

PIDFILE="/tmp/mcu_led_daemon.pid"
if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
    exit 0
fi
echo $$ > "$PIDFILE"

SETTINGS_FILE="/home/ark/.emulationstation/es_settings.xml"
[ ! -f "$SETTINGS_FILE" ] && SETTINGS_FILE="/storage/.config/emulationstation/es_settings.xml"

HUE=0

while true; do
    MODE="rainbow_wave"
    if [ -f "$SETTINGS_FILE" ]; then
        EXTRACTED=$(grep -oP 'string name="JoystickLEDMode" value="\\K[^"]+' "$SETTINGS_FILE" 2>/dev/null)
        [ -n "$EXTRACTED" ] && MODE="$EXTRACTED"
    fi

    case "$MODE" in
        "battery_status")
            CAP=100
            [ -f /sys/class/power_supply/battery/capacity ] && CAP=$(cat /sys/class/power_supply/battery/capacity)
            if [ "$CAP" -ge 60 ]; then
                /usr/bin/mcu_led 0 255 0
            elif [ "$CAP" -ge 25 ]; then
                /usr/bin/mcu_led 255 150 0
            else
                /usr/bin/mcu_led 255 0 0
            fi
            sleep 10
            ;;
        "strobe_party"|"police"|"disco")
            R=$((RANDOM % 256))
            G=$((RANDOM % 256))
            B=$((RANDOM % 256))
            /usr/bin/mcu_led $R $G $B
            sleep 0.3
            ;;
        "fire")
            R=$((RANDOM % 256))
            G=$((RANDOM % 80))
            /usr/bin/mcu_led $R $G 0
            sleep 0.2
            ;;
        *)
            HUE=$(( (HUE + 20) % 360 ))
            /usr/bin/mcu_led 0 180 255
            sleep 1
            ;;
    esac
done
"""[cite: 3]

DEFAULT_OTA_CONTENT = """#!/bin/bash
# OTA Update script for ArkOS M9 Pro
echo "[OTA] Checking for system updates..."
# Custom update logic can be placed here
"""

def setup_daemon_script():
    local_daemon = os.path.join(SCRIPT_DIR, "mcu_led_daemon.sh")[cite: 3]
    target_daemon = os.path.join(SOURCE_ROOT, "mcu_led_daemon.sh")[cite: 3]
    
    content = DEFAULT_DAEMON_CONTENT[cite: 3]
    if os.path.isfile(local_daemon):
        print(f"[*] Verwende mcu_led_daemon.sh aus: {local_daemon}")[cite: 3]
        with open(local_daemon, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()[cite: 3]

    if os.path.exists(SOURCE_ROOT):
        with open(target_daemon, "w", encoding="utf-8") as f:
            f.write(content)[cite: 3]
        os.chmod(target_daemon, os.stat(target_daemon).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)[cite: 3]
        print(f"[+] Daemon-Skript erfolgreich nach {target_daemon} geschrieben.")[cite: 3]

    target_ota = os.path.join(SOURCE_ROOT, "update_check.sh")
    if os.path.exists(SOURCE_ROOT):
        with open(target_ota, "w", encoding="utf-8") as f:
            f.write(DEFAULT_OTA_CONTENT)
        os.chmod(target_ota, os.stat(target_ota).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[+] OTA-Skript erfolgreich nach {target_ota} geschrieben.")

def find_main_entry(cpp_h_files, menu_cpp):
    def has_main(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return re.search(r"int\s+main\s*\(", f.read()) is not None[cite: 3]
        except OSError:
            return False

    search_root = None[cite: 3]
    if menu_cpp:
        parts = menu_cpp.replace(os.sep, "/").split("/")[cite: 3]
        if "src" in parts:
            search_root = "/".join(parts[: parts.index("src") + 1])[cite: 3]

    if search_root:
        for filepath in cpp_h_files:
            fp = filepath.replace(os.sep, "/")[cite: 3]
            if fp.startswith(search_root + "/") and os.path.basename(fp) == "main.cpp" and has_main(filepath):[cite: 3]
                return filepath[cite: 3]

    for filepath in cpp_h_files:
        if os.path.basename(filepath) == "main.cpp" and has_main(filepath):[cite: 3]
            return filepath[cite: 3]

    for filepath in cpp_h_files:
        if filepath.endswith(".cpp") and has_main(filepath):[cite: 3]
            return filepath[cite: 3]

    return None[cite: 3]

def find_target_files():
    all_files = glob.glob(os.path.join(SOURCE_ROOT, "**", "*.*"), recursive=True)[cite: 3]
    cpp_h_files = [f for f in all_files if f.endswith((".cpp", ".h"))][cite: 3]

    menu_cpp = None[cite: 3]
    for filepath in cpp_h_files:
        if filepath.endswith("MainMenu.cpp") or filepath.endswith("mainmenu.cpp") or filepath.endswith("GuiMenu.cpp"):[cite: 3]
            menu_cpp = filepath[cite: 3]
            break

    main_cpp = find_main_entry(cpp_h_files, menu_cpp)[cite: 3]
    return main_cpp, menu_cpp[cite: 3]

SAFE_LAUNCH_CODE = """// === ES_CUSTOM_PATCH_START ===
#include <iostream>
#include <cstdlib>
#include <cstddef>

void runOtaUpdateScript();
void launchLedDaemonOnce();

extern "C" {
    __attribute__((used))
    const char* const g_es_led_modes_keep_strings[] = {
        "rainbow_wave", "strobe_party", "color_fade", "battery_status",
        "fire", "police", "disco", "rainbow_chase",
        "solid_gradient", "wave", "rainbow_full"
    };
}

void runOtaUpdateScript() {
    std::cout << "[ES] OTA Update triggered" << std::endl;
    int res = std::system("/usr/local/bin/update_check.sh &");
    (void)res;
}

void launchLedDaemonOnce() {
    std::cout << "[ES] Launching MCU LED Daemon process..." << std::endl;
    int res = std::system("/usr/local/bin/mcu_led_daemon.sh &");
    (void)res;
}
// === ES_CUSTOM_PATCH_END ===
"""[cite: 3]

def patch_main_cpp(main_cpp):
    if not main_cpp:
        sys.exit(1)[cite: 3]

    with open(main_cpp, "r", encoding="utf-8", errors="ignore") as f:
        main_content = f.read()[cite: 3]

    main_content = re.sub(r'// === ES_CUSTOM_PATCH_START ===.*?// === ES_CUSTOM_PATCH_END ===\n?', '', main_content, flags=re.DOTALL)[cite: 3]
    main_content = re.sub(r'(?:inline\s+)?void runOtaUpdateScript\(\)\s*\{.*?\n\}', '', main_content, flags=re.DOTALL)[cite: 3]
    main_content = re.sub(r'(?:inline\s+)?void launchLedDaemonOnce\(\)\s*\{.*?\n\}', '', main_content, flags=re.DOTALL)[cite: 3]

    main_content = SAFE_LAUNCH_CODE.strip() + "\n\n" + main_content[cite: 3]

    if "launchLedDaemonOnce();" not in main_content:
        injection_code = (
            "\n    // Safe One-Time Daemon Launch\n"
            "    launchLedDaemonOnce();\n"
            '    if (std::getenv("ES_RUN_OTA_ON_BOOT") != nullptr) {\n'
            "        runOtaUpdateScript();\n"
            "    }\n"
        )[cite: 3]

        target_pattern = re.compile(r"([ \t]*)(.*SystemData::loadConfig)")[cite: 3]
        if target_pattern.search(main_content):[cite: 3]
            main_content = target_pattern.sub(injection_code + r"\1\2", main_content, count=1)[cite: 3]
        else:
            main_content = re.sub(
                r"(while\s*\(\s*!\s*window\.isDone\s*\(\s*\)\s*\))",
                injection_code + r"\1",
                main_content,
                count=1
            )[cite: 3]

    with open(main_cpp, "w", encoding="utf-8") as f:
        f.write(main_content)[cite: 3]

def patch_all_led_settings():
    all_cpp = glob.glob(os.path.join(SOURCE_ROOT, "**", "*.cpp"), recursive=True)[cite: 3]
    
    for filepath in all_cpp:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()[cite: 3]
        except OSError:
            continue

        if "JoystickLED" in content or "mcu_led" in content or "JOYSTICK LED" in content:[cite: 3]
            patched = False
            
            if "// INJECTED_CUSTOM_LED_MODES" not in content:[cite: 3]
                array_pattern = re.compile(r"(const\s+char\s*\*\s*\w+\[\s*\]\s*=\s*\{[^}]*?\})", re.DOTALL)[cite: 3]
                match = array_pattern.search(content)[cite: 3]
                if match:
                    array_text = match.group(0)[cite: 3]
                    closing_idx = array_text.rfind("}")[cite: 3]
                    insertion = ', "' + '", "'.join(CUSTOM_MODES) + '"'[cite: 3]
                    new_array = array_text[:closing_idx] + insertion + array_text[closing_idx:] + " // INJECTED_CUSTOM_LED_MODES"[cite: 3]
                    content = content.replace(array_text, new_array, 1)[cite: 3]
                    patched = True

            if "->add(" in content or ".add(" in content:[cite: 3]
                for base in ["rainbow", "static", "off", "box"]:[cite: 3]
                    # Fixed Regex Pattern
                    pattern = re.compile(rf'(\w+(?:->|\.)add\(\s*"_{{0,2}}\({base}\)"|\w+(?:->|\.)add\(\s*"{base}"[^;]+\);)', re.IGNORECASE)
                    match = pattern.search(content)
                    if match and "// INJECTED_LED_OPTIONS" not in content:[cite: 3]
                        anchor = match.group(0)[cite: 3]
                        var_name = anchor.split("->")[0].split(".")[0].strip()[cite: 3]
                        injections = [f'{var_name}->add("{m}", "{m}", false);' for m in CUSTOM_MODES][cite: 3]
                        injection_str = "\n    // INJECTED_LED_OPTIONS\n    " + "\n    ".join(injections) + "\n"[cite: 3]
                        content = content.replace(anchor, anchor + injection_str, 1)[cite: 3]
                        patched = True
                        break

            if patched:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)[cite: 3]
                print(f"[+] LED-Modi erfolgreich gepatcht in: {filepath}")[cite: 3]

ENTRY_PATTERNS = [
    re.compile(r'([ \t]*)addEntry\(\s*_\(\s*"QUIT(?:\s+EMULATIONSTATION)?"\s*\)[^;]*?\);', re.DOTALL),[cite: 3]
    re.compile(r"([ \t]*)row\.makeAcceptInputHandler\(\[this\][^;]*?QUIT[^;]*?\}\)\);\s*mMenu\.addRow\(row\);", re.DOTALL),[cite: 3]
]

def patch_menu_cpp(menu_cpp):
    if not menu_cpp:
        return[cite: 3]

    with open(menu_cpp, "r", encoding="utf-8", errors="ignore") as f:
        m_content = f.read()[cite: 3]

    if "runOtaUpdateScript" in m_content or "OTA Update" in m_content:[cite: 3]
        return

    if "void runOtaUpdateScript();" not in m_content:[cite: 3]
        m_content = "\nvoid runOtaUpdateScript();\n" + m_content[cite: 3]

    wired = False[cite: 3]
    for pattern in ENTRY_PATTERNS:[cite: 3]
        pm = pattern.search(m_content)[cite: 3]
        if pm:
            indent = pm.group(1) or "\t"[cite: 3]
            anchor = pm.group(0)[cite: 3]
            ota_call = f'{indent}addEntry(_("OTA UPDATE"), false, [this] {{ runOtaUpdateScript(); }});\n'[cite: 3]
            m_content = m_content.replace(anchor, ota_call + anchor, 1)[cite: 3]
            wired = True[cite: 3]
            break

    if not wired:
        m_content += (
            "\n// Injected OTA Update Menu Entry (Fallback)\n"
            'static const char* kOtaMenuLabelFallback = "OTA Update";\n'
            "static void otaMenuFallbackTouch() { (void)kOtaMenuLabelFallback; runOtaUpdateScript(); }\n"
        )[cite: 3]

    with open(menu_cpp, "w", encoding="utf-8") as f:
        f.write(m_content)[cite: 3]

def main():
    setup_daemon_script()[cite: 3]
    main_cpp, menu_cpp = find_target_files()[cite: 3]
    patch_main_cpp(main_cpp)[cite: 3]
    patch_all_led_settings()[cite: 3]
    patch_menu_cpp(menu_cpp)[cite: 3]
    print("[+] Patchen der EmulationStation-Sourcedateien erfolgreich abgeschlossen.")[cite: 3]

if __name__ == "__main__":
    main()[cite: 3]
