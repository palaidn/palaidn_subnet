#!/bin/bash

# Check and set working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$( dirname "$SCRIPT_DIR" )"

if [ "$PWD" != "$REPO_ROOT" ]; then
    echo "Changing working directory to $REPO_ROOT"
    cd "$REPO_ROOT" || { echo "Failed to change directory. Exiting."; exit 1; }
fi

ENABLE_AUTO_UPDATE="false"

# Function to prompt for user input
prompt_for_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local current_value="${!var_name}"

    if [ -z "$current_value" ]; then
        # If the variable is unset or empty, use the default value
        read -p "$prompt [$default]: " user_input
        eval $var_name="${user_input:-$default}"
    else
        # If the variable is set, show the current value and allow user to change it
        read -p "$prompt [set to: $current_value]: " user_input
        eval $var_name="${user_input:-$current_value}"
    fi
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
# Prompt the user for the Alchemy Project ID
prompt_for_input "Enter your Alchemy API key: " "" "ALCHEMY_API_KEY"

echo "You need a PayPangea API key to fetch wallet data. Please enter it below:"
# Prompt the user for the PayPangea API key
prompt_for_input "Please enter your PayPangea API key: " "" "PAYPANGEA_API_KEY"

# Create the .env file and write the Alchemy APi key and PayPangea API key into it
echo "ALCHEMY_API_KEY=$ALCHEMY_API_KEY" > .env
echo "PAYPANGEA_API_KEY=$PAYPANGEA_API_KEY" >> .env

# Notify the user of completion
echo ".env file created successfully with your Alchemy API key and PayPangea API key."

# Prompt for network if not specified
prompt_for_input "Enter network (local/finney)" "finney" "NETWORK"
case $NETWORK in
    finney)
        DEFAULT_NEURON_ARGS=" --netuid 45"
        ;;
    local)
        DEFAULT_NEURON_ARGS=" --netuid 1 --subtensor.chain_endpoint ws://127.0.0.1:9946"
        ;;
    *)
        DEFAULT_NEURON_ARGS=" --subtensor.network $NETWORK"
        ;;
esac


# Check if lite node is running and add chain_endpoint if it is
if is_lite_node_running; then
    DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --subtensor.chain_endpoint ws://127.0.0.1:9946"
fi

# Prompt for wallet name and hotkey if not specified
prompt_for_input "Enter wallet name" "default" "WALLET_NAME"
prompt_for_input "Enter wallet hotkey" "default" "WALLET_HOTKEY"
DEFAULT_NEURON_ARGS="$DEFAULT_NEURON_ARGS --wallet.name $WALLET_NAME --wallet.hotkey $WALLET_HOTKEY"


# Prompt for logging level if not specified
prompt_for_input "Enter logging level (info/debug/trace)" "debug" "LOGGING_LEVEL"
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
    prompt_yes_no "Do you want to enable auto-update? We strogly recommend you do. Warning: this will apply to all running neurons" "ENABLE_AUTO_UPDATE"
fi

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

prompt_for_input "Enter instance name" "subnet45miner" "INSTANCE_NAME"

PROCESS_STATUS=$(pm2 list | grep "$INSTANCE_NAME")

if [ -z "$PROCESS_STATUS" ]; then
    # If the process is not running, start it
    echo "Starting $INSTANCE_NAME with arguments: $DEFAULT_NEURON_ARGS"
    pm2 start neurons/miner.py --interpreter=python3 --name "$INSTANCE_NAME" -- $DEFAULT_NEURON_ARGS
    echo "Miner started successfully with instance name: $INSTANCE_NAME"
else
    # If the process is found, check its status
    PROCESS_RUNNING=$(pm2 list | grep "$INSTANCE_NAME" | grep "online")

    if [ -n "$PROCESS_RUNNING" ]; then
        # If the process is running, restart it
        echo "Restarting $INSTANCE_NAME with arguments: $DEFAULT_NEURON_ARGS"
        pm2 restart "$INSTANCE_NAME"
        echo "Miner restarted successfully with instance name: $INSTANCE_NAME"
    else
        # If the process is not running (but found), start it
        echo "Starting $INSTANCE_NAME with arguments: $DEFAULT_NEURON_ARGS"
        pm2 start neurons/miner.py --interpreter=python3 --name "$INSTANCE_NAME" -- $DEFAULT_NEURON_ARGS
        echo "Miner started successfully with instance name: $INSTANCE_NAME"
    fi
fi

# Save the PM2 process list
pm2 save --force