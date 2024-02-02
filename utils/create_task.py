import asyncio
import random

from data.config import logger, WALLET
from db_api.models import Wallet
from db_api.database import get_accounts
from tasks.main import start_limited_task


async def get_tokens_from_faucet(semaphore):
    try:
        accounts: list[Wallet] = await get_accounts(faucet=True)
    
        if len(accounts) != 0:
            random.shuffle(accounts)
            logger.info(f'Всего задач: {len(accounts)}')
            tasks = []
            for account_data in accounts:
                task = asyncio.create_task(start_limited_task(semaphore, accounts, account_data))
                tasks.append(task)

            await asyncio.wait(tasks)
        else:
            msg = (f'Не удалось начать действие, возможная причина: нет подходящих аккаунтов для действия |'
                   f' не прошло 8 часов с прошлого клейма | вы не добавили аккаунты в базу данных.')
            logger.warning(msg)
    except Exception as e:
        pass


async def start_follow_and_retweet(semaphore):
    accounts: list[Wallet] = await get_accounts(twitter=True)

    if len(accounts) != 0:
        random.shuffle(accounts)
        logger.info(f'Всего задач: {len(accounts)}')
        tasks = []
        for account_data in accounts:
            task = asyncio.create_task(start_limited_task(semaphore, accounts, account_data, option=3))
            tasks.append(task)

        await asyncio.wait(tasks)
    else:
        msg = (f'Не удалось начать действие, возможная причина: нет подходящих аккаунтов для действия |'
               f' все аккаунты уже подписались и репостнули | вы не добавили аккаунты в базу данных.')
        logger.warning(msg)


async def check_token_balance(semaphore):
    try:
        accounts: list[Wallet] = await get_accounts(check_balance=True)
        if len(accounts) != 0:
            random.shuffle(accounts)
            logger.info(f'Всего задач: {len(accounts)}')
            tasks = []
            for account_data in accounts:
                task = asyncio.create_task(start_limited_task(semaphore, accounts, account_data, option=4))
                tasks.append(task)

            await asyncio.wait(tasks)

            msg = (f'Аккаунтов с балансом: {WALLET[0]} | '
                   f'Аккаунтов с нулевым балансом {WALLET[1]} | Всего BERA: {WALLET[2] / 10 ** 18}')
            logger.info(msg)
        else:
            msg = (f'Не удалось начать действие, возможная причина: нет подходящих аккаунтов для действия |'
                   f' все аккаунты последнее время клейма равно нулю | вы не добавили аккаунты в базу данных.')
            logger.warning(msg)
    except Exception as e:
        pass


async def start_daily_galxe_mint(semaphore):
    try:
        accounts: list[Wallet] = await get_accounts(daily_mint=True)
        random.shuffle(accounts)
        if len(accounts) != 0:
            logger.info(f'Всего задач: {len(accounts)}')
            tasks = []
            for account_data in accounts:
                task = asyncio.create_task(start_limited_task(semaphore, accounts, account_data, option=5))
                tasks.append(task)

            await asyncio.wait(tasks)

        else:
            msg = (f'Не удалось начать действие, возможная причина: нет подходящих аккаунтов для действия |'
                   f' все аккаунты закончили daily mint | вы не добавили аккаунты в базу данных.')
            logger.warning(msg)
    except Exception as e:
        pass


async def start_swaps(semaphore):
    try:
        accounts: list[Wallet] = await get_accounts(onchain=True)
        if len(accounts) != 0:
            random.shuffle(accounts)
            logger.info(f'Всего задач: {len(accounts)}')
            tasks = []
            for account_data in accounts:
                task = asyncio.create_task(start_limited_task(semaphore, accounts, account_data, option=6))
                tasks.append(task)

            await asyncio.wait(tasks)

        else:
            msg = (f'Не удалось начать действие, возможная причина: нет подходящих аккаунтов для действия |'
                f' все аккаунты закончили swap & mint | вы не добавили аккаунты в базу данных.')
            logger.warning(msg)
    except Exception as e:
        pass


async def start_claim_galxe_activity_nft(semaphore, option=7):
    try:
        i = 0
        while True:
            i += 1
            accounts: list[Wallet] = await get_accounts(galxy_second_nft=True)
            if len(accounts) != 0:
                all_tasks_len = len(accounts)
                msg = (f'Текущее кол-во подходящих задач: {all_tasks_len}. '
                       f'Мы будем брать их подходами по 25 пока они не кочатся...')
                logger.info(msg)
                accounts = accounts[:25]
                random.shuffle(accounts)
                logger.info(f'Задач в этом подходе: {len(accounts)}. Круг {i}. ')
                tasks = []
                for account_data in accounts:
                    task = asyncio.create_task(start_limited_task(semaphore, accounts, account_data, option))
                    tasks.append(task)

                await asyncio.wait(tasks)
                msg = (f'Сон 65 секунд перед новым подходом. Выполнено кругов: {i}. '
                       f'Осталось подходящих задач: {all_tasks_len}')
                logger.info(msg)
                await asyncio.sleep(65)

            else:
                msg = (f'Не удалось начать действие, возможная причина: нет подходящих аккаунтов для действия |'
                    f' все аккаунты закончили swap & mint | вы не добавили аккаунты в базу данных.')
                logger.warning(msg)
                await asyncio.sleep(400)
    except Exception as e:
        pass
