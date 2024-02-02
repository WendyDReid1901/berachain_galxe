from typing import Optional

from better_automation.base import BaseAsyncSession

from libs.py_eth_async.client import Client
from utils.floats import randfloat
from data.config import logger
from data.models import Ether, TokenAmount, Settings
from db_api.database import Wallet


class Base:
    def __init__(self, data: Wallet, eth_client: Client, async_session: BaseAsyncSession):
        self.data = data
        self.eth_client = eth_client
        self.async_session = async_session
        self.version = self.data.user_agent.split('Chrome/')[1].split('.')[0]

    async def get_decimals(self, contract_address: str) -> int:
        contract = await self.eth_client.contracts.default_token(contract_address=contract_address)
        return await contract.functions.decimals().call()

    def get_random_amount(self):
        settings = Settings()
        return Ether(randfloat(
            from_=settings.bera_amount_for_swap.from_,
            to_=settings.bera_amount_for_swap.to_,
            step=0.0000001
        ))

    async def check_balance_insufficient(self, amount):
        """returns if balance does not have enough token"""
        balance = await self.eth_client.wallet.balance()
        # if balance < amount + settings.minimal_balance:
        if balance.Ether < amount.Ether:
            return True
        return False

    async def submit_transaction(self, tx_params, test=False):
        gas = await self.eth_client.transactions.estimate_gas(w3=self.eth_client.w3, tx_params=tx_params)

        tx_params['gas'] = gas.Wei

        if test:
            print(tx_params['data'])
            return "test", "test"
        else:
            tx = await self.eth_client.transactions.sign_and_send(tx_params=tx_params)
            return await tx.wait_for_receipt(client=self.eth_client, timeout=300), tx.hash.hex()

    async def approve_interface(self, token_address, spender, amount: Optional[TokenAmount] = None) -> bool:
        logger.info(
            f'{self.eth_client.account.address} | start approve token_address: {token_address} for spender: {spender}'
        )
        balance = await self.eth_client.wallet.balance(token=token_address)

        if balance <= 0:
            logger.error(f'{self.eth_client.account.address} | approve | zero balance')
            return False

        if not amount or amount.Wei > balance.Wei:
            amount = balance

        approved = await self.eth_client.transactions.approved_amount(
            token=token_address,
            spender=spender,
            owner=self.eth_client.account.address
        )

        if amount.Wei <= approved.Wei:
            logger.info(f'{self.eth_client.account.address} | approve | already approved')
            return True

        tx = await self.eth_client.transactions.approve(
            token=token_address,
            spender=spender,
            amount=amount
        )
        receipt = await tx.wait_for_receipt(client=self.eth_client, timeout=300)

        if receipt:
            return True

        return False
