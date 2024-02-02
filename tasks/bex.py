import time
import asyncio
import logging
import random

from typing import Optional

from data.config import logger
from libs.py_eth_async.data.models import TokenAmount

from tasks.base import Base
from web3.exceptions import TransactionNotFound
from data.models import SwapInfo, Tokens, Pools, Routers, BaseContract


# Made by Alex
class BEX(Base):
    NAME = 'BEX'
    AVAILABLE_DEPOSIT = ['BERA', 'WBERA', 'STGUSDC', 'HONEY', 'WBTC', 'WETH']
    CONTRACT_MAP = {
        'BERA': Tokens.BERA,
        'WBTC': Tokens.WBTC,
        'WETH': Tokens.WETH,
        'WBERA': Tokens.WBERA,
        'HONEY': Tokens.HONEY,
        'STGUSDC': Tokens.STGUSDC,
    }
    POOLS_MAP = {
        'WERA_WBTC': Pools.WERA_WBTC,
        'WBERA_WETH': Pools.WBERA_WETH,
        'BERA_STGUSDC': Pools.BERA_STGUSDC,
        'STGUSDC_HONEY': Pools.STGUSDC_HONEY,
    }

    async def prepare_data_swap_bera(self, wrap_token, to_token,):
        amount = self.get_random_amount()
        slippage = 5
        if to_token.title != 'WBERA':
            pool_address, amount_out, pool_address_2, amount_out_2 = await self.quote_request(
                wrap_token.address,
                to_token.address,
                amount
            )

        # Wrap
        if to_token.title == 'WBERA':
            swap_data = '0xd0e30db0'
            return swap_data, amount
        # Swap
        elif to_token.title in ('WETH'):
            amount_out_s = int(float(amount_out) * (1 - slippage / 100))
            swap_data = (f'0xe3414c00'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'0000000000000000000000000000000000000000000000000000000000000060'
                         f'0000000000000000000000000000000000000000000000000000000005f5e0ff'
                         f'0000000000000000000000000000000000000000000000000000000000000001'
                         f'0000000000000000000000000000000000000000000000000000000000000020'
                         f'000000000000000000000000{pool_address[2:]}'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'{str(hex(amount.Wei))[2:].zfill(64)}'
                         f'000000000000000000000000{to_token.address[2:]}'
                         f'{hex(int(amount_out_s))[2:].zfill(64)}'
                         f'00000000000000000000000000000000000000000000000000000000000000c0'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         )
            return swap_data, amount

        elif to_token.title in ('STGUSDC'):
            if not amount_out_2.startswith('0x'):
                amount_out = amount_out_2

            amount_out_s = int(float(amount_out) * (1 - slippage / 100))

            swap_data = (f'0xe3414c00'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'0000000000000000000000000000000000000000000000000000000000000060'
                         f'0000000000000000000000000000000000000000000000000000000005f5e0ff'
                         f'0000000000000000000000000000000000000000000000000000000000000001'
                         f'0000000000000000000000000000000000000000000000000000000000000020'
                         f'000000000000000000000000{pool_address[2:]}'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'{str(hex(amount.Wei))[2:].zfill(64)}'
                         f'000000000000000000000000{to_token.address[2:].lower()}'
                         f'{hex(int(amount_out_s))[2:].zfill(64)}'
                         f'00000000000000000000000000000000000000000000000000000000000000c0'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         )
            return swap_data, amount

        elif to_token.title in ('WBTC'):
            amount_out_s = int(float(amount_out) * (1 - slippage / 100))
            amount_out_2_s = int(float(amount_out_2) * (1 - slippage / 100))

            swap_data = (f'0xe3414c00'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'0000000000000000000000000000000000000000000000000000000000000060'
                         f'0000000000000000000000000000000000000000000000000000000005f5e0ff'
                         f'0000000000000000000000000000000000000000000000000000000000000002'
                         f'0000000000000000000000000000000000000000000000000000000000000040'
                         f'0000000000000000000000000000000000000000000000000000000000000120'
                         f'000000000000000000000000{pool_address[2:]}'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'{str(hex(amount.Wei))[2:].zfill(64)}'
                         f'000000000000000000000000{BEX.CONTRACT_MAP["HONEY"].address[2:].lower()}'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'00000000000000000000000000000000000000000000000000000000000000c0'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'000000000000000000000000{pool_address_2[2:]}'
                         f'000000000000000000000000{BEX.CONTRACT_MAP["HONEY"].address[2:].lower()}'
                         f'{hex(int(amount_out_s))[2:].zfill(64)}'
                         f'000000000000000000000000{BEX.CONTRACT_MAP["WBTC"].address[2:].lower()}'
                         f'{hex(int(amount_out_2_s))[2:].zfill(64)}'
                         f'00000000000000000000000000000000000000000000000000000000000000c0'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         )
            return swap_data, amount

        elif to_token.title in ('HONEY'):
            if not amount_out_2.startswith('0x'):
                amount_out = amount_out_2

            amount_out_s = int(float(amount_out) * (1 - slippage / 100))

            swap_data = (f'0xe3414c00'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'0000000000000000000000000000000000000000000000000000000000000060'
                         f'0000000000000000000000000000000000000000000000000000000005f5e0ff'
                         f'0000000000000000000000000000000000000000000000000000000000000001'
                         f'0000000000000000000000000000000000000000000000000000000000000020'
                         f'000000000000000000000000{pool_address[2:]}'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         f'{str(hex(amount.Wei))[2:].zfill(64)}'
                         f'000000000000000000000000{to_token.address[2:].lower()}'
                         f'{hex(int(amount_out_s))[2:].zfill(64)}'
                         f'00000000000000000000000000000000000000000000000000000000000000c0'
                         f'0000000000000000000000000000000000000000000000000000000000000000'
                         )
            return swap_data, amount

    async def send_lend_tx(
            self,
            from_token,
            swap_data,
            swap_info: SwapInfo,
            amount: Optional[TokenAmount] = None,
            to_token: Optional[BaseContract] = None,
            test=False
    ):
        failed_text = f'Failed swap {from_token.title} to {to_token.title} via {swap_info.swap_platform.title}'

        try:
            if test:
                print(swap_data)

            if from_token.title == 'WBERA':
                if await self.check_balance_insufficient(amount):
                    logger.error(f'{self.eth_client.account.address} |'
                                 f'{swap_info.swap_platform.title} | swap | insufficient BERA balance')
                    return f'{failed_text}: insufficient balance.'

            logger.info(f'{self.eth_client.account.address} | {swap_info.swap_platform.title} | swap | '
                        f'{from_token.title} to {to_token.title} amount: {amount.Ether}')

            tx_params = {
                #'gasPrice': random.randint(1500000016, 1500000023),
                #'gas': random.randint(230000, 300000),
                'chainId': self.eth_client.network.chain_id,
                'nonce': await self.eth_client.wallet.nonce(),
                'from': self.eth_client.account.address,
                'to': swap_info.swap_platform.address if to_token.title != 'WBERA' else Routers.BEX_WETH.address,
                'data': swap_data,
                'value': amount.Wei if from_token.title == 'WBERA' else 0,
            }

            tx = await self.eth_client.transactions.sign_and_send(tx_params=tx_params)
            success_msg = (
                f'{amount.Ether} {from_token.title} was successfully swapped to {swap_info.token_to.title} '
                f'via {swap_info.swap_platform.title}')
            msg = await self.wait_tx_status(success_msg=success_msg, tx_hash=tx.hash.hex())
            if msg:
                return msg
            return f'Failed to swap via {swap_info.swap_platform.title}'

        except BaseException as e:
            logging.exception(f'{swap_info.swap_platform}.swap')
            return f'{failed_text}: {e}'

    async def swap_bera_to_token(self, to_token) -> str:
        wrap_token = BEX.CONTRACT_MAP['WBERA']
        bera_token = BEX.CONTRACT_MAP['BERA']
        to_token = BEX.CONTRACT_MAP[to_token]

        swap_info = SwapInfo(
            bera_token,
            to_token,
            Routers.BEX
        )
        failed_text = f'{self.data.address} | Failed to swap {bera_token.title}  via {swap_info.swap_platform.title}'

        try:
            swap_data, amount = await self.prepare_data_swap_bera(wrap_token, to_token)

            return await self.send_lend_tx(
                from_token=wrap_token,
                to_token=to_token,
                amount=amount,
                swap_data=swap_data,
                swap_info=swap_info,
            )

        except BaseException as e:
            logging.exception(f'BEX.wrap_bera')
            return f'{failed_text}: {e}'

    async def swap_to_bera(self, from_token) -> str:
        wrap_token = BEX.CONTRACT_MAP['WBERA']
        bera_token = BEX.CONTRACT_MAP['BERA']
        from_token = BEX.CONTRACT_MAP[from_token]

        swap_info = SwapInfo(
            from_token,
            wrap_token,
            Routers.BEX
        )
        failed_text = f'Failed to swap {bera_token.title}  via {swap_info.swap_platform.title}'

        try:
            swap_data, amount = await self.prepare_data_swap_bera(from_token, wrap_token)

            return await self.send_lend_tx(
                from_token=from_token,
                to_token=wrap_token,
                amount=amount,
                swap_data=swap_data,
                swap_info=swap_info,
            )

        except BaseException as e:
            logging.exception(f'BEX.wrap_bera')
            return f'{failed_text}: {e}'

    async def quote_request(self, from_token, to_token, amount):
        headers = {
            'authority': 'artio-80085-dex-router.berachain.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://artio.bex.berachain.com',
            'referer': 'https://artio.bex.berachain.com/',
            'sec-ch-ua': f'"Google Chrome";v="{self.version}", "Chromium";v="{self.version}", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.data.platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.data.user_agent,
        }

        params = {
            'quoteAsset': f'{to_token}',
            'baseAsset': f'{from_token}',
            'amount': f'{amount.Wei}',
            'swap_type': 'given_in',
        }

        max_retries = 5

        for retry_count in range(1, max_retries + 1):
            response = await self.async_session.get(
                'https://artio-80085-dex-router.berachain.com/dex/route',
                params=params,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                pools = data['steps']

                if len(pools) == 1:
                    pool_address = pools[0]['pool']
                    amount_out = pools[0]['amountOut']
                    return pool_address, amount_out, '0x', '0x'

                elif len(pools) == 2:
                    pool_1 = pools[0]['pool']
                    amount_out_1 = pools[0]['amountOut']
                    pool_2 = pools[1]['pool']
                    amount_out_2 = pools[1]['amountOut']
                    return pool_1, amount_out_1, pool_2, amount_out_2

            else:
                logger.error(f"Attempt {retry_count}: Request failed with status code: {response.status_code}")

    async def wait_tx_status(self, success_msg, tx_hash, max_wait_time=100):
        start_time = time.time()
        while True:
            try:
                receipts = await self.eth_client.w3.eth.get_transaction_receipt(tx_hash)
                status = receipts.get("status")
                if status == 1:
                    return (f"{success_msg} | tx hash: "
                            f"https://artio.beratrail.io//tx/{tx_hash}")
                elif status is None:
                    await asyncio.sleep(0.3)
                else:
                    return (f"{self.eth_client.account.address} | Couldn't Bera Swapped to STGUSDC | tx hash: "
                            f"https://artio.beratrail.io//tx/{tx_hash}")
            except TransactionNotFound:
                if time.time() - start_time > max_wait_time:
                    return (f"{self.eth_client.account.address} | Couldn't Bera Swapped to STGUSDC | tx hash: "
                            f"https://artio.beratrail.io//tx/{tx_hash}")
                await asyncio.sleep(3)

