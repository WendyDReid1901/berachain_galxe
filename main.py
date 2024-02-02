import itertools

import asyncio

from utils.create_files import create_files
from utils.user_menu import get_action
from utils.import_info import get_accounts_info
from utils.adjust_policy import set_windows_event_loop_policy
from data.config import TWITTER_TOKENS, PROXYS, PRIVATE_KEYS, EMAIL_DATA, logger
from settings.settings import ASYNC_SEMAPHORE
from db_api.database import initialize_db
from db_api.start_import import ImportToDB
from utils.create_task import (
    get_tokens_from_faucet,
    start_follow_and_retweet,
    check_token_balance,
    start_daily_galxe_mint,
    start_swaps,
    start_claim_galxe_activity_nft
)


def main():
    twitter_tokens: list[str] = get_accounts_info(TWITTER_TOKENS)
    proxies: list[str] = get_accounts_info(PROXYS)
    private_keys: list[str] = get_accounts_info(PRIVATE_KEYS)
    email_data: list[str] = get_accounts_info(EMAIL_DATA)

    cycled_proxies_list = itertools.cycle(proxies) if proxies else None

    logger.info(f'Загружено в twitter_tokens.txt {len(twitter_tokens)} аккаунтов \n'
                f'\t\t\t\t\t\t\tЗагружено в proxys.txt {len(proxies)} прокси \n'
                f'\t\t\t\t\t\t\tЗагружено в private_keys.txt {len(private_keys)} приватных ключей \n')

    formatted_data: list = [{
            'twitter_token': twitter_tokens.pop(0) if twitter_tokens else None,
            'proxy': next(cycled_proxies_list) if cycled_proxies_list else None,
            'private_key': private_key,
            'email_data': email_data.pop(0) if email_data else None
        } for private_key in private_keys
    ]

    user_choice = get_action()

    semaphore = asyncio.Semaphore(ASYNC_SEMAPHORE)

    if user_choice == '   1) Импорт в базу данных':

        asyncio.run(ImportToDB.add_account_to_db(accounts_data=formatted_data))

    elif user_choice == '   2) Получить токены с крана':

        asyncio.run(get_tokens_from_faucet(semaphore))

    elif user_choice == '   3) Репостнуть и подписаться':

        asyncio.run(start_follow_and_retweet(semaphore))

    elif user_choice == '   4) Проверить баланс на кошельках':

        asyncio.run(check_token_balance(semaphore))

    elif user_choice == '   5) daily mint на galxe':

        asyncio.run(start_daily_galxe_mint(semaphore))

    elif user_choice == '   6) Базовые действия galxe (ончейн)':

        asyncio.run(start_swaps(semaphore))

    elif user_choice == '   7) Claim galxe 70 points':

        asyncio.run(start_claim_galxe_activity_nft(semaphore))

    elif user_choice == '   8) Claim galxe 50 points (без твиттера)':

        asyncio.run(start_claim_galxe_activity_nft(semaphore, option=8))

    else:
        logger.error('ВЫБРАНО НЕВЕРНОЕ ДЕЙСТВИЕ')


if __name__ == "__main__":
    try:
        asyncio.run(initialize_db())
        create_files()
        set_windows_event_loop_policy()
        main()
    except TypeError:
        logger.info('Программа завершена')