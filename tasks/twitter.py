import traceback

import aiofiles
from better_automation.twitter import TwitterClient, TwitterAccount
from better_automation.twitter.errors import Forbidden, Unauthorized, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db_api.models import Wallet
from data.config import logger, PROBLEMS, tasks_lock
from db_api.database import db
from settings.settings import NUMBER_OF_ATTEMPTS


class TwitterTasks:

    def __init__(self, account_data: Wallet) -> None:

        self.data = account_data
        self.twitter_client: TwitterClient | None = None
        self.twitter_account: TwitterAccount = TwitterAccount(self.data.token)
        self.retweet_done = False
        self.follow_done = False

    async def get_name(self):
        """ Возвращает никнейм пользователя, не username """

        await self.twitter_client.request_username()
        await self.twitter_client._request_user_data(self.twitter_account.username)

        return True

    async def raise_error(self, status):
        await self.write_to_db(status=status)
        await self.write_status(status=status)

    async def write_status(self, status, path=PROBLEMS):

        """ Записывает текщий статус проблемного токена в соответсвующий файл """

        async with tasks_lock:
            async with aiofiles.open(file=path, mode='a', encoding='utf-8-sig') as f:
                await f.write(f'{self.data.token} | {self.data.proxy} | {self.data.private_key} | {status}\n')

    async def write_to_db(self, status="OK"):
        async with AsyncSession(db.engine) as session:
            self.data.twitter_account_status = status
            await session.merge(self.data)
            await session.commit()

    async def retweet(self, tweet_id: int):

        """ делаем ретвит """

        retweet = await self.twitter_client.repost(tweet_id=tweet_id)
        if retweet:
            logger.info(f'{self.data.address} | успешно репостнул {tweet_id}')
            return True
        return False

    async def process_retweet(self, tweet_id: int):
        try:
            status = await self.retweet(tweet_id)
            if status:
                logger.info(f'{self.data.address} | успешно ретвитнул {tweet_id}.')
                self.retweet_done = True
                return True
            else:
                logger.warning(f'{self.data.address} | не смог ретвитнуть {tweet_id}.')
                return False

        except HTTPException as err:
            if 'already retweeted' in str(err):
                logger.warning(f'{self.data.address} | уже ретвитнул {tweet_id}.')
                self.retweet_done = True
                return True
            else:
                logger.warning(f'{self.data.address} | неизвестная ошибка: {err}.')
                return False

    async def follow(self, username: str):
        """ Подписываемся на пользователя """
        user_info = await self.twitter_client.request_user_data(username)
        status = await self.twitter_client.follow(user_id=user_info.id)
        if status:
            logger.info(f'{self.data.address} | Успешно подписался на {username}')
            self.follow_done = True
            return True
        return False

    async def make_galxe_tweet(self, user_id):
        tweet = f"Verifying my Twitter account for my #GalxeID gid:{user_id} @Galxe \n\n galxe.com/id "
        post_id = await self.twitter_client.tweet(text=tweet)
        if post_id:
            return True, f'https://twitter.com/{self.twitter_account.username}/status/{post_id}'
        return False, 'tweet not created'

    async def start_post_galxe_tweet(self, user_id):
        try:
            async with TwitterClient(
                    account=self.twitter_account,
                    proxy=self.data.proxy,
                    verify=False
            ) as twitter:

                self.twitter_client = twitter

                try:
                    await self.get_name()
                except Unauthorized:
                    msg = f'{self.data.address} | не удалось авторизироваться по токену! Проверьте токен.'
                    logger.error(msg)
                    self.data.twitter_account_status = 'BAD_TOKEN'
                    await self.raise_error('BAD_TOKEN')
                    return False, 'tweet not created'

                except Forbidden:
                    if self.twitter_account.status != 'GOOD':
                        msg = (f'{self.data.address} | Возникла проблема с аккаунтом!'
                               f' Текущий статус аккаунта = {self.twitter_account.status}')
                        logger.error(msg)

                        if self.twitter_account.status == 'SUSPENDED':
                            msg = f'Действие учетной записи приостановлено (бан)! Токен - {self.data.address}'
                            logger.warning(msg)
                            self.data.twitter_account_status = 'SUSPENDED'
                            await self.raise_error('SUSPENDED')
                            return False, 'tweet not created'

                        elif self.twitter_account.status == "LOCKED":
                            msg = (f'Учетная запись заморожена (лок)! Требуется прохождение капчи. '
                                   f'Токен - {self.data.address}')
                            logger.warning(msg)
                            self.data.twitter_account_status = 'LOCKED'
                            await self.raise_error('LOCKED')
                            return False, 'tweet not created'

                status, tweet_url = await self.make_galxe_tweet(user_id)
                if status:
                    return True, tweet_url
                return False, 'tweet not created'

        except Exception as error:
            logger.error(f'{self.data.address} | неизвестная ошибка: {error}')
            print(traceback.print_exc())
            return False, 'tweet not created'

    async def start_like_and_retweet(self):
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            logger.info(f'{self.data.address} | Попытка {num}')
            try:
                async with TwitterClient(
                        account=self.twitter_account,
                        proxy=self.data.proxy,
                        verify=False
                ) as twitter:

                        self.twitter_client = twitter

                        try:
                            await self.get_name()
                        except Unauthorized:
                            msg = f'{self.data.address} | не удалось авторизироваться по токену! Проверьте токен.'
                            logger.error(msg)
                            self.data.twitter_account_status = 'BAD_TOKEN'
                            await self.raise_error('BAD_TOKEN')
                            return

                        except Forbidden:
                            if self.twitter_account.status != 'GOOD':
                                msg = (f'{self.data.address} | Возникла проблема с аккаунтом!'
                                       f' Текущий статус аккаунта = {self.twitter_account.status}')
                                logger.error(msg)

                                if self.twitter_account.status == 'SUSPENDED':
                                    msg = f'Действие учетной записи приостановлено (бан)! Токен - {self.data.address}'
                                    logger.warning(msg)
                                    self.data.twitter_account_status = 'SUSPENDED'
                                    await self.raise_error('SUSPENDED')
                                    return

                                elif self.twitter_account.status == "LOCKED":
                                    msg = (f'Учетная запись заморожена (лок)! Требуется прохождение капчи. '
                                           f'Токен - {self.data.address}')
                                    logger.warning(msg)
                                    self.data.twitter_account_status = 'LOCKED'
                                    await self.raise_error('LOCKED')
                                    return

                        # follow
                        status = await self.follow("berachain")
                        print(status)
                        if not status:
                            continue

                        # retweet
                        status = await self.process_retweet(int("1745446022380408996"))
                        print(status)
                        if not status:
                            continue
                        
                        if self.follow_done and self.retweet_done:
                            self.data.follow_and_retweet = True
                            await self.write_to_db()
                            logger.success(f'{self.data.address} | успешно закончил действия с твиттером.')
                            return

            except Exception as error:
                logger.error(f'{self.data.address} | неизвестная ошибка: {error}')
                print(traceback.print_exc())
                continue
