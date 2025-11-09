#!/usr/bin/env bash
set -euo pipefail
sleep 120
# ----------------------------------------
# Graphical environment configuration
export DISPLAY=:0
export XAUTHORITY="${HOME}/.Xauthority"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
# ----------------------------------------

# User home directory
HOME_DIR="${HOME}"
PROJECT_DIR="${HOME_DIR}/Desktop/ksiengowy"
WIFI_FILE="${PROJECT_DIR}/wifi_cred.txt"
MIRROR_URL_FILE="${PROJECT_DIR}/mirror_url.txt"
VENV_DIR="${PROJECT_DIR}/ksiengowy_env"

UVICORN_CMD="cd ${PROJECT_DIR} && source ${VENV_DIR}/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
NGROK_CMD="ngrok http 8000"

# Function to detect available terminal
detect_terminal() {
    if command -v gnome-terminal >/dev/null 2>&1; then
        echo "gnome-terminal"
    elif command -v konsole >/dev/null 2>&1; then
        echo "konsole"
    elif command -v xterm >/dev/null 2>&1; then
        echo "xterm"
    elif command -v terminology >/dev/null 2>&1; then
        echo "terminology"
    elif command -v mate-terminal >/dev/null 2>&1; then
        echo "mate-terminal"
    elif command -v xfce4-terminal >/dev/null 2>&1; then
        echo "xfce4-terminal"
    elif command -v lxterminal >/dev/null 2>&1; then
        echo "lxterminal"
    else
        echo "none"
    fi
}

# Function to get ngrok URL via API
get_ngrok_url() {
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for ngrok URL..."
    
    while [ $attempt -le $max_attempts ]; do
        # Attempt to get URL via ngrok API
        local ngrok_url=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | grep -o 'https://[^"]*\.ngrok-free\.dev' | head -1)
        
        if [ -n "$ngrok_url" ]; then
            echo "$ngrok_url"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: ngrok URL not yet available..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "Failed to get ngrok URL within $max_attempts attempts"
    return 1
}

# Function to get URL from mirror_url.txt file
get_mirror_url() {
    if [[ ! -f "${MIRROR_URL_FILE}" ]]; then
        echo "Error: file ${MIRROR_URL_FILE} not found." >&2
        return 1
    fi
    
    local mirror_url=$(head -n 1 "${MIRROR_URL_FILE}" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    if [[ -z "$mirror_url" ]]; then
        echo "Error: file ${MIRROR_URL_FILE} is empty or contains invalid URL." >&2
        return 1
    fi
    
    # Check if URL starts with http:// or https://
    if [[ ! "$mirror_url" =~ ^https?:// ]]; then
        echo "Error: URL in file ${MIRROR_URL_FILE} must start with http:// or https://" >&2
        return 1
    fi
    
    echo "$mirror_url"
    return 0
}

# Function to send URL via curl
send_ngrok_url() {
    local ngrok_url="$1"
    local mirror_url="$2"
    
    if [ -z "$ngrok_url" ]; then
        echo "Error: Empty ngrok URL to send"
        return 1
    fi
    
    if [ -z "$mirror_url" ]; then
        echo "Error: Empty mirror URL to send"
        return 1
    fi
    
    echo "Sending ngrok URL: $ngrok_url"
    echo "To address: $mirror_url"
    
    # Send POST request with URL
    local response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "{\"ngrok_url\": \"$ngrok_url\", \"timestamp\": \"$(date -Iseconds)\", \"project\": \"ksiengowy\"}" \
        "$mirror_url")
    
    local http_code=$(echo "$response" | tail -n1)
    local response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo "URL successfully sent! HTTP status: $http_code"
        if [ -n "$response_body" ]; then
            echo "Server response: $response_body"
        fi
        return 0
    else
        echo "Error sending URL. HTTP status: $http_code"
        if [ -n "$response_body" ]; then
            echo "Server response: $response_body"
        fi
        return 1
    fi
}

# Function to run command in terminal
run_in_terminal() {
    local title="$1"
    local command="$2"
    local workdir="${3:-}"
    
    local terminal=$(detect_terminal)
    
    case "$terminal" in
        "gnome-terminal")
            if [[ -n "$workdir" ]]; then
                gnome-terminal --title="$title" --working-directory="$workdir" -- bash -c "$command; echo 'Command completed. Press Enter...'; read"
            else
                gnome-terminal --title="$title" -- bash -c "$command; echo 'Command completed. Press Enter...'; read"
            fi
            ;;
        "konsole")
            if [[ -n "$workdir" ]]; then
                konsole --new-tab --title "$title" -e bash -c "cd '$workdir' && $command; echo 'Command completed. Press Enter...'; read"
            else
                konsole --new-tab --title "$title" -e bash -c "$command; echo 'Command completed. Press Enter...'; read"
            fi
            ;;
        "xterm")
            if [[ -n "$workdir" ]]; then
                xterm -title "$title" -hold -e bash -c "cd '$workdir' && $command" &
            else
                xterm -title "$title" -hold -e bash -c "$command" &
            fi
            ;;
        "terminology")
            if [[ -n "$workdir" ]]; then
                terminology --title="$title" -e bash -c "cd '$workdir' && $command; echo 'Command completed. Press Enter...'; read"
            else
                terminology --title="$title" -e bash -c "$command; echo 'Command completed. Press Enter...'; read"
            fi
            ;;
        "mate-terminal")
            if [[ -n "$workdir" ]]; then
                mate-terminal --title="$title" --working-directory="$workdir" --command="bash -c '$command; echo \"Command completed. Press Enter...\"; read'"
            else
                mate-terminal --title="$title" --command="bash -c '$command; echo \"Command completed. Press Enter...\"; read'"
            fi
            ;;
        "xfce4-terminal")
            if [[ -n "$workdir" ]]; then
                xfce4-terminal --title="$title" --working-directory="$workdir" --command="bash -c '$command; echo \"Command completed. Press Enter...\"; read'"
            else
                xfce4-terminal --title="$title" --command="bash -c '$command; echo \"Command completed. Press Enter...\"; read'"
            fi
            ;;
        "lxterminal")
            if [[ -n "$workdir" ]]; then
                lxterminal --title="$title" --working-directory="$workdir" --command="bash -c '$command; echo \"Command completed. Press Enter...\"; read'"
            else
                lxterminal --title="$title" --command="bash -c '$command; echo \"Command completed. Press Enter...\"; read'"
            fi
            ;;
        "none")
            echo "ERROR: Could not find supported terminal!" >&2
            return 1
            ;;
    esac
    
    echo "Launched in terminal: $terminal - $title"
    return 0
}

