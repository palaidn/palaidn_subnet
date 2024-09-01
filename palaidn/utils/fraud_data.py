# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Palaidn

import requests
import json
import uuid
from datetime import datetime, timezone
from dateutil import parser
import sqlite3
import bittensor as bt
import os
from palaidn.utils.migrations import run_migrations

class FraudData:
    def __init__(self, db_name="data/fraud.db"):
        self.db_name = db_name
        self.create_database()

    def create_database(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS wallet_transactions (
                        id TEXT PRIMARY KEY,
                        wallet_address TEXT,
                        base_address TEXT,
                        transaction_hash TEXT,
                        amount REAL,
                        is_fraudulent INTEGER
                    )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS migrations (
                        id TEXT PRIMARY KEY,
                        migration_name TEXT
                    )"""
        )
        conn.commit()
        conn.close()

        # Run migrations after creating the initial tables
        run_migrations(self.db_name)

    def insert_into_database(self, base_address, transaction_data, hotkeys):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()

        for tx in transaction_data:
            try:
                amount = tx.amount
                # Check if the amount can be converted to a float
                try:
                    amount = float(amount)
                except ValueError:
                    amount = 0.0

                minerWallet = hotkeys[int(tx.minerID)]

                now = datetime.now(timezone.utc).isoformat()

                # Check if the transaction is already in the database
                c.execute(
                    """SELECT COUNT(*) FROM wallet_transactions WHERE miner_wallet = ? AND transaction_hash = ?""",
                    (minerWallet, tx.transaction_hash)
                )

                exists = c.fetchone()

                # bt.logging.info(f"exists {exists}.")

                if exists and exists[0] > 0:
                    # If the transaction exists, update the scan_date
                    c.execute(
                        """UPDATE wallet_transactions
                        SET scan_date = ?
                        WHERE miner_wallet = ? AND transaction_hash = ?""",
                        (now, minerWallet, tx.transaction_hash)
                    )
                    conn.commit()
                    # bt.logging.info(f"Updated scan_date for transaction {tx.transaction_hash} for miner wallet {minerWallet} - {tx.scanDate}.")
                else:
                    # If the transaction does not exist, insert it
                    c.execute(
                        """INSERT INTO wallet_transactions (
                            id, wallet_address, base_address, transaction_hash, transaction_date, 
                            amount, token_symbol, category, token_address, is_fraudulent, scanID, minerID, miner_wallet, scan_date, sender, receiver)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(uuid.uuid4()),
                            tx.sender,
                            base_address,
                            tx.transaction_hash,
                            tx.transaction_date,
                            amount,
                            tx.token_symbol,
                            tx.category,
                            tx.token_address,
                            tx.scanID,
                            tx.minerID,
                            minerWallet,
                            now,
                            tx.sender,
                            tx.receiver
                        )
                    )
                    conn.commit()
                    # bt.logging.info(f"Inserted new transaction {tx.transaction_hash} for miner wallet {minerWallet}.")
            except sqlite3.Error as e:
                bt.logging.error(f"Error inserting transaction {tx.transaction_hash} into database: {e}")
                conn.rollback()

        conn.close()



    def mark_as_fraudulent(self, transaction_hash):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            """UPDATE wallet_transactions
               SET is_fraudulent = 1
               WHERE transaction_hash = ?""",
            (transaction_hash,)
        )
        conn.commit()
        conn.close()

    def is_transaction_fraudulent(self, transaction_hash):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            """SELECT is_fraudulent FROM wallet_transactions WHERE transaction_hash = ? LIMIT 1""",
            (transaction_hash,)
        )
        result = c.fetchone()
        conn.close()
        return result is not None and result[0] == 1

    def get_all_fraudulent_transactions(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            """SELECT * FROM wallet_transactions WHERE is_fraudulent = 1"""
        )
        transactions = c.fetchall()
        conn.close()
        return transactions

    def get_transactions_by_wallet(self, wallet_address):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute(
            """SELECT * FROM wallet_transactions WHERE wallet_address = ?""",
            (wallet_address,)
        )
        transactions = c.fetchall()
        conn.close()
        return transactions

    async def fetch_wallet_data(self, api_key):
        url = "https://api.paypangea.com/v1/palaidn/get-wallet"

        bt.logging.info(f"get data from: {url}")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        try:
            response = requests.get(url, headers=headers)
            bt.logging.info(f"response: {response}")

            if response.status_code == 200:
                wallet_data = response.json()
                wallet_address = wallet_data.get("wallet")
                is_fraud = wallet_data.get("is_fraud")
                
                if is_fraud == 1:
                    bt.logging.info(f"Fraudulent wallet detected: {wallet_address}")
                    return wallet_address
                else:
                    bt.logging.info(f"Wallet {wallet_address} is not fraudulent.")
                    return ''
            else:
                bt.logging.error(f"Failed to fetch wallet data: {response.status_code} - {response.text}")
                return ''

        except requests.exceptions.RequestException as e:
            bt.logging.error(f"An error occurred during the request: {e}")
            return ''
