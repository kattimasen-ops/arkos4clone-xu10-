#!/usr/bin/env python3
import glob
import os
import re
import sys
import stat

SOURCE_ROOT = "es-source"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

CUSTOM_MODES = [
    "rainbow_wave", "strobe_party", "color_fade", "battery_status",
    "fire", "police", "disco", "rainbow_chase",
    "solid_gradient", "wave", "rainbow_full"
]

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
"""

def setup_daemon_script():
    local_daemon = os.path.join(SCRIPT_DIR, "mcu_led_daemon.sh")
    target_daemon = os.path.join(SOURCE_ROOT, "mcu_led_daemon.sh")
    
    content = DEFAULT_DAEMON_CONTENT
    if os.path.isfile(local_daemon):
        print(f"[*] Verwende mcu_led_daemon.sh aus: {local_daemon}")
        with open(local_daemon, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    else:
        print("[*] Lokales mcu_led_daemon.sh nicht gefunden. Generiere Standard-Template...")

    if os.path.exists(SOURCE_ROOT):
        with open(target_daemon, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(target_daemon, os.stat(target_daemon).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        print(f"[+] Daemon-Skript erfolgreich nach {target_daemon} geschrieben und ausführbar gemacht.")

def find_main_entry(cpp_h_files, menu_cpp):
    def has_main(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return re.search(r"int\s+main\s*\(", f.read()) is not None
        except OSError:
            return False

    search_root = None
    if menu_cpp:
        parts = menu_cpp.replace(os.sep, "/").split("/")
        if "src" in parts:
            search_root = "/".join(parts[: parts.index("src") + 1])

    if search_root:
        for filepath in cpp_h_files:
            fp = filepath.replace(os.sep, "/")
            if fp.startswith(search_root + "/") and os.path.basename(fp) == "main.cpp" and has_main(filepath):
                return filepath

    for filepath in cpp_h_files:
        if os.path.basename(filepath) == "main.cpp" and has_main(filepath):
            return filepath

    for filepath in cpp_h_files:
        if filepath.endswith(".cpp") and has_main(filepath):
            return filepath

    return None

def find_target_files():
    all_files = glob.glob(os.path.join(SOURCE_ROOT, "**", "*.*"), recursive=True)
    cpp_h_files = [f for f in all_files if f.endswith((".cpp", ".h"))]

    settings_cpp = None
    menu_cpp = None

    for filepath in cpp_h_files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue

        if "JoystickLEDMode" in content or "JoystickLED" in content or "mcu_led" in content:
            if not settings_cpp:
                settings_cpp = filepath
        if filepath.endswith("MainMenu.cpp") or filepath.endswith("mainmenu.cpp") or filepath.endswith("GuiMenu.cpp"):
            menu_cpp = filepath

    if not settings_cpp:
        for filepath in cpp_h_files:
            if "GuiSettings" in filepath and filepath.endswith(".cpp"):
                settings_cpp = filepath
                break

    if not settings_cpp:
        print("[!] Keine passende Einstellungsdatei gefunden. Abbruch.")
        sys.exit(1)

    main_cpp = find_main_entry(cpp_h_files, menu_cpp)
    return settings_cpp, main_cpp, menu_cpp

SAFE_LAUNCH_CODE = """
// Safe External Daemon & OTA Launchers
#include <iostream>
#include <cstdlib>

static void safeSystemCall(const char* cmd) {
    if (!cmd) return;
    int res = system(cmd);
    (void)res;
}

void runOtaUpdateScript() {
    std::cout << "[ES] OTA Update triggered" << std::endl;
    safeSystemCall("/usr/local/bin/update_check.sh &");
}

