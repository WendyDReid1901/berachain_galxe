import uuid
import time
import json
import random
import string
import traceback
from datetime import datetime, timedelta, timezone

import asyncio
from faker import Faker
from eth_account.messages import encode_defunct
from better_automation.base import BaseAsyncSession

from db_api.models import Wallet
from db_api.database import db
from eth.eth_client import EthClient
from sqlalchemy.ext.asyncio import AsyncSession
from data.config import logger
from settings.settings import NUMBER_OF_ATTEMPTS, W, ADD_TWITTER
from tasks.capmonster import Capmonster
from utils.email_imap import EmailClient
from tasks.twitter import TwitterTasks


class GalxeRequests:

    def __init__(self, data: Wallet):
        self.data = data
        self.async_session = BaseAsyncSession(proxy=data.proxy, verify=False, user_agent=self.data.user_agent)
        self.version = self.data.user_agent.split('Chrome/')[1].split('.')[0]
        self.eth_client = EthClient(
            private_key=self.data.private_key, proxy=self.data.proxy, user_agent=self.data.user_agent)
        self.auth_token = None
        self.capmonster = Capmonster(data=data, async_session=self.async_session)
        if self.data.token:
            self.twitter = TwitterTasks(account_data=data)

    async def start_claim_bera_points(self, second_nft=False, fifty_five_points=False):
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            try:
                logger.info(f'{self.data.address} | Попытка {num}')
                login_status = await self.start_login()
                if login_status:
                    logger.info(f'{self.data.address} | успешно авторизировался')
                    registration_status = await self.check_if_address_register()
                    if registration_status:
                        if not self.data.register:
                            self.data.register = True
                            await self.write_to_db()
                    else:
                        status, msg = await self.start_of_registration()
                        if status:
                            self.data.register = True
                            await self.write_to_db()
                            msg = f'{self.data.address} | успешно зарегистрировался на galxe. Account id: {msg}'
                            logger.success(msg)
                        else:
                            continue

                    status, need_add_email, need_add_twitter = await self.check_galxe_account_info()

                    if status:
                        msg = (f'{self.data.address} | успешно получил информацию об аккаунте | '
                               f'need_add_email: {str(need_add_email).lower()} |'
                               f' need_add_twitter: {str(need_add_twitter).lower()}')
                        logger.info(msg)

                        if need_add_email:
                            if self.data.email_data:
                                status = await self.add_email_to_galxe()
                                if status:
                                    logger.success(f'{self.data.address} | успешно прикрепил почту к galxe')
                                else:
                                    continue
                            else:
                                logger.error(f'{self.data.address} | need add email data!')
                                break

                        if need_add_twitter and ADD_TWITTER:
                            if self.data.token:
                                status = await self.add_twitter_to_galxe()
                                if status:
                                    logger.success(f'{self.data.address} | успешно прикрепил твиттер к galxe')
                                else:
                                    continue
                            else:
                                logger.error(f'{self.data.address} | need add twitter token!')
                                break

                        if second_nft:
                            status = await self.start_claim_second_nft(fifty_five_points)
                            if status:
                                break
                            else:
                                continue

                        else:
                            status = await self.start_claim_five_points()
                            if status:
                                break
                            else:
                                continue
                    else:
                        continue
                else:
                    continue

            except Exception as error:
                logger.error(f'{self.data.address} | неизвестная ошибка: {error}')
                print(traceback.print_exc())
                continue

    @staticmethod
    def get_random_nonce(length=17):
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

    @staticmethod
    def get_activity_time_login():
        issued_at = datetime.now(timezone.utc)
        expiration_time = issued_at + timedelta(days=7)
        issued_at_str = issued_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        expiration_time_str = expiration_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        return issued_at_str, expiration_time_str

    @staticmethod
    def get_random_request_id():
        return str(uuid.uuid4())

    @staticmethod
    def get_random_username(min_lenght=6) -> str:
        return Faker().user_name().ljust(min_lenght, str(random.randint(1, 9)))

    def get_main_headers(self):
        return {
            'authority': 'graphigo.prd.galaxy.eco',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': self.auth_token,
            'content-type': 'application/json',
            'origin': 'https://galxe.com',
            'request-id': self.get_random_request_id(),
            'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{self.version}", "Google Chrome";v="{self.version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.data.platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.data.user_agent,
        }

    async def start_login(self):
        issued_at_str, expiration_time_str = self.get_activity_time_login()

        message = (
            'galxe.com wants you to sign in with your Ethereum account:\n'
            f'{self.eth_client.account.address}\n\n'
            'Sign in with Ethereum to the app.\n\n'
            'URI: https://galxe.com\n'
            'Version: 1\n'
            'Chain ID: 1\n'
            f'Nonce: {self.get_random_nonce()}\n'
            f'Issued At: {issued_at_str}\n'
            f'Expiration Time: {expiration_time_str}'
        )

        message_encoded = encode_defunct(text=message)
        signed_message = self.eth_client.account.sign_message(message_encoded)

        headers = {
            'authority': 'graphigo.prd.galaxy.eco',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://galxe.com',
            'request-id': self.get_random_request_id(),
            'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{self.version}", "Google Chrome";v="{self.version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.data.platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.data.user_agent,
        }

        json_data = {
            'operationName': 'SignIn',
            'variables': {
                'input': {
                    'address': self.data.address.lower(),
                    'message': message,
                    'signature': signed_message.signature.hex(),
                    'addressType': 'EVM',
                },
            },
            'query': 'mutation SignIn($input: Auth) {\n  signin(input: $input)\n}\n',
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            try:
                self.auth_token = answer['data']['signin']
                return True
            except (KeyError, TypeError):
                pass
        logger.warning(f'{self.data.address} | не смог авторизироваться на galxe. Ответ сервера: {response.text}')
        return False

    async def check_if_address_register(self):

        headers = {
            'authority': 'graphigo.prd.galaxy.eco',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/json',
            'origin': 'https://galxe.com',
            'request-id': self.get_random_request_id(),
            'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{self.version}", "Google Chrome";v="{self.version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.data.platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': self.data.user_agent,
        }

        json_data = {
            'operationName': 'GalxeIDExist',
            'variables': {
                'schema': f'EVM:{self.data.address.lower()}',
            },
            'query': 'query GalxeIDExist($schema: String!) {\n  galxeIdExist(schema: $schema)\n}\n',
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            try:
                return answer["data"]["galxeIdExist"]
            except (KeyError, TypeError):
                pass
        msg = (f'{self.data.address} | не удалось проверить зарегистрирован ли аккаунт. '
               f'Код ответа: {response.status_code}. Ответ: {response.text}')
        logger.warning(msg)
        return False

    async def check_if_username_exist(self, username):

        headers = self.get_main_headers()

        json_data = {
            'operationName': 'IsUsernameExisting',
            'variables': {
                'username': username,
            },
            'query': 'query IsUsernameExisting($username: String!) {\n  usernameExist(username: $username)\n}\n',
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            try:
                return answer['data']['usernameExist']
            except KeyError:
                pass
        msg = f'{self.data.address} | не удалось проверить свободен ли юзернейм. Ответ сервера: {response.text}'
        logger.warning(msg)
        return True

    async def start_of_registration(self):

        username = self.get_random_username()
        i = 0
        while i < NUMBER_OF_ATTEMPTS:
            username_exist = await self.check_if_username_exist(username)
            if not username_exist:
                break
            username = self.get_random_username()
            i += 1
            if i == 10:
                return False, 'не удалось проверить cвободен ли username'

        headers = self.get_main_headers()

        json_data = {
            'operationName': 'CreateNewAccount',
            'variables': {
                'input': {
                    'schema': f'EVM:{self.data.address.lower()}',
                    'socialUsername': '',
                    'username': username,
                },
            },
            'query': 'mutation CreateNewAccount($input: CreateNewAccount!) {\n  createNewAccount(input: $input)\n}\n',
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            try:
                if answer['data']['createNewAccount']:
                    return True, answer['data']['createNewAccount']
            except (KeyError, TypeError):
                pass
        logger.warning(f'{self.data.address} | не удалось зарегистрироваться. Ответ сервера: {response.text}')
        return False, 'не удалось зарегистироваться'

    async def check_galxe_account_info(self, check_user_id=False):

        headers = self.get_main_headers()

        query = (
            'query BasicUserInfo($address: String!) '
            '{\n  addressInfo(address: $address) {\n    id\n    username\n    avatar\n    address\n    '
            'evmAddressSecondary {\n      address\n      __typename\n    }\n    hasEmail\n    solanaAddress\n'
            '    aptosAddress\n    seiAddress\n    injectiveAddress\n    flowAddress\n    starknetAddress\n    '
            'bitcoinAddress\n    hasEvmAddress\n    hasSolanaAddress\n    hasAptosAddress\n    hasInjectiveAddress\n'
            '    hasFlowAddress\n    hasStarknetAddress\n    hasBitcoinAddress\n    hasTwitter\n    hasGithub\n    '
            'hasDiscord\n    hasTelegram\n    displayEmail\n    displayTwitter\n    displayGithub\n    displayDiscord\n'
            '    displayTelegram\n    displayNamePref\n    email\n    twitterUserID\n    twitterUserName\n    '
            'githubUserID\n    githubUserName\n    discordUserID\n    discordUserName\n    telegramUserID\n    '
            'telegramUserName\n    enableEmailSubs\n    subscriptions\n    isWhitelisted\n    isInvited\n    isAdmin\n'
            '    accessToken\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'BasicUserInfo',
            'variables': {
                'address': self.data.address.lower(),
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if check_user_id:
                user_id = answer.get('data', False).get('addressInfo', False).get('id', False)
                if user_id:
                    return user_id
            else:
                need_add_email = False
                need_add_twitter = False
                try:
                    if not answer['data']['addressInfo']['hasEmail']:
                        need_add_email = True

                    if not answer['data']['addressInfo']['hasTwitter']:
                        need_add_twitter = True

                    return True, need_add_email, need_add_twitter
                except (KeyError, TypeError):
                    pass
        logger.warning(f'{self.data.address} | не смог получить информацию об аккаунте. Ответ сервера: {response.text}')
        return False, False, False

    async def request_to_add_email(self, solution):
        
        headers = self.get_main_headers()

        query = (
            'mutation SendVerifyCode($input: SendVerificationEmailInput!) '
            '{\n  sendVerificationCode(input: $input) {\n    code\n    message\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'SendVerifyCode',
            'variables': {
                'input': {
                    'address': self.data.address.lower(),
                    'email': self.data.email_data.split(':')[0],
                    'captcha': {
                        'lotNumber': solution['lot_number'],
                        'captchaOutput': solution['seccode']['captcha_output'],
                        'passToken': solution['seccode']['pass_token'],
                        'genTime': solution['seccode']['gen_time'],
                    },
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )
        if response.status_code == 200:
            answer = response.json()
            try:
                if not answer['data']['sendVerificationCode']:
                    return True
            except (KeyError, TypeError):
                pass
        msg = f'{self.data.address} | не удалось выслать запрос на прикрепление почты. Ответ сервера: {response.text}'
        logger.warning(msg)
        return False

    async def send_email_verif_code(self, verif_code):

        headers = self.get_main_headers()

        query = ('mutation UpdateEmail($input: UpdateEmailInput!) '
                 '{\n  updateEmail(input: $input) {\n    code\n    message\n    __typename\n  }\n}\n')

        json_data = {
            'operationName': 'UpdateEmail',
            'variables': {
                'input': {
                    'address': self.data.address.lower(),
                    'email': self.data.email_data.split(':')[0],
                    'verificationCode': verif_code,
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if 'errors' in answer:
                return False
            elif not answer['data']['updateEmail']:
                return True
        return False

    async def add_email_to_galxe(self):
        # solution = await self.capmonster.wait_for_geetest_gcaptcha()
        solution = await self.prepare_and_solution_captcha()
        if solution:
            status = await self.request_to_add_email(solution)
            if status:
                logger.info(f'{self.data.address} | успешно отправил запрос на прикрепление почты.')
                await asyncio.sleep(10)
                verif_code = await EmailClient(
                    self.data.email_data.split(':')[0], self.data.email_data.split(':')[1]).get_code()
                if verif_code:
                    logger.info(f'{self.data.address} | email verify code успешно получен.')
                    status = await self.send_email_verif_code(verif_code)
                    if status:
                        logger.info(f'{self.data.address} | email успешно прикреплен')
                        return True
                    else:
                        logger.warning(f'{self.data.address} | не смог прикрепить email')
                        return False
                else:
                    logger.warning(f'{self.data.address} | не смог получить код верификации почты')
                    return False

        return False

    async def prepare_task_before_claim(self, solution):
        headers = self.get_main_headers()

        query = (
            'mutation AddTypedCredentialItems($input: MutateTypedCredItemInput!) '
            '{\n  typedCredentialItems(input: $input) {\n    id\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'AddTypedCredentialItems',
            'variables': {
                'input': {
                    'credId': '367886459336302592',
                    'campaignId': 'GCTN3ttM4T',
                    'operation': 'APPEND',
                    'items': [
                        self.data.address.lower(),
                    ],
                    'captcha': {
                        'lotNumber': solution['lot_number'],
                        'captchaOutput': solution['seccode']['captcha_output'],
                        'passToken': solution['seccode']['pass_token'],
                        'genTime': solution['seccode']['gen_time'],
                    },
                    # 'captcha': {
                    #     'lotNumber': solution['lot_number'],
                    #     'captchaOutput': solution['captcha_output'],
                    #     'passToken': solution['pass_token'],
                    #     'genTime': solution['gen_time'],
                    # },
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            try:
                typed_items = answer.get('data', {}).get('typedCredentialItems', {})
                if 'id' in typed_items and '__typename' in typed_items:
                    return True
            except (KeyError, TypeError):
                pass
        msg = (f'{self.data.address} | не удалось подготовить задание перед клеймом 5 поинтов. '
               f'Ответ сервера: {response.text}')
        logger.info(msg)
        return False

    async def try_claim_five_points(self, solution):
        
        headers = self.get_main_headers()

        query = (
            'mutation PrepareParticipate($input: PrepareParticipateInput!) '
            '{\n  prepareParticipate(input: $input) {\n    allow\n    disallowReason\n    signature\n    nonce\n    '
            'mintFuncInfo {\n      funcName\n      nftCoreAddress\n      verifyIDs\n      powahs\n      cap\n      '
            '__typename\n    }\n    extLinkResp {\n      success\n      data\n      error\n      __typename\n    }\n'
            '    metaTxResp {\n      metaSig2\n      autoTaskUrl\n      metaSpaceAddr\n      forwarderAddr\n      '
            'metaTxHash\n      reqQueueing\n      __typename\n    }\n    solanaTxResp {\n      mint\n      '
            'updateAuthority\n      explorerUrl\n      signedTx\n      verifyID\n      __typename\n    }\n    '
            'aptosTxResp {\n      signatureExpiredAt\n      tokenName\n      __typename\n    }\n    '
            'tokenRewardCampaignTxResp {\n      signatureExpiredAt\n      verifyID\n      __typename\n    }\n    '
            'loyaltyPointsTxResp {\n      TotalClaimedPoints\n      __typename\n    }\n    flowTxResp {\n      Name\n'
            '      Description\n      Thumbnail\n      __typename\n    }\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'PrepareParticipate',
            'variables': {
                'input': {
                    'signature': '',
                    'campaignID': 'GCTN3ttM4T',
                    'address': self.data.address.lower(),
                    'mintCount': 1,
                    'chain': 'ETHEREUM',
                    'captcha': {
                        'lotNumber': solution['lot_number'],
                        'captchaOutput': solution['seccode']['captcha_output'],
                        'passToken': solution['seccode']['pass_token'],
                        'genTime': solution['seccode']['gen_time'],
                    },
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            try:
                if answer['data']['prepareParticipate']['allow']:
                    return True
            except (KeyError, TypeError):
                pass
        logger.warning(f'{self.data.address} | не получилось заклеймить 5 поинтов. Пробую еще раз...')
        return False

    async def start_claim_five_points(self):
        first_solution = await self.prepare_and_solution_captcha()
        # first_solution = await self.capmonster.wait_for_geetest_gcaptcha()
        if first_solution:
            status = await self.prepare_task_before_claim(first_solution)
            if status:
                logger.info(f'{self.data.address} | успешно выслал подготовительный запрос для клейма 5 поинтов')
                await asyncio.sleep(20)
                second_solution = await self.prepare_and_solution_captcha()
                # second_solution = await self.capmonster.wait_for_geetest_gcaptcha()
                if second_solution:
                    status = await self.try_claim_five_points(second_solution)
                    if status:
                        self.data.galxe_daily_claim = datetime.now(timezone.utc)
                        await self.write_to_db()
                        logger.success(f'{self.data.address} | успешно склеймил daily 5 galxe points.')
                        return True
        return False
    
    @staticmethod
    def generate_random_string(length=1024):
        letters_and_digits = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(letters_and_digits) for i in range(length))
        return random_string.lower()

    async def prepare_and_solution_captcha(self):
        try:
            call = int(time.time() * 1e3)
            params = {
                'captcha_id': '244bcb8b9846215df5af4c624a750db4',
                'challenge': self.get_random_request_id(),
                'client_type': 'web',
                'lang': 'en',
                'callback': f'geetest_{call}',
            }

            response = await self.async_session.get('https://gcaptcha4.geetest.com/load', params=params)
            js_data = json.loads(response.text.strip(f'geetest_{call}(').strip(')'))['data']

            params = {
                'captcha_id': '244bcb8b9846215df5af4c624a750db4',
                'client_type': 'web',
                'lot_number': js_data['lot_number'],
                'payload': js_data['payload'],
                'process_token': js_data['process_token'],
                'payload_protocol': '1',
                'pt': '1',
                'w': W,
                'callback': f'geetest_{call}',
            }

            response = await self.async_session.get('https://gcaptcha4.geetest.com/verify', params=params)
            solution = json.loads(response.text.strip('geetest_{}('.format(call)).strip(')'))['data']
            if solution.get('result', False) == 'success':
                return solution
            return False
        except json.decoder.JSONDecodeError:
            print(response.status_code)
            print(response.text)
            print(traceback)
            return False

    async def galxe_twitter_check_account(self, tweet_url):

        headers = self.get_main_headers()

        query = (
            'mutation checkTwitterAccount($input: VerifyTwitterAccountInput!) '
            '{\n  checkTwitterAccount(input: $input) {\n    address\n    twitterUserID\n    twitterUserName\n'
            '    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'checkTwitterAccount',
            'variables': {
                'input': {
                    'address': self.data.address.lower(),
                    'tweetURL': tweet_url,
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if (
                answer.get('data', {}).get('checkTwitterAccount', {}).get('twitterUserID', {}) ==
                self.twitter.twitter_account.username
            ):
                return True
        msg = (f'{self.data.address} | не удалось выслать запрос на проверку твиттер аккаунта.'
               f' Ответ сервера: {response.text}')
        logger.warning(msg)
        return False

    async def galxe_twitter_verify_account(self, tweet_url):

        headers = self.get_main_headers()

        query = (
            'mutation VerifyTwitterAccount($input: VerifyTwitterAccountInput!) '
            '{\n  verifyTwitterAccount(input: $input) {\n    address\n    twitterUserID\n    twitterUserName\n'
            '    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'VerifyTwitterAccount',
            'variables': {
                'input': {
                    'address': self.data.address.lower(),
                    'tweetURL': tweet_url,
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if (
                answer.get('data', {}).get('verifyTwitterAccount', {}).get('twitterUserName', {}) ==
                self.twitter.twitter_account.username
            ):
                return True
        logger.warning(f'{self.data.address} | не удалось прикрепить твиттер аккаунт. Ответ сервера: {response.text}')
        return False

    async def add_twitter_to_galxe(self):
        user_id = await self.check_galxe_account_info(check_user_id=True)
        if user_id:
            status, tweet_url = await self.twitter.start_post_galxe_tweet(user_id=user_id)
            if status:
                status = await self.galxe_twitter_check_account(tweet_url)
                if status:
                    status = await self.galxe_twitter_verify_account(tweet_url)
                    if status:
                        return True
        return False

    @staticmethod
    def get_value_by_path(data, path):
        current_data = data
        for p in path:
            try:
                if isinstance(p, int):
                    current_data = current_data[p]
                else:
                    current_data = current_data[p]
            except (IndexError, KeyError, TypeError):
                return False
        return current_data

    async def get_second_nft_current_points(self):

        headers = self.get_main_headers()

        query = (
            'query SpaceCampaignsMetricQuery($id: Int, $alias: String, $address: String!, $campaignInput: '
            'ListCampaignInput!) {\n  space(id: $id, alias: $alias) {\n    id\n    campaigns(input: $campaignInput) '
            '{\n      list {\n        nftCore {\n          id\n          __typename\n        }\n        '
            '...SpaceCampaignBasic\n        info\n        referralCode(address: $address)\n        metrics\n        '
            'childrenCampaigns {\n          nftCore {\n            id\n            __typename\n          }\n          '
            '...SpaceCampaignBasic\n          info\n          metrics\n          gamification {\n            id\n'
            '            type\n            __typename\n          }\n          __typename\n        }\n        '
            'gamification {\n          id\n          type\n          __typename\n        }\n        __typename\n      '
            '}\n      pageInfo {\n        hasNextPage\n        endCursor\n        __typename\n      }\n      '
            'totalCount\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment SpaceBasic on Space {\n  '
            'id\n  name\n  thumbnail\n  alias\n  isVerified\n  info\n  links\n  status\n  followersCount\n  '
            'followersRank\n  backers\n  categories\n  token\n  discordGuildID\n  discordGuildInfo\n  '
            'banner\n  seoImage\n  __typename\n}\n\nfragment SpaceCampaignBasic on Campaign {\n  id\n  name\n  '
            'description\n  thumbnail\n  startTime\n  endTime\n  status\n  formula\n  cap\n  gasType\n  isPrivate\n  '
            'type\n  loyaltyPoints\n  tokenRewardContract {\n    id\n    address\n    chain\n    __typename\n  }\n  '
            'tokenReward {\n    userTokenAmount\n    tokenAddress\n    depositedTokenAmount\n    tokenRewardId\n    '
            'tokenDecimal\n    tokenLogo\n    tokenSymbol\n    __typename\n  }\n  numberID\n  chain\n  rewardName\n  '
            '...SpaceCampaignMedia\n  space {\n    ...SpaceBasic\n    __typename\n  }\n  credentialGroups(address: '
            '$address) {\n    ...CredentialGroupForAddress\n    __typename\n  }\n  rewardInfo {\n    discordRole {\n'
            '      guildId\n      guildName\n      roleId\n      roleName\n      inviteLink\n      __typename\n    }\n'
            '    premint {\n      startTime\n      endTime\n      chain\n      price\n      totalSupply\n      '
            'contractAddress\n      banner\n      __typename\n    }\n    __typename\n  }\n  participants {\n    '
            'participantsCount\n    bountyWinnersCount\n    __typename\n  }\n  recurringType\n  latestRecurringTime\n'
            '  ...WhitelistInfoFrag\n  creds {\n    ...CredForAddress\n    __typename\n  }\n  taskConfig(address: '
            '$address) {\n    participateCondition {\n      conditions {\n        ...ExpressionEntity\n        '
            '__typename\n      }\n      conditionalFormula\n      eligible\n      __typename\n    }\n    '
            'rewardConfigs {\n      conditions {\n        ...ExpressionEntity\n        __typename\n      }\n      '
            'conditionalFormula\n      eligible\n      rewards {\n        arithmeticFormula\n        rewardType\n   '
            '     rewardCount\n        rewardVal\n        __typename\n      }\n      __typename\n    }\n    '
            '__typename\n  }\n  __typename\n}\n\nfragment SpaceCampaignMedia on Campaign {\n  thumbnail\n  '
            'gamification {\n    id\n    type\n    __typename\n  }\n  __typename\n}\n\nfragment CredentialGroup'
            'ForAddress on CredentialGroup {\n  id\n  description\n  credentials {\n    ...CredForAddressWithout'
            'Metadata\n    __typename\n  }\n  conditionRelation\n  conditions {\n    expression\n    eligible\n    '
            '...CredentialGroupConditionForVerifyButton\n    __typename\n  }\n  rewards {\n    expression\n    '
            'eligible\n    rewardCount\n    rewardType\n    __typename\n  }\n  rewardAttrVals {\n    attrName\n    '
            'attrTitle\n    attrVal\n    __typename\n  }\n  claimedLoyaltyPoints\n  __typename\n}\n\nfragment CredFor'
            'AddressWithoutMetadata on Cred {\n  id\n  name\n  type\n  credType\n  credSource\n  referenceLink\n  des'
            'cription\n  lastUpdate\n  lastSync\n  syncStatus\n  credContractNFTHolder {\n    timestamp\n    __typena'
            'me\n  }\n  chain\n  eligible(address: $address)\n  subgraph {\n    endpoint\n    query\n    expression\n  '
            '  __typename\n  }\n  dimensionConfig\n  value {\n    gitcoinPassport {\n      score\n      lastScoreTimest'
            'amp\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment CredentialGroupConditionFor'
            'VerifyButton on CredentialGroupCondition {\n  expression\n  eligibleAddress\n  __typename\n}\n\nfragment '
            'WhitelistInfoFrag on Campaign {\n  id\n  whitelistInfo(address: $address) {\n    address\n    maxCount\n  '
            '  usedCount\n    claimedLoyaltyPoints\n    currentPeriodClaimedLoyaltyPoints\n    currentPeriodMaxLoyalty'
            'Points\n    __typename\n  }\n  __typename\n}\n\nfragment ExpressionEntity on ExprEntity {\n  cred {\n   '
            ' id\n    name\n    type\n    credType\n    credSource\n    referenceLink\n    description\n    lastUpdate'
            '\n    lastSync\n    chain\n    eligible(address: $address)\n    metadata {\n      visitLink {\n        lin'
            'k\n        __typename\n      }\n      twitter {\n        isAuthentic\n        __typename\n      }\n      _'
            '_typename\n    }\n    commonInfo {\n      participateEndTime\n      modificationInfo\n      __typename\n  '
            '  }\n    __typename\n  }\n  attrs {\n    attrName\n    operatorSymbol\n    targetValue\n    __typename\n  }'
            '\n  attrFormula\n  eligible\n  eligibleAddress\n  __typename\n}\n\nfragment CredForAddress on Cred {\n  ..'
            '.CredForAddressWithoutMetadata\n  metadata {\n    ...CredMetaData\n    __typename\n  }\n  dimensionConfig'
            '\n  value {\n    gitcoinPassport {\n      score\n      lastScoreTimestamp\n      __typename\n    }\n    __'
            'typename\n  }\n  commonInfo {\n    participateEndTime\n    modificationInfo\n    __typename\n  }\n  __typ'
            'ename\n}\n\nfragment CredMetaData on CredMetadata {\n  visitLink {\n    link\n    __typename\n  }\n  gitco'
            'inPassport {\n    score {\n      title\n      type\n      description\n      config\n      __typename\n   '
            ' }\n    lastScoreTimestamp {\n      title\n      type\n      description\n      config\n      __typename\n'
            '    }\n    __typename\n  }\n  campaignReferral {\n    count {\n      title\n      type\n      description'
            '\n      config\n      __typename\n    }\n    __typename\n  }\n  galxeScore {\n    dimensions {\n      id\n'
            '      type\n      title\n      description\n      config\n      values {\n        name\n        type\n   '
            '     value\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  twitter {\n    tw'
            'itterID\n    campaignID\n    isAuthentic\n    __typename\n  }\n  restApi {\n    url\n    method\n    heade'
            'rs {\n      key\n      value\n      __typename\n    }\n    postBody\n    expression\n    __typename\n  }\n'
            '  walletBalance {\n    contractAddress\n    snapshotTimestamp\n    chain\n    balance {\n      type\n     '
            ' title\n      description\n      config\n      __typename\n    }\n    LastSyncBlock\n    LastSyncTimestamp'
            '\n    __typename\n  }\n  lensProfileFollow {\n    handle\n    __typename\n  }\n  graphql {\n    url\n    '
            'query\n    expression\n    __typename\n  }\n  lensPostUpvote {\n    postId\n    __typename\n  }\n  lensPo'
            'stMirror {\n    postId\n    __typename\n  }\n  multiDimensionRest {\n    url\n    method\n    headers {\n'
            '      key\n      value\n      __typename\n    }\n    postBody\n    expression\n    dimensions {\n      id'
            '\n      type\n      title\n      description\n      config\n      __typename\n    }\n    __typename\n  }\n'
            '  nftHolder {\n    contractNftHolder {\n      Chain\n      __typename\n    }\n    __typename\n  }\n  multi'
            'DimensionGraphql {\n    url\n    query\n    expression\n    dimensions {\n      id\n      type\n      titl'
            'e\n      description\n      config\n      __typename\n    }\n    __typename\n  }\n  contractQuery {\n    u'
            'rl\n    chainName\n    abi\n    method\n    headers {\n      key\n      value\n      __typename\n    }\n'
            '    contractMethod\n    contractAddress\n    block\n    inputData\n    inputs {\n      name\n      type\n'
            '      value\n      __typename\n    }\n    dimensions {\n      id\n      type\n      config\n      descript'
            'ion\n      title\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n'
        )

        json_data = {
            'operationName': 'SpaceCampaignsMetricQuery',
            'variables': {
                'alias': 'Berachain',
                'address': self.data.address.lower(),
                'campaignInput': {
                    'first': 25,
                    'forAdmin': True,
                    'after': '-1',
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            return GalxeRequests.get_value_by_path(
                data=response.json(),
                path=[
                    'data', 'space', 'campaigns', 'list', 0,
                    'childrenCampaigns', 1, 'whitelistInfo',
                    'currentPeriodMaxLoyaltyPoints'
                ]
            )
        return False

    async def prepare_galxe_task(self, solution, task_id):

        headers = self.get_main_headers()

        query = (
            'mutation AddTypedCredentialItems($input: MutateTypedCredItemInput!) '
            '{\n  typedCredentialItems(input: $input) {\n    id\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'AddTypedCredentialItems',
            'variables': {
                'input': {
                    'credId': str(task_id),
                    'campaignId': 'GC433ttn6N',
                    'operation': 'APPEND',
                    'items': [
                        self.data.address.lower(),
                    ],
                    'captcha': {
                        'lotNumber': solution['lot_number'],
                        'captchaOutput': solution['seccode']['captcha_output'],
                        'passToken': solution['seccode']['pass_token'],
                        'genTime': solution['seccode']['gen_time'],
                    },
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            return True, answer.get('data', {}).get('typedCredentialItems', {}).get('id', False)
        return False, 'notId'

    async def confirm_galxe_task(self, task_id):

        headers = self.get_main_headers()

        query = (
            'mutation VerifyCredential($input: VerifyCredentialInput!) {\n  verifyCredential(input: $input)\n}\n'
        )

        json_data = {
            'operationName': 'VerifyCredential',
            'variables': {
                'input': {
                    'credId': task_id,
                    'address': self.data.address.lower(),
                    'campaignId': 'GC433ttn6N',
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            return answer.get('data', {}).get('verifyCredential', False)
        return False

    # Twitter task
    async def start_confirm_twitter_tasks(self):
        first_solution = await self.prepare_and_solution_captcha()
        if first_solution:
            status, task_id = await self.prepare_galxe_task(solution=first_solution, task_id='367853344551247872')
            if status:
                status = await self.confirm_galxe_task(task_id)
                second_solution = await self.prepare_and_solution_captcha()
                if status and second_solution:
                    status, task_id = await self.prepare_galxe_task(
                        solution=second_solution, task_id='368036627574595584')
                    if status:
                        status = await self.confirm_galxe_task(task_id)
                        if status:
                            return True
        return False

    # Visit the Proof of Liquidity main website page
    async def visit_proof_of_liquidity_task(self):
        captha_solution = await self.prepare_and_solution_captcha()
        if captha_solution:
            status, task_id = await self.prepare_galxe_task(solution=captha_solution, task_id='368778853896331264')
            if status:
                status = await self.confirm_galxe_task(task_id)
                if status:
                    return True
        return False

    async def prepare_galxe_quiz(self):

        headers = self.get_main_headers()

        query = (
            'query readQuiz($id: ID!) {\n  credential(id: $id) {\n    ...CredQuizFrag\n    __typename\n  '
            '}\n}\n\nfragment CredQuizFrag on Cred {\n  credQuiz {\n    quizzes {\n      title\n      type\n'
            '      items {\n        value\n        __typename\n      }\n      __typename\n    }\n    '
            '__typename\n  }\n  __typename\n}\n'
        )

        json_data = {
            'operationName': 'readQuiz',
            'variables': {
                'id': '367883082841890816',
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if answer.get('data', {}).get('credential', {}).get('credQuiz', {}).get('quizzes', {}):
                return True
        return False

    async def confirm_galxe_quiz(self, solution):

        headers = self.get_main_headers()

        query = (
            'mutation manuallyVerifyCredential($input: ManuallyVerifyCredentialInput!) {\n  '
            'manuallyVerifyCredential(input: $input) {\n    eligible\n    credQuiz {\n      output {\n        '
            'correct\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'manuallyVerifyCredential',
            'variables': {
                'input': {
                    'credId': '367883082841890816',
                    'address': self.data.address.lower(),
                    'captcha': {
                        'lotNumber': solution['lot_number'],
                        'captchaOutput': solution['seccode']['captcha_output'],
                        'passToken': solution['seccode']['pass_token'],
                        'genTime': solution['seccode']['gen_time'],
                    },
                    'credQuiz': {
                        'input': [
                            {
                                'value': '2',
                            },
                            {
                                'value': '3',
                            },
                            {
                                'value': '3',
                            },
                            {
                                'value': '3',
                            },
                            {
                                'value': '0',
                            },
                        ],
                    },
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if answer.get('data', {}).get('manuallyVerifyCredential', {}).get('eligible'):
                return True
            if not answer.get('data', {}).get('manuallyVerifyCredential', {}).get('__typename', False):
                return True
        return False

    async def confirm_two_in_one_galxe_tasks(self):
        first_solution = await self.prepare_and_solution_captcha()
        if first_solution:
            status, task_id = await self.prepare_galxe_task(solution=first_solution, task_id='367877685103992832')
            if status:
                status = await self.confirm_galxe_task(task_id)
                if status:
                    status = await self.prepare_galxe_quiz()
                    second_solution = await self.prepare_and_solution_captcha()
                    if status and second_solution:
                        status = await self.confirm_galxe_quiz(solution=second_solution)
                        if status:
                            return True
        return False

    async def claim_second_nft_quest(self, solution):

        headers = self.get_main_headers()

        query = (
            'mutation PrepareParticipate($input: PrepareParticipateInput!) {\n  prepareParticipate(input: $input) {\n'
            '    allow\n    disallowReason\n    signature\n    nonce\n    mintFuncInfo {\n      funcName\n      '
            'nftCoreAddress\n      verifyIDs\n      powahs\n      cap\n      __typename\n    }\n    extLinkResp {\n'
            '      success\n      data\n      error\n      __typename\n    }\n    metaTxResp {\n      metaSig2\n      '
            'autoTaskUrl\n      metaSpaceAddr\n      forwarderAddr\n      metaTxHash\n      reqQueueing\n      '
            '__typename\n    }\n    solanaTxResp {\n      mint\n      updateAuthority\n      explorerUrl\n      '
            'signedTx\n      verifyID\n      __typename\n    }\n    aptosTxResp {\n      signatureExpiredAt\n      '
            'tokenName\n      __typename\n    }\n    tokenRewardCampaignTxResp {\n      signatureExpiredAt\n      '
            'verifyID\n      __typename\n    }\n    loyaltyPointsTxResp {\n      TotalClaimedPoints\n      '
            '__typename\n    }\n    flowTxResp {\n      Name\n      Description\n      Thumbnail\n      __typename\n'
            '    }\n    __typename\n  }\n}\n'
        )

        json_data = {
            'operationName': 'PrepareParticipate',
            'variables': {
                'input': {
                    'signature': '',
                    'campaignID': 'GC433ttn6N',
                    'address': self.data.address.lower(),
                    'mintCount': 1,
                    'chain': 'ETHEREUM',
                    'captcha': {
                        'lotNumber': solution['lot_number'],
                        'captchaOutput': solution['seccode']['captcha_output'],
                        'passToken': solution['seccode']['pass_token'],
                        'genTime': solution['seccode']['gen_time'],
                    },
                },
            },
            'query': query,
        }

        response = await self.async_session.post(
            'https://graphigo.prd.galaxy.eco/query',
            headers=headers,
            json=json_data
        )

        if response.status_code == 200:
            answer = response.json()
            if answer.get('data', {}).get('prepareParticipate', {}).get('allow', {}):
                return True
        return False

    async def start_claim_second_nft(self, fifty_five_points):
        async def execute_task(task_function, task_name):
            status = await task_function()
            if not status:
                logger.warning(f'{self.data.address} | не смог подтвердить {task_name}')
            return status
        
        required_points = 55 if fifty_five_points else 70

        current_points = await self.get_second_nft_current_points()
        if current_points != required_points:
            logger.info(
                f'{self.data.address} | текущее кол-во поинтов 2 квеста galxe: {current_points}. Начинаю выполнять задачи...')

            if self.data.token:
                await execute_task(self.start_confirm_twitter_tasks, "start_confirm_twitter_tasks")

            await execute_task(self.visit_proof_of_liquidity_task, "visit_proof_of_liquidity_task")
            await execute_task(self.confirm_two_in_one_galxe_tasks, "confirm_two_in_one_galxe_tasks")

            current_points = await self.get_second_nft_current_points()
            if current_points != required_points:
                for task_id in ['365785346000723968', '365757873263386624', '367963574928842752']:
                    await execute_task(lambda: self.confirm_galxe_task(task_id), f"задание {task_id}")

            current_points = await self.get_second_nft_current_points()
            logger.info(f'{self.data.address} | текущее кол-во поинтов 2 квеста galxe: {current_points}.')

        if current_points >= required_points:
            logger.info(
                f'{self.data.address} | текущее кол-во поинтов 2 квеста galxe: {current_points}. Начинаю клейм...')
            captha_solution = await self.prepare_and_solution_captcha()
            if captha_solution:
                status = await self.claim_second_nft_quest(solution=captha_solution)
                if status:
                    self.data.finished_claim_second_nft = True
                    await self.write_to_db()
                    logger.success(
                        f'{self.data.address} | успешно склеймил второе нфт, кол-во за 2 нфт поинтов: {current_points}')
                    return True

        return False

    async def write_to_db(self):
        async with AsyncSession(db.engine) as session:
            await session.merge(self.data)
            await session.commit()
