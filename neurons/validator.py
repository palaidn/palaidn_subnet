# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Palaidn

import bittensor as bt
import time
import os
import sys
import random
import asyncio
from argparse import ArgumentParser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from palaidn.validator.validator import PalaidnValidator
from palaidn.utils.fraud_data import FraudData

from palaidn.protocol import PalaidnData

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from palaidn import __version__ as version

async def main(validator: PalaidnValidator):

    load_dotenv()
    paypangea_api_key = os.getenv('PAYPANGEA_API_KEY')
    alchemy_api_key = os.getenv("ALCHEMY_API_KEY")

    validator.alchemy_api_key = alchemy_api_key

    fraud_data = FraudData()

    # validator_rank = await validator.get_validators_ranked_by_stake()
    validator_rank = 0
    validator.target_group = validator_rank

    last_api_call = datetime.now()

    validator.serve_axon()
    await validator.initialize_connection()

    validator.check_hotkeys()

    validator.metagraph = await validator.sync_metagraph()

    while True:

        try:
            await validator.check_socket()

            log = (
                    f"Version:{version} ** | "
                    f"Step:{validator.step} | "
                )

            if validator.step % 600 == 0:
                bt.logging.debug(
                    f"Syncing rank of validator"
                )

                validator_rank = await validator.get_validators_ranked_by_stake()
                validator.target_group = validator_rank

            bt.logging.info(log)
            bt.logging.info(f"Validator UID: {validator.uid}")
            bt.logging.info(f"Round: {validator.target_group}")

            if validator.target_group == validator_rank:
                # Reset and get new wallet to scan
                validator.alchemy_transactions = None
                fraud_data_wallet = await fraud_data.fetch_wallet_data(paypangea_api_key)
                validator.alchemy_transactions, _ = await validator.get_erc20_transfers(fraud_data_wallet)

                bt.logging.debug(f"validator.alchemy_transactions: {validator.alchemy_transactions}")


            # Periodically sync subtensor status and save the state file
            if validator.step % 5 == 0:
                # Sync metagraph
                try:
                    validator.metagraph = await validator.sync_metagraph()
                    bt.logging.debug(f"Metagraph synced: {validator.metagraph}")
                except TimeoutError as e:
                    bt.logging.error(f"Metagraph sync timed out: {e}")

                # Update local knowledge of the hotkeys
                validator.check_hotkeys()

                # Save state
                validator.save_state()

            # Get all axons
            all_axons = validator.metagraph.axons

            # If there are more axons than scores, append the scores list and add new miners to the database
            axon_count = len(validator.metagraph.uids.tolist())
            score_count = len(validator.scores)

            # If there are more axons than scores, append the scores list and add new miners to the database
            if axon_count > score_count:
                bt.logging.info(
                    f"Discovered new Axons, current scores: {validator.scores}"
                )
                    # Append 0.0 for each new axon that doesn't yet have a score
                for _ in range(axon_count - score_count):
                    validator.scores.append(0.0)
                
                bt.logging.info(f"Updated scores, new scores: {validator.scores}")

            # validator.add_new_miners()

            # Get list of UIDs to query
            (
                uids_to_query,
                list_of_uids,
                blacklisted_uids,
                uids_not_to_query,
            ) = validator.get_uids_to_query(all_axons=all_axons)

            if not uids_to_query:
                bt.logging.warning(f"UIDs to query is empty: {uids_to_query}")

            # Broadcast query to valid Axons
            # current_time = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            current_time = datetime.now(timezone.utc).isoformat()
            # metadata = Metadata.create(validator.wallet, validator.subnet_version, validator.uid)

            synapse = PalaidnData.create(
                wallet=validator.wallet,
                subnet_version=validator.subnet_version,
                neuron_uid=validator.uid,
                wallet_data=fraud_data_wallet
            )
            
            responses = validator.dendrite.query(
                axons=uids_to_query,
                synapse=synapse,
                timeout=validator.timeout,
                deserialize=False,
            )

            # Process blacklisted UIDs (set scores to 0)
            bt.logging.debug(f"blacklisted_uids: {blacklisted_uids}")
            for uid in blacklisted_uids:
                if uid is not None:
                    bt.logging.debug(
                        f"Setting score for blacklisted UID: {uid}. Old score: {validator.scores[uid]}"
                    )
                    validator.scores[uid] = (
                        validator.neuron_config.alpha * validator.scores[uid]
                        + (1 - validator.neuron_config.alpha) * 0.0
                    )
                    bt.logging.debug(
                        f"Set score for blacklisted UID: {uid}. New score: {validator.scores[uid]}"
                    )

            # Process UIDs we did not query (set scores to 0)
            bt.logging.debug(f"uids_not_to_query: {uids_not_to_query}")
            for uid in uids_not_to_query:
                if uid is not None:

                    validator_alpha_type = type(validator.neuron_config.alpha)
                    validator_scores_type = type(validator.scores[uid])

                    bt.logging.debug(
                        f"validator_alpha_type: {validator_alpha_type}, validator_scores_type: {validator_scores_type}"
                    )
                    validator.scores[uid] = (
                        validator.neuron_config.alpha * validator.scores[uid]
                        + (1 - validator.neuron_config.alpha) * 0.0
                    )
                    bt.logging.trace(
                        f"Set score for not queried UID: {uid}. New score: {validator.scores[uid]}"
                    )

            if not responses:
                print("No responses received. Sleeping for 30 seconds.")
                time.sleep(30)

            # Process the responses
            if responses and any(responses):
                bt.logging.debug(
                    f"responses: {responses}"
                )
                bt.logging.debug(
                    f"list_of_uids: {list_of_uids}"
                )
                validator.process_miner_data(
                    processed_uids=list_of_uids, transactions=responses
                )

            
            await validator.check_socket()

            current_block = await validator.run_sync_in_async(lambda: validator.subtensor.block)

            bt.logging.debug(f"Current block {current_block}")
            blocks_since_last_update = validator.subtensor.blocks_since_last_update(validator.neuron_config.netuid, validator.uid)
            bt.logging.debug(f"blocks_since_last_update {blocks_since_last_update}")
            weights_rate_limit = validator.subtensor.weights_rate_limit(validator.neuron_config.netuid)
            bt.logging.debug(f"weights_rate_limit {weights_rate_limit}")
            blocks_to_wait = weights_rate_limit - blocks_since_last_update
            
            # bt.logging.debug(f"Last block that weights were updated: {validator.last_updated_block} | difference: {300 - current_block + validator.last_updated_block}")

            bt.logging.debug(
                f"Version:{version} ** | "
                f"Current Step: {validator.step} | "
                f"Current block: {current_block} | "
                f"weight_update_in: {blocks_to_wait} | "
            )

                
            if blocks_to_wait < 0 or validator.step % 50 == 0:
                # Periodically update the weights on the Bittensor blockchain.
                try:
                    bt.logging.info("Attempting to update weights")
                    if validator.subtensor is None:
                        bt.logging.warning("Subtensor is None. Attempting to reinitialize...")
                        validator.subtensor = await validator.initialize_connection()
                    
                    if validator.subtensor is not None:
                        success = await validator.set_weights()
                        if success:
                            # Update validators knowledge of the last updated block
                            validator.last_updated_block = await validator.run_sync_in_async(lambda: validator.subtensor.block)

                            validator.save_state()
                            bt.logging.info("Successfully updated weights and last updated block")
                        else:
                            bt.logging.info("Failed to set weights, continuing with next iteration.")
                    else:
                        bt.logging.error("Failed to reinitialize subtensor. Skipping weight update.")
                except Exception as e:
                    bt.logging.error(f"Error during weight update process: {str(e)}")
                    bt.logging.warning("Continuing with next iteration despite weight update failure.")

            # End the current step and prepare for the next iteration.
            validator.step += 1

            # sleep_duration = random.randint(90, 180)
            sleep_duration = 90
            bt.logging.debug(f"Sleeping for: {sleep_duration} seconds")
            await asyncio.sleep(sleep_duration)


        except Exception as e:
            # Log any unexpected errors
            bt.logging.error(f"An error occurred in the main loop: {str(e)}")
            bt.logging.info("Attempting to recover...")

            # Optional: Sleep for a bit before retrying to avoid rapid loops in case of consistent errors
            await asyncio.sleep(30)

            # Try to reinitialize the connection if necessary
            try:
                await validator.initialize_connection()
            except Exception as conn_error:
                bt.logging.error(f"Failed to reinitialize connection: {str(conn_error)}")
                bt.logging.warning("Retrying in the next iteration.")


