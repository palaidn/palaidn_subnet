#!/bin/bash

echo "Starting auto_update.sh"

# Check and set the working directory to the root of the repository
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$( dirname "$SCRIPT_DIR" )"

if [ "$PWD" != "$REPO_ROOT" ]; then
    echo "Changing working directory to $REPO_ROOT"
    cd "$REPO_ROOT" || { echo "Failed to change directory to $REPO_ROOT. Exiting."; exit 1; }
fi

# Get the current Git branch
current_branch=$(git rev-parse --abbrev-ref HEAD)
echo "Auto-update enabled on branch: $current_branch"

# Make sure the restart and cleanup scripts are executable
chmod +x scripts/restart_pm2_processes.sh
chmod +x scripts/cleanup_script.sh

# Function to handle update and restart
update_and_restart() {

    echo "New updates detected. Stashing local changes..."
    
    git add .
    git stash
    echo "Pulling changes..."
    if git pull origin $current_branch; then
        echo "Running cleanup script..."
        echo "$(pwd)"
        # Run the cleanup script
        if bash "$(pwd)/scripts/cleanup_script.sh"; then
            echo "Cleanup completed successfully."
            echo "Reinstalling dependencies..."

            # Install the package in editable mode
            if python3 -m pip install -e .; then

                # Schedule PM2 restart
                echo "Scheduling PM2 restart..."
                nohup bash -c "sleep 10 && $(pwd)/scripts/restart_pm2_processes.sh" > /tmp/pm2_restart.log 2>&1 &
                echo "PM2 restart scheduled. The script will exit now and restart shortly."
                exit 0
            else
                echo "Failed to install dependencies. Skipping restart."
                git stash pop
                return 1
            fi
        fi
    else
        echo "Failed to pull changes. Skipping update and restart."
        git stash pop
        return 1
    fi
}

# Main loop to check for updates
while true; do
    echo "Fetching updates..."
    git fetch
    local_hash=$(git rev-parse HEAD)
    remote_hash=$(git rev-parse origin/$current_branch)

    echo "Local hash: $local_hash"
    echo "Remote hash: $remote_hash"

    if [[ $local_hash != $remote_hash ]]; then
        if update_and_restart; then
            echo "Update successful."
            sleep 120
        else
            echo "Update failed. Retrying in 5 minutes."
            sleep 300
        fi
    else
        echo "No updates found. Checking again in 2 minutes..."
        sleep 120
    fi
done
