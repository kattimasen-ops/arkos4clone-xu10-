#!/usr/bin/env bash
# ==============================================================================
# update_check.sh - ArkOS4Clones Automated OTA Update Engine
# ==============================================================================
# Features:
#  - Queries GitHub API for new ArkOS4Clones release tags
#  - Downloads update-arkos.tar into /Easyroms/tools/
#  - Downloads firstboot.sh into /boot/ (Boot Partition)
# ==============================================================================

set -euo pipefail

LOGFILE="/tmp/ota_update.log"
MARKER_FILE="/etc/arkos4clones_version"
REPO_OWNER="arkos4clones"
REPO_NAME="arkos4clones"
BOOT_DIR="/boot"

# Resolve Easyroms tools directory with fallbacks for SD1/SD2 mount variations
TOOLS_DIR="/Easyroms/tools"
if [ ! -d "/Easyroms" ]; then
    if [ -d "/roms/tools" ]; then
        TOOLS_DIR="/roms/tools"
    elif [ -d "/roms2/tools" ]; then
        TOOLS_DIR="/roms2/tools"
    fi
fi

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

TAR_URL=$(echo "$API_RESPONSE" | jq -r '.assets[] | select(.name=="update-arkos.tar") | .browser_download_url')
FIRSTBOOT_URL=$(echo "$API_RESPONSE" | jq -r '.assets[] | select(.name=="firstboot.sh") | .browser_download_url')

if [ -z "$TAR_URL" ] || [ -z "$FIRSTBOOT_URL" ]; then
    echo "[!] ERROR: Release assets (update-arkos.tar / firstboot.sh) were not found in release ${LATEST_TAG}!"
    exit 1
fi

# Ensure staging target directories exist
mkdir -p "$TOOLS_DIR"
mkdir -p "$BOOT_DIR"

echo "[+] Staging download payloads..."

# Download update-arkos.tar into /Easyroms/tools/
echo "    -> Downloading update-arkos.tar to ${TOOLS_DIR}..."
curl -L -o "${TOOLS_DIR}/update-arkos.tar" "$TAR_URL"
echo "       [✓] Downloaded update-arkos.tar"

# Download firstboot.sh into Boot Partition (/boot/)
echo "    -> Downloading firstboot.sh to ${BOOT_DIR}..."
curl -L -o "${BOOT_DIR}/firstboot.sh" "$FIRSTBOOT_URL"
chmod +x "${BOOT_DIR}/firstboot.sh"
echo "       [✓] Downloaded firstboot.sh"

# Update local version marker
echo "${LATEST_TAG}" > "$MARKER_FILE"

echo "=================================================="
echo "[✓] Update archive placed in: ${TOOLS_DIR}/update-arkos.tar"
echo "[✓] Firstboot script placed in: ${BOOT_DIR}/firstboot.sh"
echo "[!] Reboot your device now to trigger the ArkOS update handler."
echo "=================================================="
