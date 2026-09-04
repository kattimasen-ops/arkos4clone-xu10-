#!/usr/bin/env bash
# ==============================================================================
# install_es_update.sh - ArkOS Verified Atomic Deployer & Daemon Lifecycle Engine
# ==============================================================================

set -euo pipefail

# Command Line Flags
FORCE=false
NO_REBOOT=false

for arg in "$@"; do
    case "$arg" in
        -f|--force) FORCE=true ;;
        -n|--no-reboot) NO_REBOOT=true ;;
    esac
done

# 1. Root Execution Check
if [ "$(id -u)" -ne 0 ]; then
    echo "[!] ERROR: Must be run as root (e.g., sudo ./install_es_update.sh)" >&2
    exit 1
fi

SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
WORKING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="/home/ark/es_backup_${TIMESTAMP}"
MARKER_FILE="/etc/es_installed.marker"
NEW_BIN="${WORKING_DIR}/emulationstation"

echo "=================================================="
echo "   ArkOS Verified ES & Daemon Deployer            "
echo "=================================================="

# ------------------------------------------------------------------------------
# 2. PRE-FLIGHT VALIDATION PHASE
# ------------------------------------------------------------------------------
echo "[+] Step 1: Performing Pre-Flight Safety Inspections..."

if [ ! -f "${NEW_BIN}" ]; then
    echo "[!] PRE-FLIGHT ERROR: 'emulationstation' binary missing from package folder!" >&2
    exit 1
fi

echo "    -> Verifying binary architecture..."
BIN_TYPE="$(file -b "${NEW_BIN}" || true)"
if ! echo "${BIN_TYPE}" | grep -qE "ARM|aarch64"; then
    echo "[!] PRE-FLIGHT ERROR: Binary is not compiled for ARM64/aarch64!" >&2
    echo "    Detected format: ${BIN_TYPE}" >&2
    exit 1
fi
echo "       [✓] Binary format verified: ARM 64-bit ELF"

# --------------------------------------------------------------------------
# BUGFIX: /usr/bin/emulationstation is a DIRECTORY on this device
# (confirmed from arkos4clone's own build/install script), containing the
# real binary at /usr/bin/emulationstation/emulationstation. Every
# previous version of this detection used `[ -f "${TARGET_BIN}" ]` against
# "/usr/bin/emulationstation" directly - that test is FALSE for a
# directory, so it silently skipped, and every later step in the script
# (backup, the "identical binary" check, and critically the final `mv`
# atomic swap) operated against a directory path instead of the real
# file. `mv new_file existing_directory` moves the file INTO that
# directory under its own name rather than replacing it - so the real
# target path was NEVER actually written, leaving whatever was already
# there (broken) untouched. That's almost certainly why the boot loop
# survived every previous install attempt.
# --------------------------------------------------------------------------
CANDIDATE_BIN="/usr/bin/emulationstation"
if [ -d "${CANDIDATE_BIN}" ] && [ -f "${CANDIDATE_BIN}/emulationstation" ]; then
    TARGET_BIN="${CANDIDATE_BIN}/emulationstation"
elif [ -f "${CANDIDATE_BIN}" ] && file "${CANDIDATE_BIN}" | grep -q "shell script"; then
    echo "    -> Launch wrapper script detected at ${CANDIDATE_BIN}"
    if [ -f "/usr/bin/emulationstation.exe" ]; then
        TARGET_BIN="/usr/bin/emulationstation.exe"
    elif [ -f "/usr/bin/emulationstation.bin" ]; then
        TARGET_BIN="/usr/bin/emulationstation.bin"
    else
        TARGET_BIN="${CANDIDATE_BIN}"
    fi
else
    TARGET_BIN="${CANDIDATE_BIN}"
fi
TARGET_DIR="$(dirname "${TARGET_BIN}")"
echo "       [✓] Target destination set to: ${TARGET_BIN}"

TARGET_LIB_DIR="/usr/lib/aarch64-linux-gnu"
if [ ! -d "${TARGET_LIB_DIR}" ]; then
    TARGET_LIB_DIR="/usr/lib"
fi

echo "    -> Auditing shared library linkages (ldd check)..."
MISSING_LIBS=$(LD_LIBRARY_PATH="${WORKING_DIR}:${TARGET_LIB_DIR}:/usr/lib" ldd "${NEW_BIN}" 2>&1 | grep "not found" || true)

if [ -n "${MISSING_LIBS}" ]; then
    echo "[!] PRE-FLIGHT ERROR: Binary has missing shared library dependencies!" >&2
    echo "${MISSING_LIBS}" >&2
    echo "    Aborting installation to prevent boot loops." >&2
    exit 1
