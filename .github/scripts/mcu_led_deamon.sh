#!/bin/bash

# Verhindere mehrfaches Starten des Daemons
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
        EXTRACTED=$(grep -oP 'string name="JoystickLEDMode" value="\K[^"]+' "$SETTINGS_FILE" 2>/dev/null)
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
            # Standard Rainbow / Wave Animation
            HUE=$(( (HUE + 20) % 360 ))
            /usr/bin/mcu_led 0 180 255
            sleep 1
            ;;
    esac
done