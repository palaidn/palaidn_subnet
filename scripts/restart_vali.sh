#!/bin/bash

# Source the user's profile to ensure all necessary environment variables are set
source ~/.profile

# Check if jq is installed; if not, install it
if ! command -v jq &> /dev/null; then
    echo "jq is not installed. Installing jq..."
    sudo apt-get update && sudo apt-get install -y jq
    if [ $? -ne 0 ]; then
        echo "Failed to install jq. Exiting."
        exit 1
    fi
else
    echo "jq is already installed."
fi

# Use the full path to PM2
PM2_PATH=$(which pm2)

# Function to restart validator processes
echo "Checking for validator processes..."

# Get all PM2 processes and filter for those with "validator" in the script path
pm2 jlist | jq -c '.[]' | while read -r process; do
    INSTANCE_NAME=$(echo "$process" | jq -r '.name')
    SCRIPT_PATH=$(echo "$process" | jq -r '.pm2_env.pm_exec_path')

    if [[ "$SCRIPT_PATH" == *"validator"* ]]; then
        PROCESS_ID=$(echo "$process" | jq -r '.pm2_env.pm_id')
        echo "Found validator process: $INSTANCE_NAME (ID: $PROCESS_ID), Script Path: $SCRIPT_PATH"
        
        # Restart the process
        echo "Restarting process ID: $PROCESS_ID (Name: $INSTANCE_NAME)"
        $PM2_PATH restart "$PROCESS_ID"
    fi
done

# Save the PM2 process list to make sure everything is properly updated
$PM2_PATH save --force

echo "Validator processes restarted successfully."

# Script ends here, allowing PM2 to restart it after 30 seconds
exit 0