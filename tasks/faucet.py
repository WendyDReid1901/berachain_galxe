import re
import time
import json
import random
import string
import base64
import struct
from urllib.parse import urlencode

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from better_automation.base import BaseAsyncSession

from eth.eth_client import EthClient
from db_api.database import Wallet, db
from settings.settings import NUMBER_OF_ATTEMPTS, USE_CAPTHA_SERVICE, TWO_CAPTHA_API_KEY
from data.config import logger


class Faucet:

    def __init__(self, data: Wallet):
        self.data = data
        self.eth_client = EthClient(private_key=data.private_key, proxy=data.proxy, user_agent=data.user_agent)
        self.async_session = BaseAsyncSession(proxy=data.proxy, verify=False)
        self.version = self.data.user_agent.split('Chrome/')[1].split('.')[0]
        self.cb = self.generate_cb().lower()
        self.random_id = self.generate_encoded_id(3327617, 3330000)
        self.task_id = None

    @staticmethod
    def generate_cb(length=12):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    @staticmethod
    def generate_encoded_id(min_value, max_value):
        random_int = random.randint(min_value, max_value)
        bytes_int = struct.pack('>I', random_int)
        encoded = base64.b64encode(bytes_int)
        return encoded.decode('utf-8')

    async def start_claim_tokens_from_faucet(self):
        for num, _ in enumerate(range(NUMBER_OF_ATTEMPTS), start=1):
            logger.info(f'{self.data.address} | Попытка {num}')
            status = await self.start_login()
            if status:
                break
            continue

    async def get_solution(self):

        try:
            url_base = 'https://www.google.com/recaptcha/'

            param = {
                'ar': '1',
                'k': '6LfOA04pAAAAAL9ttkwIz40hC63_7IsaU2MgcwVH',
                'co': 'aHR0cHM6Ly9hcnRpby5mYXVjZXQuYmVyYWNoYWluLmNvbTo0NDM.',
                'hl': 'en',
                'v': 'Ya-Cd6PbRI5ktAHEhm9JuKEu',
                'size': 'invisible',
                'cb': self.cb
            }

            anchor_url = url_base + 'api2/anchor?' + urlencode(param)

            headers = {
                'authority': 'www.google.com',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'referer': 'https://artio.faucet.berachain.com/',
                'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{self.version}", "Google Chrome";v="{self.version}"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{self.data.platform}"',
                'sec-fetch-dest': 'iframe',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'cross-site',
                'upgrade-insecure-requests': '1',
                'user-agent': self.data.user_agent,
                'x-client-data': self.random_id,
            }

            post_data = "v={}&reason=q&c={}&k={}&co={}"
            matches = re.findall('([api2|enterprise]+)\/anchor\?(.*)', anchor_url)[0]
            url_base += matches[0] + '/'
            params = matches[1]
            res = await self.async_session.get(anchor_url, headers=headers)
            token = re.findall(r'"recaptcha-token" value="(.*?)"', res.text)[0]
            params = dict(pair.split('=') for pair in params.split('&'))
            post_data = post_data.format(params["v"], token, params["k"], params["co"])

            headers = {
                'authority': 'www.google.com',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://www.google.com',
                'referer': anchor_url,
                'sec-ch-ua': f'"Not_A Brand";v="8", "Chromium";v="{self.version}", "Google Chrome";v="{self.version}"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{self.data.platform}"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': self.data.user_agent,
                'x-client-data': self.random_id,
            }

            k = {
                'k': params['k'],
            }

            res = await self.async_session.post(
                f'{url_base}reload',
                headers=headers,
                params=k,
                data=post_data,
            )

            solution = re.findall(r'"rresp","(.*?)"', res.text)[0]
            return True, solution
        except:
            return False, 'failed to obtain a solution'

    async def start_login(self):
        if not USE_CAPTHA_SERVICE:
            status, solution = await self.get_solution()
            if status:
                await asyncio.sleep(random.randint(3, 5))
                status = await self.try_claim_from_faucet(solution)
                if status:
                    return True
                return False
            else:
                logger.warning(f'{self.data.address} | не смог получить решение')
                return False
        else:
            status, self.task_id = await self.two_captha_task_create()
            if status:
                msg = (f'{self.data.address} | задача 2captcha успешно создана, task_id: {self.task_id}. '
                       f'Начинаю проверять решение...')
                logger.info(msg)
                status, solution = await self.check_two_captha_task_complete()
                if status:
                    logger.info(f'{self.data.address} | задача 2captcha успешно решена. Пробую отправить решение...')
                    status = await self.try_claim_from_faucet(solution)
                    if status:
                        return True
                    return False
                else:
                    logger.warning(f'{self.data.address} | не смог получить решение задачи.')
                    return False
            else:
                logger.warning(f'{self.data.address} | не смог создать задачу.')
                return False

    async def two_captha_task_create(self) -> (bool, str):
        # API v.1

        # data = {
        #     'key': TWO_CAPTHA_API_KEY,
        #     'method': 'userrecaptcha',
        #     'version': 'v3',
        #     'googlekey': '6LfOA04pAAAAAL9ttkwIz40hC63_7IsaU2MgcwVH',
        #     'pageurl': 'artio-80085-faucet-api-recaptcha.berachain.com',
        #     'json': 1
        # }
        # response = await self.async_session.post('https://2captcha.com/in.php', data=data)
        # answer = response.json()
        # if answer['status'] == 1:
        #     return True, answer['request']
        # return False, 'task not create'

        # API v.2

        json_data = {
            "clientKey": TWO_CAPTHA_API_KEY,
            "task": {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": "https://artio.faucet.berachain.com/",
                "websiteKey": "6LfOA04pAAAAAL9ttkwIz40hC63_7IsaU2MgcwVH",
                "minScore": 0.8,
            }
        }

        response = await self.async_session.post('https://api.2captcha.com/createTask', json=json_data)
        try:
            answer = response.json()
            if 'errorId' in answer and answer['errorId'] == 0:
                return True, answer.get('taskId', 'No request key in response')
            return False, answer.get('errorId', 'Unknown error')
        except Exception as e:
            return False, f'Error parsing response: {e}'

    async def check_two_captha_task_complete(self) -> (bool, str):
        # API v.1

        # i = 0
        # while i < 180:
        #     params = {
        #         'key': TWO_CAPTHA_API_KEY,
        #         'id': self.task_id,
        #         'action': 'get',
        #         'json': 1,
        #     }
        #     response = await self.async_session.get('https://2captcha.com/res.php', params=params)
        #     answer = response.json()
        #     if answer['status'] == 1:
        #         return True, answer['request']
        #     i += 1
        #     await asyncio.sleep(1)
        # if USE_CAPTHA_SERVICE:
        #     await self.send_report('reportbad')
        # return False, 'task not complete'

        # API v.2

        i = 0
        while i < 300:
            data = {
                "clientKey": TWO_CAPTHA_API_KEY,
                "taskId": self.task_id
            }

            response = await self.async_session.post('https://api.2captcha.com/getTaskResult', json=data)
            result = response.json()
            if result.get('status', False) == 'processing':
                i += 1
                await asyncio.sleep(1)
                continue
            elif result.get('status', False) == 'ready':
                return True, result['solution']['gRecaptchaResponse']
            elif result.get('status', False) != 0:
                msg = f'{result.get("errorCode", "Unknown code")} | {result.get("errorDescription", "Unknown error")}'
                logger.warning(f'{self.data.address} | {msg}.')
                return False, msg

            i += 1
            await asyncio.sleep(1)
        await self.report_bad()
        return False, 'Not possible receive solution'

    async def try_claim_from_faucet(self, solution: str):

        headers = {
            'authority': 'artio-80085-faucet-api-recaptcha.berachain.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {solution}',
            'content-type': 'text/plain;charset=UTF-8',
            'origin': 'https://artio.faucet.berachain.com',
            'referer': 'https://artio.faucet.berachain.com/',
            'sec-ch-ua': f'"Not A(Brand";v="99", "Google Chrome";v="{self.version}", "Chromium";v="{self.version}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{self.data.platform}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': self.data.user_agent,
        }

        params = {
            'address': self.eth_client.account.address,
        }

        data = json.dumps({"address": self.eth_client.account.address})

        response = await self.async_session.post(
            'https://artio-80085-faucet-api-recaptcha.berachain.com/api/claim',
            params=params,
            headers=headers,
            data=data,
        )

        answer = response.json()

        if response.status_code == 200 and answer['msg']:
            logger.success(f'{self.data.address} | успешно заклеймил токены через кран. {answer["msg"]}')
            self.data.next_available_claim = int(time.time()) + (8 * 60 * 60)
            await self.write_to_db()
            if USE_CAPTHA_SERVICE:
                # API v.1
                # await self.send_report('reportgood')

                # API v.2
                await self.report_good()
            return True

        if 'You have exceeded the rate limit' in answer['msg']:
            logger.warning(f'{self.data.address} | не смог склеймить, попробуйте позже. Ответ сервера: {answer["msg"]}.')
            # self.data.next_available_claim = int(time.time()) + (8 * 60 * 60)
            # await self.write_to_db()
            if USE_CAPTHA_SERVICE:
                # API v.1
                # await self.send_report('reportgood')

                # API v.2
                await self.report_good()
            return True

        else:
            msg = f'{self.data.address} | произошла ошибка, буду пробовать еще раз. Ответ сервера: {answer["msg"]}'
            logger.warning(msg)
            if USE_CAPTHA_SERVICE:
                # API v.1
                # await self.send_report('reportbad')

                # API v.2
                await self.report_bad()
            return False

    async def report_good(self):
        json_data = {
            "clientKey": TWO_CAPTHA_API_KEY,
            "taskId": self.task_id
        }

        response = await self.async_session.post('https://api.2captcha.com/reportCorrect', json=json_data)
        answer = response.json()
        if answer.get('status') == 'success':
            logger.warning(f'{self.data.address} | выслал отчет об успешном решение капчи.')
            return
        logger.error(
            f'{self.data.address} | не смог выслать отчет об успешном решение капчи. Ответ сервера: {answer}.')

    async def report_bad(self):
        json_data = {
           "clientKey": TWO_CAPTHA_API_KEY,
           "taskId": self.task_id
        }

        response = await self.async_session.post('https://api.2captcha.com/reportIncorrect', json=json_data)
        answer = response.json()
        if answer.get('status') == 'success':
            logger.warning(f'{self.data.address} | выслал отчет об плохом решение капчи.')
            return
        logger.error(f'{self.data.address} | не смог выслать отчет о плохом решение капчи. Ответ сервера: {answer}.')

    async def send_report(self, action):
        solution = {
            'reportgood': 'выслал отчет об успешном решение капчи.',
            'reportbad': 'выслал отчет об плохом решение капчи.'
        }

        params = {
            'key': TWO_CAPTHA_API_KEY,
            'action': action,
            'id': self.task_id,
            'json': 1
        }
        response = await self.async_session.get('https://2captcha.com/res.php', params=params)
        answer = response.json()
        if answer['request'] == 'OK_REPORT_RECORDED':
            logger.warning(f'{self.data.address} | {solution[action]}')
            return
        logger.error(f'{self.data.address} | {solution[action]} Ответ сервера: {answer}.')

    async def write_to_db(self):
        async with AsyncSession(db.engine) as session:
            await session.merge(self.data)
            await session.commit()
