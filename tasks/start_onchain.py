import random
import traceback

import asyncio
from better_automation.base import BaseAsyncSession
from sqlalchemy.ext.asyncio import AsyncSession

from db_api.models import Wallet
from data.config import logger
from settings.settings import NUMBER_OF_ATTEMPTS
from tasks.bex import BEX
from tasks.honey import HONEY
from libs.py_eth_async.client import Client
from data.models import Tokens
from data.models import Networks
from settings.settings import FROM, TO
from db_api.database import db


class OnChain:
    def __init__(self, data: Wallet):
        self.data = data
        self.version = self.data.user_agent.split('Chrome/')[1].split('.')[0]
        self.eth_client = Client(
            private_key=self.data.private_key,
            network=Networks.Berachain,
            proxy=self.data.proxy,
            user_agent=self.data.user_agent
        )
        self.async_session = BaseAsyncSession(proxy=data.proxy, verify=False, user_agent=self.data.user_agent)
        self.bex = BEX(data=data, eth_client=self.eth_client, async_session=self.async_session)
        self.honey = HONEY(data=data, eth_client=self.eth_client, async_session=self.async_session)

    async def start_onchain(self):
        value = random.uniform(0.3, 0.5)
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            try:
                logger.info(f'{self.data.address} | Попытка {num}')
                first_swap = False
                balance_usdc = await self.eth_client.wallet.balance(
                    token=Tokens.STGUSDC.address
                )
                balance_honey = await self.eth_client.wallet.balance(
                    token=Tokens.HONEY.address
                )
                balance = await self.eth_client.wallet.balance()

                if not balance.Wei:
                    logger.warning(f'{self.data.address} | нет BERA')
                    break

                if not balance_usdc.Wei:
                    status = await self.bex.swap_bera_to_token("STGUSDC")
                    if 'was successfully swapped' in status:
                        logger.success(status)
                    else:
                        logger.warning(status)
                        continue

                    balance_usdc = await self.eth_client.wallet.balance(
                        token=Tokens.STGUSDC.address
                    )
                    first_swap = True

                if not balance_honey.Ether and balance_usdc.Wei:
                    if first_swap:
                        sleep_time = random.randint(FROM, TO)
                        logger.info(f'{self.data.address} | сплю {sleep_time} cекунд между ончейн тасками')
                        await asyncio.sleep(sleep_time)

                    status = await self.honey.mint_honey(value)
                    if 'was successfully minted' in status:
                        logger.success(status)
                    else:
                        logger.warning(status)
                        continue

                    balance_honey = await self.eth_client.wallet.balance(
                        token=Tokens.HONEY.address
                    )

                if balance_usdc.Wei and balance_honey.Ether:
                    self.data.finished_onchain = True
                    await self.write_to_db()
                    msg = (f"{self.data.address} | успешно закончил ончейн действия. Баланс "
                           f"STGUSDC: {balance_usdc.Ether} | HONEY: {balance_honey.Ether}")
                    logger.success(msg)
                    break

            except Exception as error:
                logger.error(f'{self.data.address} | неизвестная ошибка: {error}')
                print(traceback.print_exc())
                continue

    async def write_to_db(self):
        async with AsyncSession(db.engine) as session:
            await session.merge(self.data)
            await session.commit()
