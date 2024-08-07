#!/bin/bash

echo "You need an Alchemy account to run this miner. Please create one and add the ID below:"
# Prompt the user for the Alchemy Project ID
read -p "Please enter your Alchemy API key: " ALCHEMY_API_KEY

echo "You need a PayPangea API key to fetch wallet data. Please enter it below:"
# Prompt the user for the PayPangea API key
read -p "Please enter your PayPangea API key: " PAYPANGEA_API_KEY

# Create the .env file and write the Alchemy APi key and PayPangea API key into it
echo "ALCHEMY_API_KEY=$ALCHEMY_API_KEY" > .env
echo "PAYPANGEA_API_KEY=$PAYPANGEA_API_KEY" >> .env

# Notify the user of completion
echo ".env file created successfully with your Alchemy API key and PayPangea API key."

