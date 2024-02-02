import os
import sys
import asyncio
from pathlib import Path

from loguru import logger

# Определяем путь и устанавливаем root dir
if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent.absolute()
else:
    ROOT_DIR = Path(__file__).parent.parent.absolute()

# Папка status
STATUS_DIR = os.path.join(ROOT_DIR, 'status')
LOG = os.path.join(STATUS_DIR, 'log.txt')
PROBLEM_PROXY = os.path.join(STATUS_DIR, 'proxy_problem.txt')
PROBLEMS = os.path.join(STATUS_DIR, 'problems.txt')
WALLETS_DB = os.path.join(STATUS_DIR, 'accounts.db')

# Папка accounts
ACCOUNTS_DIR = os.path.join(ROOT_DIR, 'accounts')
TWITTER_TOKENS = os.path.join(ACCOUNTS_DIR, 'twitter_tokens.txt')
PROXYS = os.path.join(ACCOUNTS_DIR, 'proxys.txt')
PRIVATE_KEYS = os.path.join(ACCOUNTS_DIR, 'private_keys.txt')
EMAIL_DATA = os.path.join(ACCOUNTS_DIR, 'email.txt')

# Создаем отсутсвующие директории
DIRS_TO_CREATE = [ACCOUNTS_DIR, STATUS_DIR]

# Создаем отсутсвующие файлы
IMPORTANT_FILES = [LOG, PROBLEM_PROXY, PROBLEMS, TWITTER_TOKENS, PROXYS, PRIVATE_KEYS, EMAIL_DATA]

# Кол-во выполненных асинхронных задач, блокировщий задач asyncio
completed_tasks = [0]
tasks_lock = asyncio.Lock()

# Логер
logger.add(LOG, format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}', level='DEBUG')

# Wallet status
WALLET = [0, 0, 0]

FILES_DIR = os.path.join(ROOT_DIR, 'settings')
ABIS_DIR = os.path.join(ROOT_DIR, 'data', 'abis')
SETTINGS_FILE = os.path.join(FILES_DIR, 'settings.json')

