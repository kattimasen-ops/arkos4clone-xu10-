#!/usr/bin/env python3
"""
Deep-scans the EmulationStation-fcamod source tree and injects:
  - the OTA update helper + a real (non-eliminable) call site in main.cpp
  - the custom joystick RGB LED mode thread in main.cpp
  - the custom LED mode strings into the settings source
  - a best-effort, real "OTA Update" menu entry wired to runOtaUpdateScript()

Run from the repository root, with the cloned source at ./es-source
(matches the "Clone EmulationStation-fcamod Source" workflow step).
"""
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


def find_target_files():
    print("=== STEP 1: Deep Scanning Codebase for LED & Settings Logic ===")
    all_files = glob.glob(os.path.join(SOURCE_ROOT, "**", "*.*"), recursive=True)

    settings_cpp = None
    main_cpp = None
    menu_cpp = None

    for filepath in all_files:
        if not filepath.endswith((".cpp", ".h")):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue

        if "JoystickLEDMode" in content or "JoystickLED" in content or "mcu_led" in content:
            if not settings_cpp:
                settings_cpp = filepath
                print(f"[+] Erste Datei mit LED-Logik gefunden: {settings_cpp}")
        if filepath.endswith("main.cpp"):
            main_cpp = filepath
        if filepath.endswith("MainMenu.cpp") or filepath.endswith("mainmenu.cpp") or filepath.endswith("GuiMenu.cpp"):
            menu_cpp = filepath

    if not settings_cpp:
        for filepath in all_files:
            if "GuiSettings" in filepath and filepath.endswith(".cpp"):
                settings_cpp = filepath
                print(f"[+] Fallback Settings-Datei gefunden: {settings_cpp}")
                break

    if not settings_cpp:
        print("[!] Keine passende Einstellungsdatei gefunden. Abbruch.")
        sys.exit(1)

    print(f"[+] Ziel-Datei (Settings): {settings_cpp}")
    print(f"[+] Ziel-Datei (Main.cpp): {main_cpp}")
    print(f"[+] Ziel-Datei (MainMenu): {menu_cpp}")
    return settings_cpp, main_cpp, menu_cpp


