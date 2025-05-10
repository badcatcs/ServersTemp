#!/bin/bash

if [ ! -x "$0" ]; then
    chmod +x "$0" 2>/dev/null || {
        echo "Error: Failed to set execute permissions. Try:"
        echo "sudo chmod +x $0"
        exit 1
    }
fi

if ! head -n 1 "$0" | grep -q "^#!/bin/bash"; then
    if command -v dos2unix &> /dev/null; then
        dos2unix "$0" 2>/dev/null
    else
        tr -d '\r' < "$0" > "$0.tmp" && mv "$0.tmp" "$0" 2>/dev/null
    fi
    
    if ! head -n 1 "$0" | grep -q "^#!"; then
        sed -i '1i#!/bin/bash' "$0" 2>/dev/null
    fi
    
    chmod +x "$0" 2>/dev/null
fi

REMOTE_SYSLOG_HOST="192.168.0.111"
HOSTNAME="server_main"
SERVICE="sensors"
INSTALL_MODE=false
PROTOCOL="udp"
AUTO_INSTALL=false

show_help() {
    echo "Usage: servers-temp.sh [Options]"
    echo
    echo "Options:"
    echo "  -h, --hostname HOSTNAME    Hostname (default: server_main)"
    echo "  -ip, --ip IP              IP-address API server (default: 192.168.0.111)"
    echo "  -t, --tcp                 Usage TCP instead of UDP (port 5142)"
    echo "  -i, --install             Install as system service"
    echo "  -a, --auto-install        Automatically install required packages"
    echo "  --help                    Show help menu"
    echo
    echo "Example:"
    echo "  servers-temp.sh -h server_first -ip 192.168.0.111"
    echo "  servers-temp.sh -h server_first -ip 192.168.0.111 -t"
    echo "  servers-temp.sh -i -a"
}

install_packages() {
    if [[ $EUID -ne 0 ]]; then
        echo "To install packages you need root privileges. Use sudo." >&2
        exit 1
    fi

    echo "Installing required packages..."

    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y lm-sensors inetutils-syslogd
    elif command -v yum &> /dev/null; then
        yum install -y lm_sensors inetutils-syslogd
    elif command -v dnf &> /dev/null; then
        dnf install -y lm_sensors inetutils-syslogd
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm lm_sensors inetutils
    else
        echo "Unable to determine package manager. Install packages manually:"
        echo "- lm-sensors"
        echo "- inetutils-syslogd (или inetutils)"
        exit 1
    fi

    echo "Setting up lm-sensors..."
    sensors-detect --auto
    modprobe coretemp
    modprobe k10temp

    echo "Packages are installed and configured"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--hostname)
            HOSTNAME="$2"
            shift 2
            ;;
        -ip|--ip)
            REMOTE_SYSLOG_HOST="$2"
            shift 2
            ;;
        -t|--tcp)
            PROTOCOL="tcp"
            shift
            ;;
        -i|--install)
            INSTALL_MODE=true
            shift
            ;;
        -a|--auto-install)
            AUTO_INSTALL=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            show_help
            exit 1
            ;;
    esac
done

if [ "$PROTOCOL" = "tcp" ]; then
    REMOTE_SYSLOG_PORT="5142"
else
    REMOTE_SYSLOG_PORT="5141"
fi

if ! command -v logger &> /dev/null || ! command -v sensors &> /dev/null; then
    if [ "$AUTO_INSTALL" = true ]; then
        install_packages
    else
        echo "The required packages are not installed. Install them manually or use the -a option."
        echo "Required packages:"
        echo "- lm-sensors"
        echo "- inetutils-syslogd (or inetutils)"
        exit 1
    fi
fi

