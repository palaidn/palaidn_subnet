#!/bin/bash

# Check and set working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$( dirname "$SCRIPT_DIR" )"

if [ "$PWD" != "$REPO_ROOT" ]; then
    echo "Changing working directory to $REPO_ROOT"
    cd "$REPO_ROOT" || { echo "Failed to change directory. Exiting."; exit 1; }
fi

START_VAR_FILE="$REPO_ROOT/.start_var_miner"

# Load variables from start_var if the file exists
if [ -f "$START_VAR_FILE" ]; then
    echo "Loading variables from $START_VAR_FILE..."
    source "$START_VAR_FILE"
fi

ENABLE_AUTO_UPDATE="${ENABLE_AUTO_UPDATE:-false}"


echo "NEURON_TYPE=MINER" >> "$START_VAR_FILE"

# Function to prompt for user input
prompt_for_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local current_value="${!var_name}"

    if [ -z "$current_value" ]; then
        read -p "$prompt [$default]: " user_input
        eval $var_name="${user_input:-$default}"
    else
        read -p "$prompt [set to: $current_value]: " user_input
        eval $var_name="${user_input:-$current_value}"
    fi

    # Save the variable to start_var file
    echo "$var_name=\"${!var_name}\"" >> "$START_VAR_FILE"
}

# Function to prompt for yes/no input
prompt_yes_no() {
    local prompt="$1"
    local var_name="$2"
    while true; do
        read -p "$prompt [y/n]: " yn
        case $yn in
            [Yy]* ) eval $var_name="true"; break;;
            [Nn]* ) eval $var_name="false"; break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
    # Save the variable to start_var file
    echo "$var_name=\"${!var_name}\"" >> "$START_VAR_FILE"
}

# Function to check if lite node is running
is_lite_node_running() {
    pgrep -f "substrate.*--chain bittensor" > /dev/null
}

# Function to check if auto-updater is already running
is_auto_updater_running() {
    pm2 list | grep -q "auto-updater"
}

echo "You need an Alchemy account to run this miner. Please create one and add the ID below:"
prompt_for_input "Enter your Alchemy API key: " "${ALCHEMY_API_KEY:-}" "ALCHEMY_API_KEY"

echo "You need a PayPangea API key to fetch wallet data. Please enter it below:"
prompt_for_input "Please enter your PayPangea API key: " "${PAYPANGEA_API_KEY:-}" "PAYPANGEA_API_KEY"

# Create the .env file and write the Alchemy API key and PayPangea API key into it
echo "ALCHEMY_API_KEY=$ALCHEMY_API_KEY" > .env
echo "PAYPANGEA_API_KEY=$PAYPANGEA_API_KEY" >> .env

# Notify the user of completion
echo ".env file created successfully with your Alchemy API key and PayPangea API key."

# Prompt for network if not specified
prompt_for_input "Enter network (local/finney)" "${NETWORK:-finney}" "NETWORK"
case $NETWORK in
    finney)
        DEFAULT_NEURON_ARGS=" --netuid 14"
        ;;
    local)
        prompt_for_input "Enter network UID" "${NETWORK_UID:-14}" "NETWORK_UID"
        prompt_for_input "Enter chain endpoint" "${CHAIN_ENDPOINT:-ws://127.0.0.1:9944}" "CHAIN_ENDPOINT"
        DEFAULT_NEURON_ARGS=" --netuid $NETWORK_UID --subtensor.chain_endpoint $CHAIN_ENDPOINT"
        ;;
    *)
        DEFAULT_NEURON_ARGS=" --subtensor.network $NETWORK"
        ;;
esac

# Check if lite node is running and add chain_endpoint if it is
if is_lite_node_running; then
    prompt_for_input "Enter chain endpoint" "${CHAIN_ENDPOINT:-ws://127.0.0.1:9944}" "CHAIN_ENDPOINT"
    DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --subtensor.chain_endpoint $CHAIN_ENDPOINT"
