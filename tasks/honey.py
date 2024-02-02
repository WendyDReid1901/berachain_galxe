import time
import random
import logging
import asyncio
from typing import Optional

from data.config import logger
from libs.py_eth_async.data.models import TokenAmount

from tasks.base import Base
from web3.exceptions import TransactionNotFound
from data.models import SwapInfo, Tokens, Routers, BaseContract


# Made by Alex
class HONEY(Base):
    NAME = 'HONEY_MINT'
    AVAILABLE_DEPOSIT = ['STGUSDC', 'HONEY']
    CONTRACT_MAP = {
        'HONEY': Tokens.HONEY,
        'STGUSDC': Tokens.STGUSDC,
    }

    async def prepare_data(self, from_token, balance: Optional[TokenAmount], value):
        swap_data = (f'0xc6c3bbe6'
                     f'{self.eth_client.account.address[2:].zfill(64)}'
                     f'{from_token.address[2:].zfill(64)}'
                     f'{hex(int(balance.Wei * value))[2:].zfill(64)}'
                     )
        return swap_data

    async def send_lend_tx(
            self,
            from_token,
            swap_data,
            swap_info: SwapInfo,
            to_token: Optional[BaseContract] = None,
            balance: Optional[TokenAmount] = None,
            value: float = None,
            test=False
    ):
        failed_text = f'{self.data.address} | Failed swap {from_token.title} to {to_token.title} via {swap_info.swap_platform.title}'

        try:
            if test:
                print(swap_data)

            if from_token.title == 'STGUSDC':
                if not balance.Ether:
                    logger.error(f'{self.eth_client.account.address} | '
                                 f'{swap_info.swap_platform.title} | swap | insufficient STGUSDC balance')
                    return f'{failed_text}: insufficient balance.'

            logger.info(f'{self.eth_client.account.address} | {swap_info.swap_platform.title} | mint | '
                        f'{from_token.title} to {to_token.title} amount: {(int(balance.Wei * value)) / 10 ** 18}')

            if not await self.approve_interface(
                    token_address=from_token.address,
                    spender=Routers.HONEY_MINT.address,
                    amount=balance
            ):
                return f'{failed_text}: token not approved.'

            await asyncio.sleep(random.randint(10, 20))

            tx_params = {
                # 'gasPrice': gas_price.Wei,
                # 'gas': 9000000,
                'chainId': self.eth_client.network.chain_id,
                'nonce': await self.eth_client.wallet.nonce(),
                'from': self.eth_client.account.address,
                'to': swap_info.swap_platform.address,
                'data': swap_data,
            }

            tx = await self.eth_client.transactions.sign_and_send(tx_params=tx_params)
            success_msg = (f'{(int(balance.Wei * value)) / 10 ** 18} {to_token.title} was successfully minted to'
                           f' {swap_info.token_from.title} via {swap_info.swap_platform.title}')
            msg = await self.wait_tx_status(success_msg=success_msg, tx_hash=tx.hash.hex())
            if msg:
                return msg
            return f'Failed to swap via {swap_info.swap_platform.title}'

        except BaseException as e:
            logging.exception(f'{swap_info.swap_platform}.swap')
            return f'{failed_text}: {e}'

    async def mint_honey(self, value) -> str:
        from_token = HONEY.CONTRACT_MAP['STGUSDC']
        to_token = HONEY.CONTRACT_MAP['HONEY']
        balance = await self.eth_client.wallet.balance(
            token=from_token.address
        )
        if not balance:
            return "No balance"

        swap_info = SwapInfo(
            from_token,
            to_token,
            Routers.HONEY_MINT
        )

        failed_text = f'Failed to mint {from_token.title} via {swap_info.swap_platform.title}'

        try:
            swap_data = await self.prepare_data(from_token, balance, value)

            return await self.send_lend_tx(
                from_token=from_token,
                to_token=to_token,
                swap_data=swap_data,
                swap_info=swap_info,
                balance=balance,
                value=value,
            )

        except BaseException as e:
            logging.exception(f'Honey.mint')
            return f'{failed_text}: {e}'

    async def wait_tx_status(self, success_msg, tx_hash, max_wait_time=100):
        start_time = time.time()
        while True:
            try:
                receipts = await self.eth_client.w3.eth.get_transaction_receipt(tx_hash)
                status = receipts.get("status")
                if status == 1:
                    return f"{success_msg} | tx hash: https://artio.beratrail.io//tx/{tx_hash}"
                elif status is None:
                    await asyncio.sleep(0.3)
                else:
                    return (f"{self.data.address} | Swap HONEY unsuccessful | tx hash: "
                            f"https://artio.beratrail.io//tx/{tx_hash}")
            except TransactionNotFound:
                if time.time() - start_time > max_wait_time:
                   return (f"{self.data.address} | Swap HONEY unsuccessful | tx hash: "
                           f"https://artio.beratrail.io//tx/{tx_hash}")
                await asyncio.sleep(3)