send_log() {
    local type=$1
    local name=$2
    local value=$3
    local unit=$4
    local hostname=$5
    local service=$6
    local sensor_type=$7
    local adapter=$8
    local device=$9
    json="{\"type\":\"$type\",\"name\":\"$name\",\"value\":$value,\"unit\":\"$unit\",\"hostname\":\"$hostname\",\"service\":\"$service\",\"sensor_type\":\"$sensor_type\",\"adapter\":\"$adapter\",\"device\":\"$device\"}"
    if [ "$PROTOCOL" = "tcp" ]; then
        logger -n "$REMOTE_SYSLOG_HOST" -P "$REMOTE_SYSLOG_PORT" -T -t sensors -p local0.info "$json"
    else
        logger -n "$REMOTE_SYSLOG_HOST" -P "$REMOTE_SYSLOG_PORT" -t sensors -p local0.info "$json"
    fi
}

process_sensors_data() {
    local current_device=""
    local current_adapter=""
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue

        if [[ "$line" =~ ^[a-zA-Z0-9._-]+$ ]]; then
            current_device="$line"
            continue
        fi
        if [[ "$line" =~ ^Adapter:\ (.*) ]]; then
            current_adapter="${BASH_REMATCH[1]}"
            continue
        fi
        if [[ "$line" =~ ^[[:space:]]*([^:]+):[[:space:]]*\+([0-9.]+)°C ]]; then
            sensor_name="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            sensor_type="other"
            if [[ "$current_adapter" == *"ISA adapter"* ]]; then
                if [[ "$sensor_name" == "Package id"* ]]; then
                    sensor_type="cpu_package"
                elif [[ "$sensor_name" == "Core"* ]]; then
                    sensor_type="cpu_core"
                else
                    sensor_type="cpu_other"
                fi
            elif [[ "$current_adapter" == *"PCI adapter"* ]]; then
                if [[ "$current_device" == *"nouveau"* || "$sensor_name" == "GPU"* ]]; then
                    sensor_type="gpu"
                elif [[ "$current_device" == *"nvme"* || "$sensor_name" == "Composite"* || "$sensor_name" == "Sensor "* ]]; then
                    sensor_type="nvme"
                else
                    sensor_type="pci_other"
                fi
            elif [[ "$current_adapter" == *"ACPI interface"* ]]; then
                sensor_type="mb"
            elif [[ "$current_adapter" == *"Virtual device"* ]]; then
                sensor_type="virtual"
            fi
            json="{\"type\":\"temperature\",\"name\":\"$sensor_name\",\"value\":$value,\"unit\":\"°C\",\"hostname\":\"$HOSTNAME\",\"service\":\"$SERVICE\",\"sensor_type\":\"$sensor_type\",\"adapter\":\"$current_adapter\",\"device\":\"$current_device\"}"
            if [ "$PROTOCOL" = "tcp" ]; then
                logger -n "$REMOTE_SYSLOG_HOST" -P "$REMOTE_SYSLOG_PORT" -T -t sensors -p local0.info "$json"
            else
                logger -n "$REMOTE_SYSLOG_HOST" -P "$REMOTE_SYSLOG_PORT" -t sensors -p local0.info "$json"
            fi
        fi
    done
}

install_service() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root." >&2
        exit 1
    fi

    SCRIPT_NAME="servers-temp.sh"
    INSTALL_PATH="/usr/local/bin/$SCRIPT_NAME"

    cp "$0" "$INSTALL_PATH"
    chmod +x "$INSTALL_PATH"

    echo "The script is installed in $INSTALL_PATH"

    SERVICE_PATH="/etc/systemd/system/servers-temp.service"

    START_CMD="$INSTALL_PATH -h $HOSTNAME -ip $REMOTE_SYSLOG_HOST"
    if [ "$PROTOCOL" = "tcp" ]; then
        START_CMD="$START_CMD -t"
    fi

    cat > "$SERVICE_PATH" << EOF
[Unit]
Description=ServersTemp by ProConnectX [xxx]
After=network.target