fi
echo "       [✓] All dynamic library dependencies satisfied."

if [ -f "${TARGET_BIN}" ]; then
    OLD_HASH="$(md5sum "${TARGET_BIN}" | awk '{print $1}')"
    NEW_HASH="$(md5sum "${NEW_BIN}" | awk '{print $1}')"

    if [ "${OLD_HASH}" == "${NEW_HASH}" ]; then
        echo "[!] WARNING: Executable binary is IDENTICAL to the currently installed version."
        if [ "$FORCE" = false ]; then
            if [ -t 0 ]; then
                read -p "    Proceed with script/library deployment anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo "[-] Installation cancelled by user."
                    exit 0
                fi
            else
                echo "    [i] Non-interactive execution detected; defaulting to proceed with asset update."
            fi
        fi
    fi
fi

if [ -d "${WORKING_DIR}/resources" ]; then
    RESOURCE_COUNT=$(find "${WORKING_DIR}/resources" -mindepth 1 | wc -l)
    if [ "${RESOURCE_COUNT}" -eq 0 ]; then
        echo "[!] PRE-FLIGHT ERROR: 'resources' directory exists but is completely empty!" >&2
        exit 1
    fi
    echo "       [✓] Package resources directory verified (${RESOURCE_COUNT} items)"
fi

# ------------------------------------------------------------------------------
# 3. BACKUP PHASE
# ------------------------------------------------------------------------------
echo "[+] Step 2: Creating safety backup in ${BACKUP_DIR}..."
mkdir -p "${BACKUP_DIR}/libs" "${BACKUP_DIR}/scripts"

if [ -f "${TARGET_BIN}" ]; then
    cp -p "${TARGET_BIN}" "${BACKUP_DIR}/emulationstation.bak"
    echo "       [✓] Binary backed up."
else
    echo "       [WARNUNG] Keine bestehende Binary unter ${TARGET_BIN} gefunden - kein Backup moeglich."
fi

# BUGFIX: resources live alongside the binary (TARGET_DIR/resources), not
# hardcoded at /usr/bin/resources - same directory-layout issue as above.
if [ -d "${TARGET_DIR}/resources" ]; then
    cp -a "${TARGET_DIR}/resources" "${BACKUP_DIR}/resources.bak"
fi