# if __name__ == "__main__":
#     with PalaidnValidator() as validator:
#         asyncio.get_event_loop().run_until_complete(main(validator))


if __name__ == "__main__":
    parser = ArgumentParser()

    parser.add_argument('--subtensor.network', type=str, help="The subtensor network to connect to")
    parser.add_argument('--subtensor.chain_endpoint', type=str, help="The subtensor chain endpoint to connect to")
    parser.add_argument('--wallet.name', type=str, help="The name of the wallet to use")
    parser.add_argument('--wallet.hotkey', type=str, help="The hotkey of the wallet to use")
    parser.add_argument('--logging.debug', action='store_true', help="Enable debug logging")
    parser.add_argument('--logging.info', action='store_true', help="Enable info logging")
    parser.add_argument('--logging.trace', action='store_true', help="Enable trace logging")
    parser.add_argument(
        "--alpha", type=float, default=0.9, help="The alpha value for the validator."
    )
    parser.add_argument("--netuid", type=int, default=30, help="The chain subnet uid.")
    parser.add_argument('--axon.port', type=int, help="The port this axon endpoint is serving on.")
    parser.add_argument(
        "--max_targets",
        type=int,
        default=32,
        help="Sets the value for the number of targets to query at once",
    )
    parser.add_argument(
        "--load_state",
        type=str,
        default="True",
        help="WARNING: Setting this value to False clears the old state.",
    )
    args = parser.parse_args()
    
    validator = PalaidnValidator(parser=parser)

    if (
        not validator.apply_config(bt_classes=[bt.subtensor, bt.logging, bt.wallet])
        or not validator.initialize_neuron()
    ):
        bt.logging.error("Unable to initialize Validator. Exiting.")
        sys.exit()

    asyncio.get_event_loop().run_until_complete(main(validator))