[Service]
Type=simple
ExecStart=$START_CMD
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable servers-temp
    systemctl start servers-temp
    
    echo "The service is installed and running."
    echo "Protocol: $PROTOCOL"
    echo "Port: $REMOTE_SYSLOG_PORT"
    systemctl status servers-temp --no-pager
}

if [ "$INSTALL_MODE" = true ]; then
    install_service
    exit 0
fi

while true; do
    declare -A sent_unparsed
    current_device=""
    current_adapter=""
    sensors | while read line; do
        [[ -z "$line" ]] && continue

        if [[ "$line" =~ ^[a-zA-Z0-9._-]+$ ]]; then
            current_device="$line"
            continue
        fi
        if [[ "$line" =~ ^Adapter:\ (.*) ]]; then
            current_adapter="${BASH_REMATCH[1]}"
            continue
        fi
        if [[ "$line" =~ ^temp1: ]]; then
            value=$(echo "$line" | grep -oP '\+\d+\.\d+' | head -n1 | tr -d '+')
            if [[ ! -z "$value" ]]; then
                send_log "temperature" "temp1" "$value" "°C" "$HOSTNAME" "$SERVICE" "cpu_other" "$current_adapter" "$current_device"
            fi
            continue
        fi
        if [[ "$line" =~ ^Composite: ]]; then
            value=$(echo "$line" | grep -oP '\+\d+\.\d+' | head -n1 | tr -d '+')
            if [[ ! -z "$value" ]]; then
                send_log "temperature" "Composite" "$value" "°C" "$HOSTNAME" "$SERVICE" "nvme" "$current_adapter" "$current_device"
            fi
            continue
        fi
        if [[ "$line" =~ ^Sensor\ 1: ]]; then
            value=$(echo "$line" | grep -oP '\+\d+\.\d+' | head -n1 | tr -d '+')
            if [[ ! -z "$value" ]]; then
                send_log "temperature" "Sensor 1" "$value" "°C" "$HOSTNAME" "$SERVICE" "nvme" "$current_adapter" "$current_device"
            fi
            continue
        fi
        if [[ "$line" =~ ^Sensor\ 2: ]]; then
            value=$(echo "$line" | grep -oP '\+\d+\.\d+' | head -n1 | tr -d '+')
            if [[ ! -z "$value" ]]; then
                send_log "temperature" "Sensor 2" "$value" "°C" "$HOSTNAME" "$SERVICE" "nvme" "$current_adapter" "$current_device"
            fi
            continue
        fi
        if [[ "$line" =~ ^Package\ id\ 0: ]]; then
            value=$(echo "$line" | grep -oP '\+\d+\.\d+' | head -n1 | tr -d '+')
            if [[ ! -z "$value" ]]; then
                send_log "temperature" "Package id 0" "$value" "°C" "$HOSTNAME" "$SERVICE" "cpu_package" "$current_adapter" "$current_device"
            fi
            continue
        fi
        if [[ "$line" =~ ^Core\ [0-9]+: ]]; then
            core_name=$(echo "$line" | awk -F: '{print $1}')
            value=$(echo "$line" | grep -oP '\+\d+\.\d+' | head -n1 | tr -d '+')
            if [[ ! -z "$value" ]]; then
                send_log "temperature" "$core_name" "$value" "°C" "$HOSTNAME" "$SERVICE" "cpu_core" "$current_adapter" "$current_device"
            fi
            continue
        fi
        if [[ "$line" =~ ^[[:space:]]*([^:]+):[[:space:]]*\+([0-9.]+)°C ]]; then
            sensor_name="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            key="${sensor_name}_${value}"
            if [[ -z "${sent_unparsed[$key]}" ]]; then
                sent_unparsed[$key]=1
                send_log "temperature" "$sensor_name" "$value" "°C" "$HOSTNAME" "$SERVICE" "unparsed" "$current_adapter" "$current_device"
            fi
        fi
    done
    sleep 30
done