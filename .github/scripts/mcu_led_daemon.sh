#!/bin/bash
# MCU LED Daemon for ArkOS4clones - Stock Compatible + Custom Modes

# BUGFIX: no duplicate-instance guard existed here. install_es_update.sh
# does pkill any existing instance before relaunching, but this makes the
# script safe to run standalone too (e.g. if rc.local or something else
# ever launches it a second time without going through the installer).
PIDFILE="/tmp/mcu_led_daemon.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    exit 0
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

SETTINGS_FILE="/home/ark/.emulationstation/es_settings.xml"
HUE=0

get_mode() {
    if [ -f "$SETTINGS_FILE" ]; then
        # BUGFIX: grep -P (PCRE lookbehind) requires GNU grep. Many
        # embedded ArkOS-style rootfs images use BusyBox grep, which does
        # not support -P - it would either error or silently match
        # nothing, making get_mode() always fall back to "off" regardless
        # of what the user picked in the menu. sed works everywhere.
        MODE=$(sed -n 's/.*<string name="JoystickLED" value="\([^"]*\)".*/\1/p' "$SETTINGS_FILE" 2>/dev/null | head -n1)
        if [ -z "$MODE" ]; then
            MODE=$(sed -n 's/.*<string name="JoystickLEDMode" value="\([^"]*\)".*/\1/p' "$SETTINGS_FILE" 2>/dev/null | head -n1)
        fi
        echo "${MODE:-off}"
    else
        echo "off"
    fi
}

set_rgb() {
    /usr/bin/mcu_led "$1" "$2" "$3" 2>/dev/null
}

while true; do
    CURRENT_MODE=$(get_mode)

    case "$CURRENT_MODE" in
        "off")
            set_rgb 0 0 0
            sleep 1
            ;;

        # --- STOCK STATIC MODES ---
        "static_red"|"red")          set_rgb 255 0 0; sleep 1 ;;
        "static_green"|"green")      set_rgb 0 255 0; sleep 1 ;;
        "static_blue"|"blue")        set_rgb 0 0 255; sleep 1 ;;
        "static_yellow"|"yellow")    set_rgb 255 200 0; sleep 1 ;;
        "static_cyan"|"cyan")        set_rgb 0 255 255; sleep 1 ;;
        "static_purple"|"purple")    set_rgb 180 0 255; sleep 1 ;;
        "static_white"|"white")      set_rgb 255 255 255; sleep 1 ;;

        # --- STOCK BREATHING MODES ---
        "breathing_red")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb $i 0 0; sleep 0.03
            done
            ;;
        "breathing_green")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb 0 $i 0; sleep 0.03
            done
            ;;
        "breathing_blue"|"breathing")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb 0 0 $i; sleep 0.03
            done
            ;;
        "breathing_yellow")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb $i $((i*80/100)) 0; sleep 0.03
            done
            ;;
        "breathing_cyan")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb 0 $i $i; sleep 0.03
            done
            ;;
        "breathing_purple")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb $i 0 $i; sleep 0.03
            done
            ;;
        "breathing_white")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb $i $i $i; sleep 0.03
            done
            ;;

        # --- STOCK FLOW / RAINBOW MODES ---
        "flow"|"rainbow")
            HUE=$(( (HUE + 10) % 360 ))
            R=$(( (HUE * 255) / 360 ))
            G=$(( 255 - R ))
            set_rgb $R $G 180
            sleep 0.08
            ;;

        # --- NEW CUSTOM MODES ---
        "rainbow_wave")
            HUE=$(( (HUE + 15) % 360 ))
            set_rgb $(( (HUE * 255) / 360 )) 120 220
            sleep 0.05
            ;;

        "battery_status")
            CAP=100
            [ -f /sys/class/power_supply/battery/capacity ] && CAP=$(cat /sys/class/power_supply/battery/capacity)
            if [ "$CAP" -ge 60 ]; then
                set_rgb 0 255 0
            elif [ "$CAP" -ge 25 ]; then
                set_rgb 255 150 0
            else
                set_rgb 255 0 0
            fi
            sleep 2
            ;;

        "fire")
            set_rgb $((150 + RANDOM % 106)) $((RANDOM % 50)) 0
            sleep 0.08
            ;;

        "strobe_party"|"disco")
            set_rgb $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256))
            sleep 0.08
            ;;

        "police")
            set_rgb 255 0 0; sleep 0.12
            set_rgb 0 0 255; sleep 0.12
            ;;

        "pulse_red")
            for i in $(seq 0 25 255) $(seq 255 -25 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb $i 0 0; sleep 0.02
            done
            ;;
        "pulse_blue")
            for i in $(seq 0 25 255) $(seq 255 -25 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb 0 0 $i; sleep 0.02
            done
            ;;
        "pulse_green")
            for i in $(seq 0 25 255) $(seq 255 -25 0); do
                [ "$(get_mode)" != "$CURRENT_MODE" ] && break
                set_rgb 0 $i 0; sleep 0.02
            done
            ;;

        *)
            sleep 1
            ;;
    esac
done
