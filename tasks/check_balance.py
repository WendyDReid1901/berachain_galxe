import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from db_api.database import Wallet, db
from eth.eth_client import EthClient
from data.models import Networks
from settings.settings import NUMBER_OF_ATTEMPTS
from data.config import logger, WALLET, tasks_lock
from libs.py_eth_async.client import Client


class BalanceChecker:

    def __init__(self, account_data: Wallet) -> None:

        self.data = account_data
        self.eth_client = EthClient(
            private_key=self.data.private_key,
            network=Networks.Berachain,
            proxy=self.data.proxy,
            user_agent=self.data.user_agent
        )

    async def start_check_balance(self):
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            try:
                logger.info(f'{self.data.address} | Попытка {num}')
                current_balance = await self.eth_client.w3.eth.get_balance(self.eth_client.account.address)
                if current_balance == 0:
                    logger.warning(f'{self.data.address} | текущий баланс равен нулю!')
                    self.data.next_available_claim = 0
                    await self.write_to_db()
                    async with tasks_lock:
                        WALLET[1] += 1

                    return
                
                elif current_balance < 1000000000000000000:
                    msg = (
                        f'{self.data.address} | текущий баланс меньше 1 BERA!'
                        f'Текущий баланс: {current_balance / 10 ** 18} BERA.'
                           )
                    logger.warning(msg)
                    self.data.next_available_claim = 0
                    await self.write_to_db()
                    async with tasks_lock:
                        WALLET[0] += 1
                        WALLET[2] += current_balance
                    return
                
                msg = (f'{self.data.address} | успешно получил баланс. '
                       f'Текущий баланс: {current_balance / 10 ** 18} BERA.')
                logger.success(msg)
                async with tasks_lock:
                    WALLET[0] += 1
                    WALLET[2] += current_balance
                return
            except Exception as err:
                logger.error(f'{self.data.address} | Неизвестная ошибка: {err}')
                print(traceback.print_exc())

    async def write_to_db(self, status="OK"):
        async with AsyncSession(db.engine) as session:
            self.data.twitter_account_status = status
            await session.merge(self.data)
            await session.commit()