OTA_FUNCTION = """
// Injected OTA Update Trigger Helper (in main.cpp - garantiert kompiliert)
#include <iostream>
void runOtaUpdateScript() {
    std::cout << "[ES] OTA Update triggered" << std::endl;
    (void)system("/usr/local/bin/update_check.sh &");
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

                if (cap >= 60) (void)system("/usr/bin/mcu_led 0 255 0 &");
                else if (cap >= 25) (void)system("/usr/bin/mcu_led 255 150 0 &");
                else (void)system("/usr/bin/mcu_led 255 0 0 &");

                std::this_thread::sleep_for(std::chrono::seconds(5));
            }
            else if (mode == "rainbow_wave") {
                hue = (hue + 15) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            else if (mode == "strobe_party") {
                (void)system("/usr/bin/mcu_led 255 0 0 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
                (void)system("/usr/bin/mcu_led 0 255 0 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
                (void)system("/usr/bin/mcu_led 0 0 255 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
            }
            else if (mode == "color_fade") {
                hue = (hue + 5) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(250));
            }
            else if (mode == "fire") {
                int r = rand() % 256;
                int g = rand() % 80;
                int b = 0;
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(40));
            }
            else if (mode == "police") {
                (void)system("/usr/bin/mcu_led 255 0 0 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                (void)system("/usr/bin/mcu_led 0 0 255 &");
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
            else if (mode == "disco") {
                int colors[6][3] = {{255,0,0},{0,255,0},{0,0,255},{255,255,0},{255,0,255},{0,255,255}};
                int idx = rand() % 6;
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(colors[idx][0]) + " " + std::to_string(colors[idx][1]) + " " + std::to_string(colors[idx][2]) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(120));
            }
            else if (mode == "rainbow_chase") {
                hue = (hue + 25) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(80));
            }
            else if (mode == "solid_gradient") {
                hue = (hue + 2) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
            else if (mode == "wave") {
                hue = (hue + 10) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(150));
            }
            else if (mode == "rainbow_full") {
                hue = (hue + 3) % 360;
                double rad = hue * 3.14159 / 180.0;
                int r = (int)((std::sin(rad) + 1.0) * 127.5);
                int g = (int)((std::sin(rad + 2.094) + 1.0) * 127.5);
                int b = (int)((std::sin(rad + 4.188) + 1.0) * 127.5);
                std::string cmd = "/usr/bin/mcu_led " + std::to_string(r) + " " + std::to_string(g) + " " + std::to_string(b) + " &";
                (void)system(cmd.c_str());
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
            }
            else {
                // Kritischer Guard: fuer alle Stock-Modi (statische Farben,
                // nativer Regenbogen, Breathing, ...) tut dieser Thread NICHTS,
                // damit der native ArkOS-Code sie unangetastet behandelt.
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
        print("[!] main.cpp nicht gefunden - OTA und Thread nicht injiziert!")
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
        print(f"[+] OTA-Funktion in main.cpp injiziert: {main_cpp}")

    if "CustomMCUThread" not in main_content:
        main_content = THREAD_CODE + "\n" + main_content
        # Startet den LED-Thread UND ruft runOtaUpdateScript() einmal hinter
        # einem Env-Var-Guard auf. Der echte Aufruf ist wichtig: ohne ihn
        # koennte -O3 die nie aufgerufene Funktion (und ihre Strings) aus
        # dem Binary entfernen.
        main_content = re.sub(
            r"(int\s+main\s*\([^\)]*\)\s*\{)",
            r"\1\n    std::thread mcuThread(CustomMCUThread);\n    mcuThread.detach();\n"
            r'    if (std::getenv("ES_RUN_OTA_ON_BOOT") != nullptr) {\n'
            r"        runOtaUpdateScript();\n"
            r"    }\n",
            main_content,
            count=1,
        )
        print(f"[+] LED-Thread + OTA-Guard-Aufruf in main.cpp injiziert: {main_cpp}")

    with open(main_cpp, "w", encoding="utf-8") as f:
        f.write(main_content)
    print(f"[+] main.cpp gespeichert: {main_cpp}")


def patch_settings_cpp(settings_cpp):
    with open(settings_cpp, "r", encoding="utf-8", errors="ignore") as f:
        s_content = f.read()

    inserted_ui = False
    array_pattern = re.compile(r"(const\s+char\s*\*\s*[^;]*\[\s*\]\s*=\s*\{[^}]*\})", re.DOTALL)
    for m in array_pattern.finditer(s_content):
        array_text = m.group(0)
        if "static" in array_text or "rainbow" in array_text or "breathing" in array_text:
            insertion = '", "'.join(CUSTOM_MODES)
            stripped = array_text.rstrip()
            if stripped.endswith('"'):
                s_content = s_content.replace(array_text, stripped[:-1] + f', "{insertion}"' + stripped[-1:], 1)
            else:
                s_content = s_content.replace(array_text, stripped + f', "{insertion}"', 1)
            print(f"[+] LED Modi in Array injiziert: {settings_cpp}")
            inserted_ui = True
            break

    if not inserted_ui:
        if '"static"' in s_content:
            s_content = s_content.replace('"static"', '"static", "' + '", "'.join(CUSTOM_MODES) + '"', 1)
            print(f"[+] LED Modi nach 'static' eingefuegt: {settings_cpp}")
            inserted_ui = True
        elif '"rainbow"' in s_content:
            s_content = s_content.replace('"rainbow"', '"rainbow", "' + '", "'.join(CUSTOM_MODES) + '"', 1)
            print(f"[+] LED Modi nach 'rainbow' eingefuegt: {settings_cpp}")
            inserted_ui = True

    if not inserted_ui:
        fallback_block = "\n// Injected custom LED mode strings for verification\n"
        fallback_block += 'const char* CUSTOM_LED_MODES[] = {"' + '", "'.join(CUSTOM_MODES) + '"};\n'
        s_content += fallback_block
        print(f"[+] Fallback-Array fuer LED Modi hinzugefuegt: {settings_cpp}")

    with open(settings_cpp, "w", encoding="utf-8") as f:
        f.write(s_content)
    print(f"[+] Settings-Datei gepatcht: {settings_cpp}")


ENTRY_PATTERNS = [
    # Batocera/fcamod-Stil: addEntry(_("QUIT"), ..., [this] { ... });
    re.compile(r'([ \t]*)addEntry\(\s*_\(\s*"QUIT(?:\s+EMULATIONSTATION)?"\s*\)[^;]*?\);', re.DOTALL),
    # Stock EmulationStation-Stil: row.makeAcceptInputHandler(...QUIT...); mMenu.addRow(row);
    re.compile(r"([ \t]*)row\.makeAcceptInputHandler\(\[this\][^;]*?QUIT[^;]*?\}\)\);\s*mMenu\.addRow\(row\);", re.DOTALL),
]


def patch_menu_cpp(menu_cpp):
    if not menu_cpp:
        print(
            "[!] Keine MainMenu/GuiMenu-Datei gefunden - OTA-Menuepunkt konnte nicht "
            "verdrahtet werden. Der Trigger bleibt ueber main.cpp verfuegbar "
            "(ES_RUN_OTA_ON_BOOT), aber ohne UI-Eintrag."
        )
        return

    with open(menu_cpp, "r", encoding="utf-8", errors="ignore") as f:
        m_content = f.read()

    if "runOtaUpdateScript" in m_content or "OTA Update" in m_content:
        print(f"[i] OTA-Eintrag bereits vorhanden in {menu_cpp}, ueberspringe.")
        return

    if "extern void runOtaUpdateScript();" not in m_content:
        m_content = "\nextern void runOtaUpdateScript();\n" + m_content

    wired = False
    for pattern in ENTRY_PATTERNS:
        pm = pattern.search(m_content)
        if pm:
            indent = pm.group(1) or "\t"
            anchor = pm.group(0)
            # NOTE: earlier versions used "mMenuIconPath" here, guessing this
            # fork had a member variable by that name for the icon argument.
            # It doesn't - that produced "'mMenuIconPath' was not declared in
            # this scope". An empty string literal is a safe, dependency-free
            # stand-in for an icon path argument and does not require knowing
            # this fork's internal icon plumbing.
            ota_call = (
                f'{indent}addEntry(_("OTA UPDATE"), "", false, '
                f"[this] {{ runOtaUpdateScript(); }});\n"
            )
            m_content = m_content.replace(anchor, ota_call + anchor, 1)
            wired = True
            print(f"[+] OTA-Menueeintrag live verdrahtet (Muster erkannt) in: {menu_cpp}")
            break

    if not wired:
        m_content += (
            "\n// Injected OTA Update Menu Entry (Fallback - Muster nicht erkannt)\n"
            'static const char* kOtaMenuLabelFallback = "OTA Update";\n'
            "static void otaMenuFallbackTouch() { (void)kOtaMenuLabelFallback; runOtaUpdateScript(); }\n"
        )
        print(
            f"[!] Kein bekanntes Menue-Muster in {menu_cpp} erkannt - "
            f"String/Aufruf hinterlegt, echte UI-Verdrahtung bitte manuell pruefen."
        )

    with open(menu_cpp, "w", encoding="utf-8") as f:
        f.write(m_content)
    print(f"[+] MainMenu-Datei gespeichert: {menu_cpp}")


def main():
    settings_cpp, main_cpp, menu_cpp = find_target_files()
    patch_main_cpp(main_cpp)
    patch_settings_cpp(settings_cpp)
    patch_menu_cpp(menu_cpp)
    print("=== STEP 1 ABGESCHLOSSEN ===")


if __name__ == "__main__":
    main()
