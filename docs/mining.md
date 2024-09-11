# Guide for Miners

1. **Obtain API key(s) from Alchemy**:

Setting up your Alchemy API key is essential for the validation of transactions received from miners. For detailed instructions, visit the [Alchemy instructions](docs/alchemy-setup.md)

2. **Obtain your PayPangea API key**:

Paypangea is a free decentralised wallet that we use for web3 authentication. You will find your API key under Profile settings on the top right corner.

3. **Set up your miner**:

Follow the instructions in the [mining-instructions.md](docs/mining-instructions.md) to configure your miner after obtaining the API keys.

4. **Run the miner setup**:

Run the following command and follow the prompts to complete the miner setup:
```bash
bash ./scripts/start_miner.sh
```

5. **Verify the `.env` file**:

After running the setup, check if the .env file was created in your root directory with the following content:

```bash
ALCHEMY_API_KEY=<YOUR_API_KEY>
PAYPANGEA_API_KEY=<YOUR_API_KEY>
```

>[!NOTE]
> We recommend running with --logging.trace while we are in Beta. This is much more verbose, but it will help us to debug if you run into issues.