fi

# Prompt for wallet name and hotkey if not specified
prompt_for_input "Enter wallet name" "${WALLET_NAME:-default}" "WALLET_NAME"
prompt_for_input "Enter wallet hotkey" "${WALLET_HOTKEY:-default}" "WALLET_HOTKEY"
DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --wallet.name $WALLET_NAME --wallet.hotkey $WALLET_HOTKEY"

# Prompt for logging level if not specified
prompt_for_input "Enter logging level (info/debug/trace)" "${LOGGING_LEVEL:-debug}" "LOGGING_LEVEL"
case $LOGGING_LEVEL in
    info|debug|trace)
        DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --logging.$LOGGING_LEVEL"
        ;;
    *)
        echo "Invalid logging level. Using default (debug)."
        DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --logging.debug"
        ;;
esac

# Prompt for disabling auto-update if not specified
if [ "$ENABLE_AUTO_UPDATE" = "false" ]; then
    prompt_yes_no "Do you want to enable auto-update? We strongly recommend you do. Warning: this will apply to all running neurons" "ENABLE_AUTO_UPDATE"
fi

# Save the auto-update status to start_var
echo "ENABLE_AUTO_UPDATE=\"$ENABLE_AUTO_UPDATE\"" >> "$START_VAR_FILE"

pm2 save

# Handle auto-updater
if [ "$ENABLE_AUTO_UPDATE" = "true" ]; then
    if ! is_auto_updater_running; then
        pm2 start scripts/auto_update.sh --name "auto-updater"
        echo "Auto-updater started."
    else
        pm2 restart scripts/auto_update.sh --name "auto-updater"
        echo "Auto-updater is already running."
    fi
else
    if is_auto_updater_running; then
        pm2 stop auto-updater
        pm2 delete auto-updater
        echo "Auto-updater has been stopped and removed."
    else
        echo "Auto-updater is not running."
    fi
fi

prompt_for_input "Enter instance name" "${INSTANCE_NAME:-subnet14miner}" "INSTANCE_NAME"
prompt_for_input "Enter axon port" "${AXON:-8091}" "AXON"

DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --axon.port $AXON"

# Save the final command used to start/restart the process
echo "DEFAULT_NEURON_ARGS=\"$DEFAULT_NEURON_ARGS\"" >> "$START_VAR_FILE"

PROCESS_STATUS=$(pm2 list | grep "$INSTANCE_NAME")

if [ -z "$PROCESS_STATUS" ]; then
    echo "Starting $INSTANCE_NAME with arguments: $DEFAULT_NEURON_ARGS"
    pm2 start neurons/miner.py --interpreter=python3 --name "$INSTANCE_NAME" -- $DEFAULT_NEURON_ARGS
    echo "Miner started successfully with instance name: $INSTANCE_NAME"
else
    PROCESS_RUNNING=$(pm2 list | grep "$INSTANCE_NAME" | grep "online")

    if [ -n "$PROCESS_RUNNING" ]; then
        echo "Restarting $INSTANCE_NAME with arguments: $DEFAULT_NEURON_ARGS"
        pm2 delete "$INSTANCE_NAME"
        sleep 1
        pm2 start neurons/miner.py --interpreter=python3 --name "$INSTANCE_NAME" -- $DEFAULT_NEURON_ARGS
        echo "Miner restarted successfully with instance name: $INSTANCE_NAME"
    else
        echo "Starting $INSTANCE_NAME with arguments: $DEFAULT_NEURON_ARGS"
        pm2 start neurons/miner.py --interpreter=python3 --name "$INSTANCE_NAME" -- $DEFAULT_NEURON_ARGS
        echo "Miner started successfully with instance name: $INSTANCE_NAME"
    fi
fi

# Save the PM2 process list
pm2 save --force

# Output confirmation of saved variables
echo "All variables have been saved to $START_VAR_FILE"
