#!/bin/bash
# OTA Update check & installation trigger for ArkOS4Clones
# Fetches latest release from lcdyk0517/arkos4clone, downloads assets,
# and places them in the correct partitions for automatic update on next boot.

set -euo pipefail

LOGFILE="/tmp/ota_update.log"
REPO="lcdyk0517/arkos4clone"
VERSION_FILE="/home/ark/.emulationstation/es_version"   # adjust if needed

echo "[OTA] Check initiated on $(date)" > "$LOGFILE"

# ----------------------------------------------------------------------
# 1. Get latest release info from GitHub API
# ----------------------------------------------------------------------
echo "[OTA] Fetching latest release info..." >> "$LOGFILE"
LATEST_RELEASE_JSON=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest")
LATEST_TAG=$(echo "$LATEST_RELEASE_JSON" | grep -oP '"tag_name":\s*"\K[^"]+' || true)

if [ -z "$LATEST_TAG" ]; then
    echo "[OTA] Could not fetch latest release. Aborting." >> "$LOGFILE"
    exit 1
fi

echo "[OTA] Latest release: $LATEST_TAG" >> "$LOGFILE"

# ----------------------------------------------------------------------
# 2. Compare with current version (if stored)
# ----------------------------------------------------------------------
CURRENT_TAG=""
if [ -f "$VERSION_FILE" ]; then
    CURRENT_TAG=$(cat "$VERSION_FILE")
fi

if [ "$CURRENT_TAG" == "$LATEST_TAG" ]; then
    echo "[OTA] Already up to date ($CURRENT_TAG)." >> "$LOGFILE"
    exit 0
fi

# ----------------------------------------------------------------------
# 3. Extract asset download URLs
# ----------------------------------------------------------------------
# Parse JSON for asset names and browser_download_url
ASSET_URLS=$(echo "$LATEST_RELEASE_JSON" | jq -r '.assets[] | "\(.name)|\(.browser_download_url)"')

FIRSTBOOT_URL=""
UPDATE_URL=""

while IFS= read -r line; do
    NAME=$(echo "$line" | cut -d'|' -f1)
    URL=$(echo "$line" | cut -d'|' -f2)
    if [ "$NAME" == "firstboot.sh" ]; then
        FIRSTBOOT_URL="$URL"
    elif [ "$NAME" == "update-arkos.tar" ]; then
        UPDATE_URL="$URL"
    fi
done <<< "$ASSET_URLS"

if [ -z "$FIRSTBOOT_URL" ] || [ -z "$UPDATE_URL" ]; then
    echo "[OTA] Required assets not found in release. Aborting." >> "$LOGFILE"
    exit 1
fi

echo "[OTA] Downloading firstboot.sh..." >> "$LOGFILE"
curl -L -o /tmp/firstboot.sh "$FIRSTBOOT_URL"

echo "[OTA] Downloading update-arkos.tar..." >> "$LOGFILE"
curl -L -o /tmp/update-arkos.tar "$UPDATE_URL"

# ----------------------------------------------------------------------
# 4. Verify downloads are valid (check file size)
# ----------------------------------------------------------------------
if [ ! -s /tmp/firstboot.sh ] || [ ! -s /tmp/update-arkos.tar ]; then
    echo "[OTA] Download failed (empty file). Aborting." >> "$LOGFILE"
    exit 1
fi

# ----------------------------------------------------------------------
# 5. Locate and mount the BOOT partition (if not already mounted)
# ----------------------------------------------------------------------
echo "[OTA] Preparing BOOT partition..." >> "$LOGFILE"

# Check if /boot is already mounted (it usually is on ArkOS)
if ! mountpoint -q /boot; then
    echo "[OTA] /boot not mounted. Attempting to mount..." >> "$LOGFILE"
    # Find the boot partition device (common on SD: /dev/mmcblk0p1 or /dev/root)
    # Try common patterns. If it fails, prompt user.
    # BUGFIX: the previous line's "2>/dev/null || true" was attached to a
    # bare variable assignment (no command being run at that point), so it
    # had no actual effect - harmless, but confusing. Cleaned up.
    BOOT_DEV="$(ls /dev/mmcblk* 2>/dev/null | head -n1 | sed 's/p[0-9]*$//')p1"
    if [ -z "$BOOT_DEV" ] || [ "$BOOT_DEV" = "p1" ]; then
        # Fallback to typical first partition
        BOOT_DEV="/dev/mmcblk0p1"
    fi
    if [ ! -b "$BOOT_DEV" ]; then
        echo "[OTA] Could not find BOOT partition device. Please mount manually and re-run." >> "$LOGFILE"
        exit 1
    fi
    # CAUTION: this is a heuristic guess, not a verified boot partition.
    # Mounting and writing to the wrong block device can damage the
    # device's boot chain. If this ever runs on a layout other than the
    # single-SD-card default (e.g. booting from eMMC, or a differently
    # numbered partition), verify BOOT_DEV manually before trusting this.
    echo "[OTA] Detected boot device candidate: $BOOT_DEV" >> "$LOGFILE"
    mkdir -p /mnt/boot
    mount "$BOOT_DEV" /mnt/boot || {
        echo "[OTA] Failed to mount $BOOT_DEV on /mnt/boot." >> "$LOGFILE"
        exit 1
    }
else
    # If /boot is already mounted, it might be read-only? Assume it's writable.
    BOOT_DIR="/boot"
fi

# Determine actual boot directory
BOOT_DIR="${BOOT_DIR:-/mnt/boot}"

# ----------------------------------------------------------------------
# 6. Copy firstboot.sh to boot partition
# ----------------------------------------------------------------------
echo "[OTA] Copying firstboot.sh to $BOOT_DIR/" >> "$LOGFILE"
cp -f /tmp/firstboot.sh "$BOOT_DIR/firstboot.sh"
chmod +x "$BOOT_DIR/firstboot.sh"

# ----------------------------------------------------------------------
# 7. Locate and copy update-arkos.tar to Easyroms folder
# ----------------------------------------------------------------------
echo "[OTA] Searching for Easyroms directory..." >> "$LOGFILE"
# Common locations on ArkOS
if [ -d "/home/ark/Easyroms" ]; then
    EASYROMS="/home/ark/Easyroms"
elif [ -d "/roms" ]; then
    # Check for tools subfolder as fallback
    if [ -d "/roms/tools" ]; then
        EASYROMS="/roms/tools"
    else
        EASYROMS="/roms"
    fi
else
    echo "[OTA] Easyroms directory not found. Please ensure it exists." >> "$LOGFILE"
    exit 1
fi

echo "[OTA] Copying update-arkos.tar to $EASYROMS/" >> "$LOGFILE"
cp -f /tmp/update-arkos.tar "$EASYROMS/update-arkos.tar"

# ----------------------------------------------------------------------
# 8. Update version file
# ----------------------------------------------------------------------
echo "$LATEST_TAG" > "$VERSION_FILE"
echo "[OTA] Version file updated to $LATEST_TAG" >> "$LOGFILE"

# ----------------------------------------------------------------------
# 9. Cleanup and final message
# ----------------------------------------------------------------------
rm -f /tmp/firstboot.sh /tmp/update-arkos.tar
echo "[OTA] Update staged. Reboot device to apply update." >> "$LOGFILE"
echo "[OTA] Done."

# You may want to trigger a reboot or let the user do it.
# Uncomment the following line for automatic reboot (optional)
# reboot
