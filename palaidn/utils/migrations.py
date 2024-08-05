# The MIT License (MIT)
# Copyright © 2023 Palaidn

import sqlite3

migrations = [
    {
        "id": "20230804_add_missing_fields",
        "description": "Add missing fields to wallet_transactions table",
        "queries": [
            "ALTER TABLE wallet_transactions ADD COLUMN scanID TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN minerID TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN miner_wallet TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN scan_date DATE",
            "ALTER TABLE wallet_transactions ADD COLUMN sender TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN receiver TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN transaction_date DATE",
            "ALTER TABLE wallet_transactions ADD COLUMN token_symbol TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN category TEXT",
            "ALTER TABLE wallet_transactions ADD COLUMN token_address TEXT"
        ]
    },
    # Add more migrations here as needed
]

def run_migrations(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()

    # Create migrations table if it doesn't exist
    c.execute("""CREATE TABLE IF NOT EXISTS migrations (
                    id TEXT PRIMARY KEY,
                    migration_name TEXT
                )""")

    for migration in migrations:
        migration_id = migration['id']
        c.execute("""SELECT 1 FROM migrations WHERE id = ?""", (migration_id,))
        result = c.fetchone()
        if result is None:
            for query in migration['queries']:
                c.execute(query)
            c.execute("""INSERT INTO migrations (id, migration_name) VALUES (?, ?)""",
                      (migration_id, migration['description']))
            conn.commit()

    conn.close()
