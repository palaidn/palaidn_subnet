from argparse import ArgumentParser
from typing import List, Dict, Any, Tuple
import sys
import bittensor as bt
import sqlite3
from palaidn.base.neuron import BaseNeuron
from palaidn.protocol import PalaidnData, ScanWalletTransactions
from palaidn.utils.sign_and_validate import verify_signature
import datetime
import os
import threading
from contextlib import contextmanager
import requests
import uuid

from dotenv import load_dotenv

class PalaidnMiner(BaseNeuron):
    """
    The PalaidnMiner class contains all of the code for a Miner neuron

    Attributes:
        neuron_config:
            This attribute holds the configuration settings for the neuron:
            bt.subtensor, bt.wallet, bt.logging & bt.axon
        miner_set_weights:
            A boolean attribute that determines whether the miner sets weights.
            This is set based on the command-line argument args.miner_set_weights.
        wallet:
            Represents an instance of bittensor.wallet returned from the setup() method.
        subtensor:
            An instance of bittensor.subtensor returned from the setup() method.
        metagraph:
            An instance of bittensor.metagraph returned from the setup() method.
        miner_uid:
            An int instance representing the unique identifier of the miner in the network returned
            from the setup() method.
        hotkey_blacklisted:
            A boolean flag indicating whether the miner's hotkey is blacklisted.

    """
    alchemy_api_key = 'empty'

    default_db_path = "./data/miner.db"

    def __init__(self, parser: ArgumentParser):
        """
        Initializes the Miner class.

        Arguments:
            parser:
                An ArgumentParser instance.

        Returns:
            None
        """
        super().__init__(parser=parser, profile="miner")

        # Neuron configuration
        self.neuron_config = self.config(
            bt_classes=[bt.subtensor, bt.logging, bt.wallet, bt.axon]
        )

        args = parser.parse_args()


        # TODO If users want to run a dual miner/vali. Not fully implemented yet.
        if args.miner_set_weights == "False":
            self.miner_set_weights = False
        else:
            self.miner_set_weights = True

        # Minimum stake for validator whitelist
        self.validator_min_stake = args.validator_min_stake

        # Neuron setup
        self.wallet, self.subtensor, self.metagraph, self.miner_uid = self.setup()
        self.hotkey_blacklisted = False
        self.hotkey = self.wallet.hotkey.ss58_address

        os.environ["HOTKEY"] = self.wallet.hotkey.ss58_address
        os.environ["UID"] = str(self.miner_uid)

        # Ensure the data directory exists
        os.makedirs(os.path.dirname("data/miner_env.txt"), exist_ok=True)

        # Check if the miner's hotkey is already in the file
        if not self.hotkey_exists_in_file("data/miner_env.txt", self.wallet.hotkey.ss58_address):
            with open("data/miner_env.txt", "a") as f:
                f.write(
                    f"UID={self.miner_uid}, HOTKEY={self.wallet.hotkey.ss58_address}\n"
                )
            bt.logging.info(f"Added miner info to data/miner_env.txt")
        else:
            bt.logging.info(f"Miner info already exists in data/miner_env.txt")

        bt.logging.trace(
            f"Miner stats initialized with miner instance"
        )


    def setup(self) -> Tuple[bt.wallet, bt.subtensor, bt.metagraph, str]:
        """This function sets up the neuron.

        The setup function initializes the neuron by registering the
        configuration.

        Arguments:
            None

        Returns:
            wallet:
                An instance of bittensor.wallet containing information about
                the wallet
            subtensor:
                An instance of bittensor.subtensor
            metagraph:
                An instance of bittensor.metagraph
            miner_uid:
                An instance of int consisting of the miner UID

        Raises:
            AttributeError:
                The AttributeError is raised if wallet, subtensor & metagraph cannot be logged.
        """
        bt.logging(config=self.neuron_config, logging_dir=self.neuron_config.full_path)
        bt.logging.info(
            f"Initializing miner for subnet: {self.neuron_config.netuid} on network: {self.neuron_config.subtensor.chain_endpoint} with config:\n {self.neuron_config}"
        )

        # Setup the bittensor objects
        try:
            wallet = bt.wallet(config=self.neuron_config)
            subtensor = bt.subtensor(config=self.neuron_config)
            metagraph = subtensor.metagraph(self.neuron_config.netuid)
        except AttributeError as e:
            bt.logging.error(f"Unable to setup bittensor objects: {e}")
            sys.exit()

        bt.logging.info(
            f"Bittensor objects initialized:\nMetagraph: {metagraph}\
            \nSubtensor: {subtensor}\nWallet: {wallet}"
        )

        # Validate that our hotkey can be found from metagraph
        if wallet.hotkey.ss58_address not in metagraph.hotkeys:
            bt.logging.error(
                f"Your miner: {wallet} is not registered to chain connection: {subtensor}. Run btcli register and try again"
            )
            sys.exit()

        # Get the unique identity (UID) from the network
        miner_uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
        bt.logging.info(f"Miner is running with UID: {miner_uid}")

        return wallet, subtensor, metagraph, miner_uid

    def check_whitelist(self, hotkey):
        """
        Checks if a given validator hotkey has been whitelisted.

        Arguments:
            hotkey:
                A str instance depicting a hotkey.

        Returns:
            True:
                True is returned if the hotkey is whitelisted.
            False:
                False is returned if the hotkey is not whitelisted.
        """

        if isinstance(hotkey, bool) or not isinstance(hotkey, str):
            return False

        whitelisted_hotkeys = []

        if hotkey in whitelisted_hotkeys:
            return True

        return False

    def blacklist(self, synapse: PalaidnData) -> Tuple[bool, str]:
        """
        This function is executed before the synapse data has been
        deserialized.

        On a practical level this means that whatever blacklisting
        operations we want to perform, it must be done based on the
        request headers or other data that can be retrieved outside of
        the request data.

        As it currently stands, we want to blacklist requests that are
        not originating from valid validators. This includes:
        - unregistered hotkeys
        - entities which are not validators
        - entities with insufficient stake

        Returns:
            [True, ""] for blacklisted requests where the reason for
            blacklisting is contained in the quotes.
            [False, ""] for non-blacklisted requests, where the quotes
            contain a formatted string (f"Hotkey {synapse.dendrite.hotkey}
            has insufficient stake: {stake}",)
        """

        # Check whitelisted hotkeys (queries should always be allowed)
        if self.check_whitelist(hotkey=synapse.dendrite.hotkey):
            bt.logging.info(f"Accepted whitelisted hotkey: {synapse.dendrite.hotkey})")
            return (False, f"Accepted whitelisted hotkey: {synapse.dendrite.hotkey}")

        # Blacklist entities that have not registered their hotkey
        if synapse.dendrite.hotkey not in self.metagraph.hotkeys:
            bt.logging.info(f"Blacklisted unknown hotkey: {synapse.dendrite.hotkey}")
            return (
                True,
                f"Hotkey {synapse.dendrite.hotkey} was not found from metagraph.hotkeys",
            )

        # Blacklist entities that are not validators
        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        # print("uid:", uid)
        # print("metagraph", self.metagraph)
        if not self.metagraph.validator_permit[uid]:
            bt.logging.info(f"Blacklisted non-validator: {synapse.dendrite.hotkey}")
            return (True, f"Hotkey {synapse.dendrite.hotkey} is not a validator")


        bt.logging.info(f"validator_min_stake: {self.validator_min_stake}")
        # Blacklist entities that have insufficient stake
        stake = float(self.metagraph.S[uid])
        if stake < self.validator_min_stake:
            bt.logging.info(
                f"Blacklisted validator {synapse.dendrite.hotkey} with insufficient stake: {stake}"
            )
            return (
                True,
                f"Hotkey {synapse.dendrite.hotkey} has insufficient stake: {stake}",
            )

        # Allow all other entities
        bt.logging.info(
            f"Accepted hotkey: {synapse.dendrite.hotkey} (UID: {uid} - Stake: {stake})"
        )
        return (False, f"Accepted hotkey: {synapse.dendrite.hotkey}")

    def priority(self, synapse: PalaidnData) -> float:
        """
        Assigns a priority to the synapse based on the stake of the validator.
        """

        # Prioritize whitelisted validators
        if self.check_whitelist(hotkey=synapse.dendrite.hotkey):
            return 10000000.0

        # Otherwise prioritize validators based on their stake
        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        stake = float(self.metagraph.S[uid])

        # print(f"Prioritized: {synapse.dendrite.hotkey} (UID: {uid} - Stake: {stake})")

        return stake

    def forward(self, synapse: PalaidnData) -> PalaidnData:
        bt.logging.info(f"Miner: Received synapse from {synapse.dendrite.hotkey}")

        # Print version information and perform version checks
        bt.logging.info(
            f"Synapse version: {synapse.subnet_version}, our version: {self.subnet_version}"
        )
        if synapse.subnet_version > self.subnet_version:
            bt.logging.warning(
                f"Received a synapse from a validator with higher subnet version ({synapse.subnet_version}) than yours ({self.subnet_version}). Please update the miner, or you may encounter issues."
            )
        if synapse.subnet_version < self.subnet_version:
            bt.logging.warning(
                f"Received a synapse from a validator with lower subnet version ({synapse.subnet_version}) than yours ({self.subnet_version}). You can safely ignore this warning."
            )

        bt.logging.info(f"Miner: synapse {synapse}")
        bt.logging.info(f"Miner: synapse {synapse}")

        transactions = self.trace_transactions(synapse.wallet_address)

        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="minutes")

        bt.logging.info(f"Processing ...")

        transactions_dict = []
        scanID = str(uuid.uuid4())

        for tx in transactions:
            bt.logging.trace(f" Processing transactions: {tx}")

            transact = ScanWalletTransactions(
                scanID=scanID,
                minerID=str(synapse.neuron_uid),
                scanDate=current_time,
                sender=synapse.wallet_address,
                receiver=tx['to'],
                transaction_hash=tx['transaction_hash'],
                transaction_date=tx['transaction_date'],
                amount=str(tx['amount']),
                category=tx['category'],
                token_symbol=tx['token_symbol'],
                token_address=tx['token_address']
            )
            transactions_dict.append(transact)

        synapse.transactions_dict = transactions_dict

        return synapse


    def hotkey_exists_in_file(self, file_path, hotkey):
        if not os.path.exists(file_path):
            return False
        with open(file_path, "r") as f:
            for line in f:
                if f"HOTKEY={hotkey}" in line:
                    return True
        return False

    def trace_transactions(self, wallet_address: str) -> List[Dict[str, Any]]:
        bt.logging.debug(f"Miner: transactions {wallet_address}")
        erc20_transfers = self.get_erc20_transfers(wallet_address)

        tainted_wallets = set(wallet_address)
        trace_result = []

        for tx in erc20_transfers:
            bt.logging.debug(f"Miner: transactions {tx}")
            from_address = tx.get('from', '') or ''
            to_address = tx.get('to', '') or ''
            trace_result.append({
                'transaction_hash': tx.get('hash', '') or '',
                'from': from_address,
                'to': to_address,
                'transaction_date': tx.get('metadata', {}).get('blockTimestamp', '') or '',
                'amount': tx.get('value', '') or '',
                'token_symbol': tx.get('asset', '') or '',
                'category': tx.get('category', '') or '',
                'token_address': tx.get('token_address', '') or ''
            })

        return trace_result



    def get_erc20_transfers(self, wallet_address: str) -> List[Dict[str, Any]]:
        url = f"https://eth-mainnet.g.alchemy.com/v2/{self.alchemy_api_key}"

        bt.logging.debug(f"get_erc20_transfers: wallet_address {wallet_address} -> {url}")
        
        headers = {
            'Content-Type': 'application/json'
        }

        payload = {
            "jsonrpc": "2.0",
            "method": "alchemy_getAssetTransfers",
            "params": [{
                "fromBlock": "0x0",
                "toBlock": "latest",
                "fromAddress": wallet_address,
                "category": ["erc721", "erc20", "erc1155"],
                "withMetadata": True,
                "excludeZeroValue": True
            }],
            "id": 1
        }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        
        bt.logging.debug(f"get_erc20_transfers: response {data}")
        return data.get('result', {}).get('transfers', [])