#!/bin/bash
# MCU LED Daemon for ArkOS4clones (M9 Pro / RK3326)

SETTINGS_FILE="/home/ark/.emulationstation/es_settings.xml"
LAST_MODE=""
HUE=0

get_mode() {
    if [ -f "$SETTINGS_FILE" ]; then
        MODE=$(grep -oP '(?<=<string name="JoystickLEDMode" value=")[^"]*' "$SETTINGS_FILE" 2>/dev/null)
        echo "${MODE:-off}"
    else
        echo "off"
    fi
}

# Helper to set RGB
set_rgb() {
    /usr/bin/mcu_led "$1" "$2" "$3" 2>/dev/null
}

while true; do
    CURRENT_MODE=$(get_mode)

    case "$CURRENT_MODE" in
        "off")
            set_rgb 0 0 0
            sleep 3
            ;;

        # --- STOCK COLOR MODES ---
        "static_red"|"static red")       set_rgb 255 0 0; sleep 3 ;;
        "static_green"|"static green")   set_rgb 0 255 0; sleep 3 ;;
        "static_blue"|"static blue")     set_rgb 0 0 255; sleep 3 ;;
        "static_yellow"|"static yellow") set_rgb 255 200 0; sleep 3 ;;
        "static_cyan"|"static cyan")     set_rgb 0 255 255; sleep 3 ;;
        "static_purple"|"static purple") set_rgb 180 0 255; sleep 3 ;;
        "static_white"|"static white")   set_rgb 255 255 255; sleep 3 ;;
        "static"|"static_cyan_default")  set_rgb 0 180 255; sleep 3 ;;

        # --- STOCK BREATHING MODES ---
        "breathing_red")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do set_rgb $i 0 0; sleep 0.04; done
            ;;
        "breathing_green")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do set_rgb 0 $i 0; sleep 0.04; done
            ;;
        "breathing_blue"|"breathing")
            for i in $(seq 0 15 255) $(seq 255 -15 0); do set_rgb 0 0 $i; sleep 0.04; done
            ;;

        # --- STOCK FLOW MODE ---
        "flow"|"rainbow")
            HUE=$(( (HUE + 20) % 360 ))
            # Fast RGB smooth cycle for stock 'flow'
            R=$(( (HUE * 255) / 360 ))
            G=$(( 255 - R ))
            set_rgb $R $G 180
            sleep 0.15
            ;;

        # --- NEW CUSTOM MODES ---
        "rainbow_wave"|"rainbow_full")
            HUE=$(( (HUE + 15) % 360 ))
            set_rgb $(( (HUE * 255) / 360 )) 120 220
            sleep 0.1
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
            sleep 5
            ;;

        "fire")
            set_rgb $((150 + RANDOM % 106)) $((RANDOM % 60)) 0
            sleep 0.12
            ;;

        "strobe_party"|"disco")
            set_rgb $((RANDOM % 256)) $((RANDOM % 256)) $((RANDOM % 256))
            sleep 0.1
            ;;

        "police")
            set_rgb 255 0 0; sleep 0.15
            set_rgb 0 0 255; sleep 0.15
            ;;

        "pulse_red")
            for i in $(seq 0 20 255) $(seq 255 -20 0); do set_rgb $i 0 0; sleep 0.03; done
            ;;
        "pulse_blue")
            for i in $(seq 0 20 255) $(seq 255 -20 0); do set_rgb 0 0 $i; sleep 0.03; done
            ;;
        "pulse_green")
            for i in $(seq 0 20 255) $(seq 255 -20 0); do set_rgb 0 $i 0; sleep 0.03; done
            ;;

        *)
            sleep 2
            ;;
    esac
done
