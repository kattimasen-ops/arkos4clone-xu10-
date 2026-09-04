#!/usr/bin/env bash
# ==============================================================================
# update_check.sh - ArkOS4Clones Automated OTA Update Engine
# ==============================================================================
#  - Scans GitHub API for new ArkOS4Clones releases
#  - Displays release changelog notes
#  - Downloads update-arkos.tar and firstboot.sh into /boot/ for system execution
# ==============================================================================

set -euo pipefail

LOGFILE="/tmp/ota_update.log"
MARKER_FILE="/etc/arkos4clones_version"
REPO_OWNER="arkos4clones"
REPO_NAME="arkos4clones"
BOOT_DIR="/boot"

exec > >(tee -a "$LOGFILE") 2>&1

echo "=================================================="
echo " ArkOS4Clones OTA Update Check: $(date)"
echo "=================================================="

CURRENT_VERSION="v0.0.0"
if [ -f "$MARKER_FILE" ]; then
    CURRENT_VERSION="$(cat "$MARKER_FILE" | tr -d ' \n\r')"
fi
echo "[+] Currently installed version: ${CURRENT_VERSION}"

echo "[+] Querying GitHub API for latest release..."
API_RESPONSE=$(curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases/latest" || true)

if [ -z "$API_RESPONSE" ] || echo "$API_RESPONSE" | grep -q "Not Found"; then
    echo "[!] ERROR: Could not fetch release data from GitHub repository (${REPO_OWNER}/${REPO_NAME})."
    exit 1
fi

LATEST_TAG=$(echo "$API_RESPONSE" | jq -r '.tag_name // empty')
CHANGELOG=$(echo "$API_RESPONSE" | jq -r '.body // "No release notes provided."')

if [ -z "$LATEST_TAG" ]; then
    echo "[!] ERROR: Failed to parse latest tag from release API."
    exit 1
fi

echo "[+] Latest available version: ${LATEST_TAG}"

if [ "$CURRENT_VERSION" == "$LATEST_TAG" ]; then
    echo "[✓] Your system is already up to date (${CURRENT_VERSION})!"
    exit 0
fi

echo "=================================================="
echo " NEW UPDATE AVAILABLE: ${LATEST_TAG}"
echo "=================================================="
echo "Changelog:"
echo "${CHANGELOG}"
echo "=================================================="

# Extract asset URLs for update-arkos.tar and firstboot.sh
TAR_URL=$(echo "$API_RESPONSE" | jq -r '.assets[] | select(.name=="update-arkos.tar") | .browser_download_url')
FIRSTBOOT_URL=$(echo "$API_RESPONSE" | jq -r '.assets[] | select(.name=="firstboot.sh") | .browser_download_url')

if [ -z "$TAR_URL" ] || [ -z "$FIRSTBOOT_URL" ]; then
    echo "[!] ERROR: Release assets (update-arkos.tar / firstboot.sh) were not found in release ${LATEST_TAG}!"
    exit 1
fi

echo "[+] Staging download payload into ${BOOT_DIR}..."

# Download update payload
curl -L -o "${BOOT_DIR}/update-arkos.tar" "$TAR_URL"
echo "    [✓] Downloaded update-arkos.tar"

curl -L -o "${BOOT_DIR}/firstboot.sh" "$FIRSTBOOT_URL"
chmod +x "${BOOT_DIR}/firstboot.sh"
echo "    [✓] Downloaded firstboot.sh"

# Update local marker
echo "${LATEST_TAG}" > "$MARKER_FILE"

echo "=================================================="
echo "[✓] OTA Update payloads successfully installed to ${BOOT_DIR}!"
echo "[!] Reboot your device now to apply the update."
echo "=================================================="