void launchLedDaemonOnce() {
    std::cout << "[ES] Launching MCU LED Daemon process..." << std::endl;
    safeSystemCall("/usr/local/bin/mcu_led_daemon.sh &");
}
"""

def patch_main_cpp(main_cpp):
    if not main_cpp:
        sys.exit(1)

    with open(main_cpp, "r", encoding="utf-8", errors="ignore") as f:
        main_content = f.read()

    if "launchLedDaemonOnce" not in main_content:
        include_matches = list(re.finditer(r"#include\s+<[^>]+>", main_content))
        if include_matches:
            last_idx = include_matches[-1].end()
            main_content = main_content[:last_idx] + "\n" + SAFE_LAUNCH_CODE + main_content[last_idx:]
        else:
            main_content = SAFE_LAUNCH_CODE + "\n" + main_content

        injection_code = (
            "\n    // Safe One-Time Daemon Launch\n"
            "    launchLedDaemonOnce();\n"
            '    if (std::getenv("ES_RUN_OTA_ON_BOOT") != nullptr) {\n'
            "        runOtaUpdateScript();\n"
            "    }\n"
        )

        target_pattern = re.compile(r"([ \t]*)(.*SystemData::loadConfig)")
        if target_pattern.search(main_content):
            main_content = target_pattern.sub(injection_code + r"\1\2", main_content, count=1)
        else:
            main_content = re.sub(
                r"(while\s*\(\s*!\s*window\.isDone\s*\(\s*\)\s*\))",
                injection_code + r"\1",
                main_content,
                count=1
            )

    with open(main_cpp, "w", encoding="utf-8") as f:
        f.write(main_content)

def patch_settings_cpp(settings_cpp):
    with open(settings_cpp, "r", encoding="utf-8", errors="ignore") as f:
        s_content = f.read()

    # Verwende eindeutige Markierung statt "any()", da Worte wie "fire" oder "wave" oft schon existieren
    if "// INJECTED_CUSTOM_LED_MODES" in s_content or "strobe_party" in s_content:
        return

    array_pattern = re.compile(r"(const\s+char\s*\*\s*[^;=\n]+\[\s*\]\s*=\s*\{[^}]*?\})", re.DOTALL)
    match = array_pattern.search(s_content)

    if match:
        array_text = match.group(0)
        if any(k in array_text for k in ["static", "rainbow", "breathing", "off", "on"]):
            closing_idx = array_text.rfind("}")
            insertion = ', "' + '", "'.join(CUSTOM_MODES) + '"'
            new_array = array_text[:closing_idx] + insertion + array_text[closing_idx:] + " // INJECTED_CUSTOM_LED_MODES"
            s_content = s_content.replace(array_text, new_array, 1)
        else:
            match = None

    if not match:
        if '"static"' in s_content:
            s_content = s_content.replace('"static"', '"static", "' + '", "'.join(CUSTOM_MODES) + '"', 1)
        elif '"rainbow"' in s_content:
            s_content = s_content.replace('"rainbow"', '"rainbow", "' + '", "'.join(CUSTOM_MODES) + '"', 1)

    with open(settings_cpp, "w", encoding="utf-8") as f:
        f.write(s_content)

ENTRY_PATTERNS = [
    re.compile(r'([ \t]*)addEntry\(\s*_\(\s*"QUIT(?:\s+EMULATIONSTATION)?"\s*\)[^;]*?\);', re.DOTALL),
    re.compile(r"([ \t]*)row\.makeAcceptInputHandler\(\[this\][^;]*?QUIT[^;]*?\}\)\);\s*mMenu\.addRow\(row\);", re.DOTALL),
]

def patch_menu_cpp(menu_cpp):
    if not menu_cpp:
        return

    with open(menu_cpp, "r", encoding="utf-8", errors="ignore") as f:
        m_content = f.read()

    if "runOtaUpdateScript" in m_content or "OTA Update" in m_content:
        return

    if "extern void runOtaUpdateScript();" not in m_content:
        m_content = "\nextern void runOtaUpdateScript();\n" + m_content

    wired = False
    for pattern in ENTRY_PATTERNS:
        pm = pattern.search(m_content)
        if pm:
            indent = pm.group(1) or "\t"
            anchor = pm.group(0)
            ota_call = f'{indent}addEntry(_("OTA UPDATE"), false, [this] {{ runOtaUpdateScript(); }});\n'
            m_content = m_content.replace(anchor, ota_call + anchor, 1)
            wired = True
            break

    if not wired:
        m_content += (
            "\n// Injected OTA Update Menu Entry (Fallback)\n"
            'static const char* kOtaMenuLabelFallback = "OTA Update";\n'
            "static void otaMenuFallbackTouch() { (void)kOtaMenuLabelFallback; runOtaUpdateScript(); }\n"
        )

    with open(menu_cpp, "w", encoding="utf-8") as f:
        f.write(m_content)

def main():
    setup_daemon_script()
    settings_cpp, main_cpp, menu_cpp = find_target_files()
    patch_main_cpp(main_cpp)
    patch_settings_cpp(settings_cpp)
    patch_menu_cpp(menu_cpp)
    print("[+] Patchen der EmulationStation-Sourcedateien erfolgreich abgeschlossen.")

if __name__ == "__main__":
    main()
