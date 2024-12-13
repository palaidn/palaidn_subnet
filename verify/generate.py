from substrateinterface import Keypair
from os import getenv, environ
from datetime import datetime
import bittensor
import sys

# Hardcode or set the environment variable WALLET_PASS to the password for the wallet
# environ["WALLET_PASS"] = ""


def main(args):
    try:
        wallet = bittensor.wallet(name=args.name)
    except Exception as e:
        print(f"Error loading wallet: {e}")
        sys.exit(1)

    try:
        keypair = wallet.coldkey
    except Exception as e:
        print(f"Error accessing coldkey: {e}")
        sys.exit(1)
    
    timestamp = datetime.now()
    timezone = timestamp.astimezone().tzname()

    message = f"On {timestamp} {timezone} {args.message}"
    try:
        signature = keypair.sign(data=message)
    except Exception as e:
        print(f"Error signing message: {e}")
        sys.exit(1)

    file_contents = f"{message}\n\tSigned by: {keypair.ss58_address}\n\tSignature: {signature.hex()}"
    print(file_contents)
    open("message_and_signature.txt", "w").write(file_contents)

    print(f"Signature generated and saved to message_and_signature.txt")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a signature")
    parser.add_argument("--message", help="The message to sign", type=str)
    parser.add_argument("--name", help="The wallet name", type=str)
    args = parser.parse_args()

    main(args)
