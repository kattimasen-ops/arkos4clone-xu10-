#!/bin/bash

if [ "$EUID" -ne 0 ]; then
  echo "[-] Error: Please run this script as root from the ArkOS Tools menu."
  exit 1
fi

TOOLS_DIR="/roms/tools"
cd "$TOOLS_DIR" || exit 1

echo "[+] Starting automated ArkOS4Clone EmulationStation validation..."

# 1. Verify file integrity
MISSING=0
for file in emulationstation resources mcu_led_daemon.sh update_check.sh; do
  if [ ! -e "$file" ]; then
    echo "[-] Missing required file or folder: $file"
    MISSING=1
  fi
done

if [ "$MISSING" -eq 1 ]; then
  echo "[-] CRITICAL: Incomplete files detected in $TOOLS_DIR. Aborting."
  exit 1
fi

# 2. Pre-flight binary execution test (Catches library/GLIBC errors safely)
chmod +x emulationstation
echo "[+] Running local binary compatibility pre-test..."
./emulationstation --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "[-] CRITICAL ABORT: Binary failed compatibility test (GLIBC/Library mismatch)."
  echo "[-] Your system configuration has NOT been touched. Handheld is safe."
  exit 1
fi
echo "[+] Pre-flight check PASSED. Binary is fully compatible."

# 3. Safe system deployment
if [ ! -f /usr/bin/emulationstation.bak ]; then
  echo "[+] Backing up original stock binary..."
  cp /usr/bin/emulationstation /usr/bin/emulationstation.bak
fi

echo "[+] Stopping active UI processes..."
killall emulationstation || true

echo "[+] Deploying new binary and resource assets..."
cp emulationstation /usr/bin/emulationstation
chmod +x /usr/bin/emulationstation

mkdir -p /usr/bin/resources
cp -r resources/* /usr/bin/resources/

cp mcu_led_daemon.sh /usr/bin/mcu_led_daemon.sh
cp update_check.sh /usr/bin/update_check.sh
chmod +x /usr/bin/mcu_led_daemon.sh /usr/bin/update_check.sh

echo "[+] Patch successfully applied. Restarting system..."
sync
reboot