#!/usr/bin/env python3
import glob
import os
import re
import sys

SOURCE_ROOT = "es-source"

CUSTOM_MODES = [
    "rainbow_wave", "strobe_party", "color_fade", "battery_status",
    "fire", "police", "disco", "rainbow_chase",
    "solid_gradient", "wave", "rainbow_full"
]

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

OTA_FUNCTION = """
// Injected OTA Update Trigger Helper
#include <iostream>
#include <cstdlib>

static void safeSystemCall(const char* cmd) {
    int res = system(cmd);
    (void)res;
}

void runOtaUpdateScript() {
    std::cout << "[ES] OTA Update triggered" << std::endl;
    safeSystemCall("/usr/local/bin/update_check.sh &");
}
"""

THREAD_CODE = r"""
#include <thread>
#include <chrono>
#include <fstream>
#include <cstdlib>
#include <cmath>
#include <string>
#include <ctime>
#include "Settings.h"

static void safeSystemCmd(const std::string& cmd) {
    int res = system(cmd.c_str());
    (void)res;
}

void CustomMCUThread() {
    std::this_thread::sleep_for(std::chrono::seconds(5));
    int hue = 0;
    srand(time(NULL));

    while (true) {
        if (Settings::getInstance() != nullptr) {
            std::string mode = Settings::getInstance()->getString("JoystickLEDMode");

            if (mode == "battery_status") {
                std::ifstream bat("/sys/class/power_supply/battery/capacity");
                int cap = 100;
                if (bat.is_open()) { bat >> cap; bat.close(); }

                if (cap >= 60) safeSystemCmd("/usr/bin/mcu_led 0 255 0 &");
                else if (cap >= 25) safeSystemCmd("/usr/bin/mcu_led 255 150 0 &");
                else safeSystemCmd("/usr/bin/mcu_led 255 0 0 &");

                std::this_thread::sleep_for(std::chrono::seconds(5));
            }
            else if (mode == "rainbow_wave") {
                hue = (hue + 15) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            else if (mode == "strobe_party") {
                safeSystemCmd("/usr/bin/mcu_led 255 0 0 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
                safeSystemCmd("/usr/bin/mcu_led 0 255 0 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
                safeSystemCmd("/usr/bin/mcu_led 0 0 255 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
            }
            else if (mode == "color_fade") {
                hue = (hue + 5) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(250));
            }
            else if (mode == "fire") {
                int r = rand() % 256;
                int g = rand() % 80;
                int b = 0;
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(40));
            }
            else if (mode == "police") {
                safeSystemCmd("/usr/bin/mcu_led 255 0 0 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                safeSystemCmd("/usr/bin/mcu_led 0 0 255 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            else if (mode == "disco") {
                int colors[6][3] = {{255,0,0},{0,255,0},{0,0,255},{255,255,0},{255,0,255},{0,255,255}};
                int idx = rand() % 6;
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(colors[idx][0]) + " " + std::to_string(colors[idx][1]) + " " + std::to_string(colors[idx][2]) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
            }
            else if (mode == "rainbow_chase") {
                hue = (hue + 25) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(80));
            }
            else if (mode == "solid_gradient") {
                hue = (hue + 2) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
            else if (mode == "wave") {
                hue = (hue + 10) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(150));
            }
            else if (mode == "rainbow_full") {
                hue = (hue + 3) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                safeSystemCmd("/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &");
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
            }
            else {
                std::this_thread::sleep_for(std::chrono::seconds(2));
            }
        } else {
            std::this_thread::sleep_for(std::chrono::seconds(2));
        }
    }
}
"""

def patch_main_cpp(main_cpp):
    if not main_cpp:
        sys.exit(1)

    with open(main_cpp, "r", encoding="utf-8", errors="ignore") as f:
        main_content = f.read()

    if "runOtaUpdateScript" not in main_content:
        include_matches = list(re.finditer(r"#include\s+<[^>]+>", main_content))
        if include_matches:
            last_idx = include_matches[-1].end()
            main_content = main_content[:last_idx] + "\n" + OTA_FUNCTION + main_content[last_idx:]
        else:
            main_content = OTA_FUNCTION + "\n" + main_content

    if "CustomMCUThread" not in main_content:
        main_content = THREAD_CODE + "\n" + main_content
        
        injection_code = (
            "\n    // Injected MCU Thread & OTA Check\n"
            "    std::thread mcuThread(CustomMCUThread);\n"
            "    mcuThread.detach();\n"
            '    if (std::getenv("ES_RUN_OTA_ON_BOOT") != nullptr) {\n'
            "        runOtaUpdateScript();\n"
            "    }\n"
        )
        
        if "SystemData::loadConfig" in main_content:
            main_content = main_content.replace("SystemData::loadConfig", injection_code + "    SystemData::loadConfig", 1)
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

    if any(m in s_content for m in CUSTOM_MODES):
        return

    array_pattern = re.compile(r"(const\s+char\s*\*\s*[^;=\n]+\[\s*\]\s*=\s*\{[^}]*?\})", re.DOTALL)
    match = array_pattern.search(s_content)
    
    if match:
        array_text = match.group(0)
        if any(k in array_text for k in ["static", "rainbow", "breathing"]):
            closing_idx = array_text.rfind("}")
            insertion = ', "' + '", "'.join(CUSTOM_MODES) + '"'
            new_array = array_text[:closing_idx] + insertion + array_text[closing_idx:]
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
    settings_cpp, main_cpp, menu_cpp = find_target_files()
    patch_main_cpp(main_cpp)
    patch_settings_cpp(settings_cpp)
    patch_menu_cpp(menu_cpp)

if __name__ == "__main__":
    main()