# Check for required files and directories
if [[ ! -f "${WIFI_FILE}" ]]; then
  echo "Error: file ${WIFI_FILE} not found." >&2
  exit 1
fi
if [[ ! -d "${PROJECT_DIR}" ]]; then
  echo "Error: project folder ${PROJECT_DIR} not found." >&2
  exit 1
fi
if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Error: virtual environment ${VENV_DIR} not found." >&2
  exit 1
fi

# Check for mirror_url.txt file
if [[ ! -f "${MIRROR_URL_FILE}" ]]; then
    echo "WARNING: file ${MIRROR_URL_FILE} not found."
    echo "Creating template file..."
    cat > "${MIRROR_URL_FILE}" << EOF

EOF
    echo "Created file ${MIRROR_URL_FILE}. Please edit it and add your URL."
fi

# Read SSID and password
mapfile -t _lines < "${WIFI_FILE}"
SSID="${_lines[0]//[$'\t\r\n ']}"
PASSWORD="${_lines[1]//[$'\t\r\n ']}"

if [[ -z "${SSID}" ]] || [[ -z "${PASSWORD}" ]]; then
  echo "Error: SSID or password is empty in ${WIFI_FILE}." >&2
  exit 1
fi

echo "Attempting to connect to Wi-Fi: ${SSID} ..."

# Connect via nmcli
connect_via_nmcli() {
  if command -v nmcli >/dev/null 2>&1; then
    nmcli connection delete "${SSID}" 2>/dev/null || true
    nmcli device wifi connect "${SSID}" password "${PASSWORD}"
    return $?
  fi
  return 1
}

# Fallback via wpa_supplicant
connect_via_wpa() {
  if command -v wpa_cli >/dev/null 2>&1 && command -v wpa_supplicant >/dev/null 2>&1; then
    TMP_CONF="$(mktemp)"
    cat > "${TMP_CONF}" <<EOF
network={
    ssid="${SSID}"
    psk="${PASSWORD}"
    key_mgmt=WPA-PSK
}
EOF
    IFACE="$(ip -br link | awk '/w/ {print $1; exit}')"
    if [[ -z "${IFACE}" ]]; then
      echo "No Wi-Fi interface found." >&2
      rm -f "${TMP_CONF}"
      return 1
    fi
    sudo wpa_supplicant -B -i "${IFACE}" -c "${TMP_CONF}"
    sudo dhclient "${IFACE}" || true
    rm -f "${TMP_CONF}"
    return 0
  fi
  return 1
}

