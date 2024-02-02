import traceback

import asyncio
from tasks.galxe_requests import GalxeRequests
from tasks.faucet import Faucet
from tasks.twitter import TwitterTasks
from tasks.start_onchain import OnChain
from tasks.check_balance import BalanceChecker
from data.config import logger, completed_tasks, tasks_lock


async def start_task(account_data, option):
    try:
        if option == 2:
            current_task = Faucet(account_data)
            await current_task.start_claim_tokens_from_faucet()
            await current_task.async_session.close()
        elif option == 3:
            current_task = TwitterTasks(account_data)
            await current_task.start_like_and_retweet()
        elif option == 4:
            current_task = BalanceChecker(account_data)
            await current_task.start_check_balance()
        elif option == 5:
            current_task = GalxeRequests(account_data)
            await current_task.start_claim_bera_points()
            await current_task.async_session.close()
        elif option == 6:
            current_task = OnChain(account_data)
            await current_task.start_onchain()
            await current_task.async_session.close()
        elif option == 7:
            current_task = GalxeRequests(account_data)
            await current_task.start_claim_bera_points(second_nft=True)
            await current_task.async_session.close()
        elif option == 8:
            current_task = GalxeRequests(account_data)
            await current_task.start_claim_bera_points(second_nft=True, fifty_five_points=True)
            await current_task.async_session.close()
    except TypeError:
        pass

    except Exception as error:
        logger.error(f'{account_data.address} | Неизвестная ошибка: {error}')
        print(traceback.print_exc())

    except asyncio.CancelledError:
        pass


async def start_limited_task(semaphore, accounts, account_data, option=2):
    try:
        async with semaphore:
            await start_task(account_data, option)

            async with tasks_lock:
                completed_tasks[0] += 1
                remaining_tasks = len(accounts) - completed_tasks[0]

            logger.info(f'Всего задач: {len(accounts)}. Осталось задач: {remaining_tasks}')
    except asyncio.CancelledError:
        pass