shopt -s nullglob
for lib in "${WORKING_DIR}"/*.so*; do
    if [ -e "${lib}" ]; then
        LIB_NAME="$(basename "${lib}")"
        if [ -e "${TARGET_LIB_DIR}/${LIB_NAME}" ]; then
            cp -dP "${TARGET_LIB_DIR}/${LIB_NAME}" "${BACKUP_DIR}/libs/" 2>/dev/null || true
        fi
    fi
done
shopt -u nullglob

# ------------------------------------------------------------------------------
# 4. ATOMIC STAGING PHASE (.new files)
# ------------------------------------------------------------------------------
echo "[+] Step 3: Staging new files on disk..."

cp -f "${NEW_BIN}" "${TARGET_BIN}.new"
chmod 755 "${TARGET_BIN}.new"
chown root:root "${TARGET_BIN}.new"

if [ -d "${WORKING_DIR}/resources" ]; then
    rm -rf "${TARGET_DIR}/resources.new"
    cp -a "${WORKING_DIR}/resources" "${TARGET_DIR}/resources.new"
    chmod -R 755 "${TARGET_DIR}/resources.new"
    chown -R root:root "${TARGET_DIR}/resources.new"
fi

shopt -s nullglob
for lib in "${WORKING_DIR}"/*.so*; do
    if [ -e "${lib}" ]; then
        LIB_NAME="$(basename "${lib}")"
        cp -dP "${lib}" "${TARGET_LIB_DIR}/${LIB_NAME}.new"
    fi
done

for script in "${WORKING_DIR}"/*.sh; do
    if [ -e "${script}" ]; then
        SCRIPT_NAME_ITEM="$(basename "${script}")"
        if [ "${SCRIPT_NAME_ITEM}" != "${SCRIPT_NAME}" ]; then
            cp -f "${script}" "/usr/local/bin/${SCRIPT_NAME_ITEM}.new"
            chmod 755 "/usr/local/bin/${SCRIPT_NAME_ITEM}.new"
            chown root:root "/usr/local/bin/${SCRIPT_NAME_ITEM}.new"
        fi
    fi
done
shopt -u nullglob

# ------------------------------------------------------------------------------
# 5. ATOMIC SWAP PHASE
# ------------------------------------------------------------------------------
echo "[+] Step 4: Performing atomic inode replacement..."

shopt -s nullglob
for lib_new in "${TARGET_LIB_DIR}"/*.so*.new; do
    REAL_LIB="${lib_new%.new}"
    mv -f "${lib_new}" "${REAL_LIB}"
done
shopt -u nullglob

ldconfig 2>/dev/null || true

shopt -s nullglob
for script_new in /usr/local/bin/*.sh.new; do
    REAL_SCRIPT="${script_new%.new}"
    mv -f "${script_new}" "${REAL_SCRIPT}"
done
shopt -u nullglob

if [ -d "${TARGET_DIR}/resources.new" ]; then
    if [ -d "${TARGET_DIR}/resources" ]; then
        mv -f "${TARGET_DIR}/resources" "${TARGET_DIR}/resources.old_${TIMESTAMP}"
    fi
    mv -f "${TARGET_DIR}/resources.new" "${TARGET_DIR}/resources"
    rm -rf "${TARGET_DIR}/resources.old_${TIMESTAMP}" 2>/dev/null || true
fi

if [ -f "${TARGET_BIN}" ]; then
    mv -f "${TARGET_BIN}" "${TARGET_BIN}.old_${TIMESTAMP}"
fi
mv -f "${TARGET_BIN}.new" "${TARGET_BIN}"
rm -f "${TARGET_BIN}.old_${TIMESTAMP}" 2>/dev/null || true

if [ ! -x "${TARGET_BIN}" ]; then
    echo "[!] POST-SWAP ERROR: ${TARGET_BIN} is not executable after the swap!" >&2
    exit 1
fi
echo "       [✓] ${TARGET_BIN} is in place and executable."

# ------------------------------------------------------------------------------
# 6. DAEMON & BOOT INITIALIZATION PHASE
# ------------------------------------------------------------------------------
echo "[+] Step 5: Managing LED Daemon and Autostart hooks..."

# BUGFIX: the previous `sed -i -e '$i \...&\n'` one-liner does not reliably
# turn "\n" into an actual newline across sed dialects/versions - it could
# insert the daemon-launch line followed by literal backslash-n characters
# rather than a real line break. Rewritten with a temp-file based insert
# that has no such ambiguity.
if [ -f /etc/rc.local ] && ! grep -q "mcu_led_daemon.sh" /etc/rc.local; then
    RC_LOCAL_TMP="$(mktemp)"
    LAST_LINE_NUM="$(wc -l < /etc/rc.local)"
    if [ "${LAST_LINE_NUM}" -gt 0 ]; then
        head -n -1 /etc/rc.local > "${RC_LOCAL_TMP}"
        echo "/usr/local/bin/mcu_led_daemon.sh &" >> "${RC_LOCAL_TMP}"
        tail -n 1 /etc/rc.local >> "${RC_LOCAL_TMP}"
    else
        cat /etc/rc.local > "${RC_LOCAL_TMP}"
        echo "/usr/local/bin/mcu_led_daemon.sh &" >> "${RC_LOCAL_TMP}"
    fi
    cat "${RC_LOCAL_TMP}" > /etc/rc.local
    rm -f "${RC_LOCAL_TMP}"
    chmod +x /etc/rc.local
    echo "       [✓] Registered mcu_led_daemon.sh in /etc/rc.local"
fi

# Restart daemon if script was updated
if [ -f "/usr/local/bin/mcu_led_daemon.sh" ]; then
    echo "    -> Restarting active MCU LED Daemon..."
    pkill -f "mcu_led_daemon.sh" 2>/dev/null || true
    nohup /usr/local/bin/mcu_led_daemon.sh > /dev/null 2>&1 &
    echo "       [✓] LED Daemon restarted successfully."
fi

# ------------------------------------------------------------------------------
# 7. MARKER & FINALIZATION
# ------------------------------------------------------------------------------
cat << EOF > "${MARKER_FILE}"
INSTALLED_DATE="${TIMESTAMP}"
SOURCE_PACKAGE="${WORKING_DIR}"
TARGET_BINARY="${TARGET_BIN}"
BINARY_HASH="$(md5sum "${TARGET_BIN}" | awk '{print $1}')"
VERIFIED_ARCH="ARM64"
EOF
chmod 644 "${MARKER_FILE}"

echo "=================================================="
echo "[✓] ALL pre-flight checks, atomic swaps, and daemon updates SUCCESSFUL!"
echo "[✓] Safety backup preserved at: ${BACKUP_DIR}"
echo "[✓] Marker logged at: ${MARKER_FILE}"
sync

if [ "$NO_REBOOT" = true ]; then
    echo "[!] Skipping system reboot (--no-reboot flag supplied)."
    exit 0
fi

echo "    Restarting handheld in 3 seconds..."
echo "=================================================="
sleep 3
reboot
