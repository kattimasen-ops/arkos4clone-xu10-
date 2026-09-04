#!/bin/bash

# Verhindere mehrfaches Starten des Daemons
PIDFILE="/tmp/mcu_led_daemon.pid"[cite: 4]
if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then[cite: 4]
    exit 0[cite: 4]
fi
echo $$ > "$PIDFILE"[cite: 4]

SETTINGS_FILE="/home/ark/.emulationstation/es_settings.xml"[cite: 4]
[ ! -f "$SETTINGS_FILE" ] && SETTINGS_FILE="/storage/.config/emulationstation/es_settings.xml"[cite: 4]

HUE=0[cite: 4]

while true; do[cite: 4]
    MODE="rainbow_wave"[cite: 4]
    if [ -f "$SETTINGS_FILE" ]; then[cite: 4]
        EXTRACTED=$(grep -oP 'string name="JoystickLEDMode" value="\K[^"]+' "$SETTINGS_FILE" 2>/dev/null)[cite: 4]
        [ -n "$EXTRACTED" ] && MODE="$EXTRACTED"[cite: 4]
    fi

    case "$MODE" in[cite: 4]
        "battery_status")[cite: 4]
            CAP=100[cite: 4]
            [ -f /sys/class/power_supply/battery/capacity ] && CAP=$(cat /sys/class/power_supply/battery/capacity)[cite: 4]
            if [ "$CAP" -ge 60 ]; then[cite: 4]
                /usr/bin/mcu_led 0 255 0[cite: 4]
            elif [ "$CAP" -ge 25 ]; then[cite: 4]
                /usr/bin/mcu_led 255 150 0[cite: 4]
            else
                /usr/bin/mcu_led 255 0 0[cite: 4]
            fi
            sleep 10[cite: 4]
            ;;
        "strobe_party"|"police"|"disco")[cite: 4]
            R=$((RANDOM % 256))[cite: 4]
            G=$((RANDOM % 256))[cite: 4]
            B=$((RANDOM % 256))[cite: 4]
            /usr/bin/mcu_led $R $G $B[cite: 4]
            sleep 0.3[cite: 4]
            ;;
        "fire")[cite: 4]
            R=$((RANDOM % 256))[cite: 4]
            G=$((RANDOM % 80))[cite: 4]
            /usr/bin/mcu_led $R $G 0[cite: 4]
            sleep 0.2[cite: 4]
            ;;
        *)
            # Standard Rainbow / Wave Animation
            HUE=$(( (HUE + 20) % 360 ))[cite: 4]
            /usr/bin/mcu_led 0 180 255[cite: 4]
            sleep 1[cite: 4]
            ;;
    esac
done[cite: 4]
