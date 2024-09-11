#!/bin/bash

# Define the relative path for the config directory and the miner.json file
CONFIG_DIR="./config"
CONFIG_FILE="$CONFIG_DIR/miner.json"

# Ensure the config directory exists
mkdir -p "$CONFIG_DIR"

# Predefined list of blockchain networks and categories
available_networks=("ethereum" "polygon")
available_categories=("external" "erc20" "erc721" "erc1155" "specialnft")

# Initialize arrays to store selected networks and categories
selected_networks=()

# Prompt the user for input
echo "Welcome to the Miner Setup!"
echo "You will configure the miner to fetch data from multiple blockchain networks."

# Function to select a network from the list
select_network() {
    while [[ ${#available_networks[@]} -gt 0 ]]; do
        echo "Available blockchain networks:"
        for i in "${!available_networks[@]}"; do
            echo "$((i+1))) ${available_networks[$i]}"
        done

        read -p "Select a network by number: " network_idx
        if [[ $network_idx =~ ^[0-9]+$ ]] && ((network_idx >= 1 && network_idx <= ${#available_networks[@]})); then
            selected_network="${available_networks[$network_idx-1]}"
            selected_networks+=("$selected_network")
            echo "Selected network: $selected_network"

            # Remove the selected network from the available networks
            unset 'available_networks[network_idx-1]'
            available_networks=("${available_networks[@]}")  # Reindex the array
            break
        else
            echo "Invalid selection. Please select a valid network number."
        fi
    done
}

# Function to select categories for a network from the list
select_categories() {
    categories=()
    while [[ ${#available_categories[@]} -gt 0 ]]; do
        echo "You must select at least one category for the network."
        echo "Available categories:"
        for i in "${!available_categories[@]}"; do
            echo "$((i+1))) ${available_categories[$i]}"
        done

        read -p "Select a category by number (or press enter to finish): " category_idx
        if [[ -z "$category_idx" && ${#categories[@]} -ge 1 ]]; then
            break
        elif [[ $category_idx =~ ^[0-9]+$ ]] && ((category_idx >= 1 && category_idx <= ${#available_categories[@]})); then
            selected_category="${available_categories[$category_idx-1]}"
            categories+=("$selected_category")
            echo "Added category: $selected_category"

            # Remove the selected category from the available categories
            unset 'available_categories[category_idx-1]'
            available_categories=("${available_categories[@]}")  # Reindex the array
        else
            echo "Invalid selection. Please select a valid category number."
        fi
    done
}

# Initialize the JSON string
json_output='{"networks": ['

# Loop to add networks
while [[ ${#available_networks[@]} -gt 0 ]]; do
    select_network
    if [[ ${#available_categories[@]} -gt 0 ]]; then
        select_categories  # Correctly separate category prompt from selection
    fi

    # Add the network and categories to the JSON output
    json_output+='{"name": "'"$selected_network"'", "category": ['

    # Add each category to the network entry
    for category in "${categories[@]}"; do
        json_output+='"'"$category"'",'
    done
    # Remove the trailing comma and close the categories array
    json_output=${json_output%,}
    json_output+=']},'

    # Ask if the user wants to add another network
    if [[ ${#available_networks[@]} -gt 0 ]]; then
        read -p "Do you want to add another network? (y/n): " add_another
        if [[ "$add_another" != "y" ]]; then
            break
        fi
    else
        echo "No more available networks to select."
        break
    fi
done

# Remove the trailing comma and close the JSON string
json_output=${json_output%,}
json_output+=']}'

# Save to config/miner.json
echo "$json_output" > "$CONFIG_FILE"

echo "Miner configuration saved to $CONFIG_FILE"
cat "$CONFIG_FILE"
