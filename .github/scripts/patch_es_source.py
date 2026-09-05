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

# --------------------------------------------------------------------------
# SIGSEGV/SIGABRT/SIGFPE/SIGILL crash handler with backtrace.
#
# Prints a real function-name backtrace (the binary is confirmed
# not-stripped, so symbol names resolve) to /home/ark/es_crash.log before
# the process dies, instead of a bare boot-loop with no diagnostic info.
# Includes fallback routing to /tmp/es_crash.log and /dev/tty1 if the
# filesystem drops to read-only during an SD card fault.
#
# Installed via a static-init object rather than a call inserted inside
# main()'s body: a global object's constructor runs before main() starts
# (guaranteed for objects in the same translation unit as main), so this
# just needs to be prepended to main.cpp - no regex-based "find the right
# line inside main() to inject after" fragility required at all.
#
# backtrace() itself is warmed up once during that constructor (glibc can
# lazily dlopen its unwinder on first call, which is not safe to do for
# the first time from inside a signal handler) so the crash-time call is
# already primed and safe.
# --------------------------------------------------------------------------
CRASH_HANDLER_CODE = r"""
// === ES_CUSTOM_PATCH: crash handler ===
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <execinfo.h>
#include <fcntl.h>
#include <unistd.h>

namespace {
    void es_crash_signal_handler(int sig) {
        int fd = open("/home/ark/es_crash.log", O_WRONLY | O_CREAT | O_APPEND, 0644);
        if (fd < 0) {
            fd = open("/tmp/es_crash.log", O_WRONLY | O_CREAT | O_APPEND, 0644);
        }
        int tty_fd = open("/dev/tty1", O_WRONLY | O_APPEND);

        const char* header = "\n[CRASH] EmulationStation caught a fatal signal\n";
        if (fd >= 0) write(fd, header, strlen(header));
        if (tty_fd >= 0) write(tty_fd, header, strlen(header));

        const char* sig_name =
            (sig == SIGSEGV) ? "SIGSEGV (segmentation fault)\n" :
            (sig == SIGABRT) ? "SIGABRT (abort)\n" :
            (sig == SIGFPE)  ? "SIGFPE (floating point exception)\n" :
            (sig == SIGILL)  ? "SIGILL (illegal instruction)\n" :
                                "unknown signal\n";
        
        if (fd >= 0) write(fd, sig_name, strlen(sig_name));
        if (tty_fd >= 0) write(tty_fd, sig_name, strlen(sig_name));

        void* bt[64];
        int n = backtrace(bt, 64);
        if (fd >= 0) backtrace_symbols_fd(bt, n, fd);
        if (tty_fd >= 0) backtrace_symbols_fd(bt, n, tty_fd);

        if (fd >= 0) close(fd);
        if (tty_fd >= 0) close(tty_fd);

        // Re-raise with the default handler so the OS still records/handles
        // the crash normally (correct exit status, core dump if enabled).
        signal(sig, SIG_DFL);
        raise(sig);
    }

    struct EsCrashHandlerInstaller {
        EsCrashHandlerInstaller() {
            void* warmup[4];
            backtrace(warmup, 4);

            signal(SIGSEGV, es_crash_signal_handler);
            signal(SIGABRT, es_crash_signal_handler);
            signal(SIGFPE, es_crash_signal_handler);
            signal(SIGILL, es_crash_signal_handler);
        }
    } es_crash_handler_installer_instance;
}
// === END ES_CUSTOM_PATCH: crash handler ===
"""


def find_main_entry(cpp_h_files, guis_dir):
    """Find the file with the real int main() entry point, preferring the
    same src/ subtree as the guis/ folder to avoid a vendored submodule's
    unrelated main.cpp (only relevant if this fork has submodules)."""
    def has_main(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return re.search(r"int\s+main\s*\(", f.read()) is not None
        except OSError:
            return False

    search_root = None
    if guis_dir:
        parts = guis_dir.replace(os.sep, "/").split("/")
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


def patch_crash_handler():
    source_root = get_source_root()

    all_cpp_h = []
    for root, _, files in os.walk(source_root):
        for file in files:
            if file.endswith((".cpp", ".h")):
                all_cpp_h.append(os.path.join(root, file))

    guis_dir = os.path.join(source_root, "es-app", "src", "guis")
    guis_dir = guis_dir if os.path.exists(guis_dir) else None

    main_cpp = find_main_entry(all_cpp_h, guis_dir)
    if not main_cpp:
        print("[!] Could not locate main.cpp with a real int main() - skipping crash handler.")
        return

    with open(main_cpp, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if "ES_CUSTOM_PATCH: crash handler" in content:
        print(f"[i] Crash handler already present in {main_cpp}, skipping.")
        return

    content = CRASH_HANDLER_CODE.strip() + "\n\n" + content
    with open(main_cpp, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Injected SIGSEGV/SIGABRT/SIGFPE/SIGILL backtrace handler into: {main_cpp}")
    print("    Crash backtraces will be appended to /home/ark/es_crash.log, /tmp/, or /dev/tty1")


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
    patch_crash_handler()
    patch_joystick_menu()