# Attempt to connect multiple times
MAX_RETRIES=6
SLEEP_BETWEEN=5
CONNECTED=1
for i in $(seq 1 "${MAX_RETRIES}"); do
  echo "Attempt ${i}/${MAX_RETRIES}..."
  if connect_via_nmcli; then CONNECTED=0; break; fi
  if connect_via_wpa; then CONNECTED=0; break; fi
  sleep "${SLEEP_BETWEEN}"
done

if [[ "${CONNECTED}" -ne 0 ]]; then
  echo "Failed to connect to Wi-Fi ${SSID}." >&2
  exit 2
fi

echo "Wi-Fi connected. Waiting for IP..."
TIMEOUT=60
EL=0
while [[ $EL -lt $TIMEOUT ]]; do
  if ip -4 addr show scope global | grep -q 'inet '; then break; fi
  sleep 1
  EL=$((EL+1))
done

echo "Successfully connected to Wi-Fi and obtained IP address!"
sleep 3

# Update project and install dependencies
echo "Updating project from Git repository..."
cd "${PROJECT_DIR}"
if git pull; then
    echo "Git pull completed successfully"
    
    echo "Installing/updating Python dependencies..."
    source "${VENV_DIR}/bin/activate"
    if pip3 install -r requirements.txt; then
        echo "Dependencies installed successfully"
    else
        echo "Warning: Failed to install dependencies from requirements.txt"
    fi
    deactivate
else
    echo "Warning: Git pull failed, continuing with existing code"
fi

# Detect available terminal
TERMINAL_TYPE=$(detect_terminal)
echo "Using terminal: $TERMINAL_TYPE"

if [[ "$TERMINAL_TYPE" == "none" ]]; then
    echo "ERROR: No supported terminal found!"
    exit 1
fi

# FastAPI command with git pull and pip install
FASTAPI_COMMAND="echo 'Activating virtual environment...'; source '${VENV_DIR}/bin/activate'; echo 'Changing to project directory...'; cd '${PROJECT_DIR}'; echo 'Updating project from Git...'; git pull; echo 'Installing dependencies...'; pip3 install -r requirements.txt; echo 'Starting FastAPI server...'; cd app; uvicorn main:app --reload --host 0.0.0.0 --port 8000; echo 'Server stopped. Press Enter to close...'; read"

# ngrok command with monitoring
NGROK_COMMAND="echo 'Starting ngrok for port 8000 tunneling...'; ${NGROK_CMD}; echo 'Ngrok stopped. Press Enter to close...'; read"

# Launch FastAPI in terminal
echo "Starting FastAPI project..."
if ! run_in_terminal "FastAPI Server" "$FASTAPI_COMMAND" "$PROJECT_DIR"; then
    echo "Failed to launch FastAPI in terminal"
    exit 1
fi

# Delay before starting ngrok
echo "Waiting for FastAPI server to start..."
sleep 10

# Launch ngrok in terminal
echo "Starting ngrok..."
if ! run_in_terminal "Ngrok Tunnel" "$NGROK_COMMAND" ""; then
    echo "Failed to launch ngrok in terminal"
    exit 1
fi

# Wait and get ngrok URL
echo "Waiting for ngrok initialization..."
sleep 10

NGROK_URL=$(get_ngrok_url)

if [ -n "$NGROK_URL" ]; then
    echo "Obtained ngrok URL: $NGROK_URL"
    
    # Get mirror URL from file
    MIRROR_URL=$(get_mirror_url)
    
    if [ -n "$MIRROR_URL" ]; then
        # Send URL via curl
        if send_ngrok_url "$NGROK_URL" "$MIRROR_URL"; then
            echo "Ngrok URL successfully sent to $MIRROR_URL"
        else
            echo "Error sending ngrok URL"
        fi
    else
        echo "Failed to get mirror URL, skipping send"
    fi
else
    echo "Failed to get ngrok URL, skipping send"
fi

echo "=================================================="
echo "SUCCESSFULLY LAUNCHED!"
echo "FastAPI server: http://localhost:8000"
if [ -n "$NGROK_URL" ]; then
    echo "Ngrok URL: $NGROK_URL"
fi
if [ -n "$MIRROR_URL" ]; then
    echo "Mirror URL: $MIRROR_URL"
fi
echo "API documentation: http://localhost:8000/docs"
echo "=================================================="