# Miner Setup: `miner.json` Configuration

### Important:

**Once the setup is complete, you need to restart the miner for changes to take effect.**

## Manual Setup

After setting up your Alchemy API key, you'll need to configure the miner by creating or editing the `config/miner.json` file. This file tells the miner which networks and categories to monitor for transfers.

If not config/miner.json file is present, miner will scan the dafault configuration, which is ethereum network and categories erc20, erc721 and erc1155.

### Example `config/miner.json`

```json
{
    "networks": [
        {
            "name": "ethereum",
            "category": ["external", "erc20", "erc721", "erc1155"]
        },
        {
            "name": "polygon",
            "category": ["erc20", "erc721", "erc1155", "specialnft"]
        }
    ]
}
```

### Explanation of Fields:

2. **`networks`**:  
   - This is an array of network objects. Each network object represents a blockchain that your miner will track.
   
   - **Fields in `networks`:**
     - **`name`**: The name of the network. This can be either `ethereum` or `polygon` for Alchemy-supported chains.
     - **`category`**: This is a list of the types of transactions you want to monitor. The available categories are:
       - **`external`**: Regular ETH or MATIC transactions (depending on the network).
       - **`erc20`**: ERC-20 token transfers.
       - **`erc721`**: ERC-721 token (NFT) transfers.
       - **`erc1155`**: ERC-1155 multi-token transfers.
       - **`specialnft`**: Special NFT transfers (specific to certain blockchains like Polygon).

### Customizing the `miner.json`:

- **Adding/Removing Networks**:  
  You can add additional networks by appending more objects to the `networks` array. You can also remove networks you don’t want to track.
  
- **Filtering by Categories**:  
  The `category` field allows you to filter specific transaction types. For example, if you only want to track ERC-20 transfers, you can set `"category": ["erc20"]`.

- **Example**:  
  If you want to track only ERC-721 transfers on Ethereum and Polygon, your configuration might look like this:
  
  ```json
  {
      "networks": [
          {
              "name": "ethereum",
              "category": ["erc721"]
          },
          {
              "name": "polygon",
              "category": ["erc721"]
          }
      ]
  }
  ```


## Automatic Setup with a Script

You can also set up the miner automatically using a script, which will guide you through selecting the networks and transaction categories.

```bash
./scripts/setup_miner.sh
```

### How the Script Works:

1. **Network Selection**:  
   You will be prompted to select one or more blockchain networks from a predefined list (e.g., `ethereum` and `polygon`).
   
2. **Category Selection**:  
   For each network you choose, you will be asked to select one or more transaction categories from options like `external`, `erc20`, `erc721`, `erc1155`, and `specialnft`.

3. **JSON File Creation**:  
   Once you've made your selections, the script will automatically generate the `miner.json` file with the appropriate configuration.

### Example Process:

1. **Network Selection**:  
   You will first be prompted to choose a network. For instance, if you select `ethereum`, the script will ask you to select the categories for it.

2. **Category Selection**:  
   After choosing a network, you'll be asked to select transaction categories for that network. You can choose multiple categories like `erc20`, `erc721`, or `external`. The script ensures that you do not select the same category more than once.

3. **Final Configuration**:  
   Once you finish selecting networks and categories, the script will save the configuration in the `config/miner.json` file.

### Customizing with the Script:

You can run the script multiple times to update or modify the `miner.json` file. The script ensures that categories and networks are selected correctly and no duplicates are allowed.

### Example Output:

```bash
$ ./scripts/setup_miner.sh
Welcome to the Miner Setup!
You will configure the miner to fetch data from multiple blockchain networks.
Available blockchain networks:
1) ethereum
2) polygon
Select a network by number: 1
Selected network: ethereum
You must select at least one category for the network.
Available categories:
1) external
2) erc20
3) erc721
4) erc1155
5) specialnft
Select a category by number (or press enter to finish): 1
Added category: external
Available categories:
1) erc20
2) erc721
3) erc1155
4) specialnft
Select a category by number (or press enter to finish): 2
Added category: erc20
Select a category by number (or press enter to finish): 
Do you want to add another network? (y/n): y
Available blockchain networks:
1) polygon
Select a network by number: 1
Selected network: polygon
You must select at least one category for the network.
Available categories:
1) erc721
2) erc1155
3) specialnft
Select a category by number (or press enter to finish): 3
Added category: specialnft
Available categories:
1) erc721
2) erc1155
Select a category by number (or press enter to finish): 
No more available networks to select.
Miner configuration saved to ./config/miner.json
{
    "networks": [
        {
            "name": "ethereum",
            "category": ["external", "erc20"]
        },
        {
            "name": "polygon",
            "category": ["specialnft"]
        }
    ]
}
```


