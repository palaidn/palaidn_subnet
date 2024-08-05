# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Palaidn

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import typing
import bittensor as bt

from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from palaidn.utils.sign_and_validate import create_signature
import uuid
from typing import Any, Dict, Optional, List

class ScanWalletTransactions(BaseModel):
    """
    Data class from json. 
    """

    scanID: str = Field(..., description="UUID of the scan")
    minerID: str = Field(
        ..., description="UUID of the miner (coldkey/hotkey) that made the prediction"
    )
    scanDate: str = Field(..., description="Prediction date of the prediction")
    sender: str = Field(..., description="Originating wallet")
    receiver: str = Field(..., description="Receiving wallet")
    transaction_hash: str = Field(..., description="transaction hash")
    transaction_date: str = Field(..., description="Date of the transaction")
    amount: str = Field(..., description="amount")
    token_symbol: str = Field(..., description="token symbol")
    category: str = Field(..., description="token symbol")
    token_address: str = Field(..., description="address of erc20 ot nft token")
    

class PalaidnData(bt.Synapse):
    """
    Custom protocol for Palaidn project.
    This protocol handles requests containing a wallet address and expects a response with transaction trace data.
    """

    # Required request input, filled by sending dendrite caller.

    wallet_address: str
    neuron_uid: int
    subnet_version: str
    transactions_dict: Optional[List[ScanWalletTransactions]]

    @classmethod
    def create(
        cls,
        wallet: bt.wallet,
        subnet_version,
        neuron_uid,
        wallet_data: str,
        transactions_dict: Optional[List[ScanWalletTransactions]] = [],
    ):
        wallet_address = wallet_data
        neuron_uid = neuron_uid
        subnet_version=subnet_version
        
        return cls(
            subnet_version=subnet_version,
            wallet_address=wallet_address,
            neuron_uid=neuron_uid,
            transactions_dict=transactions_dict,
        )

    def deserialize(self):
        return self.wallet_address, self.neuron_uid, self.subnet_version, self.transactions_dict
