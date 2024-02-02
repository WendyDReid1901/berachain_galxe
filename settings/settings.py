import os
from dotenv import load_dotenv

load_dotenv()

# КОЛ-ВО ПОПЫТОК
NUMBER_OF_ATTEMPTS = int(os.getenv('NUMBER_OF_ATTEMPTS'))

# Одновременное кол-во асинк семафоров для запросов
ASYNC_SEMAPHORE = int(os.getenv('ASYNC_SEMAPHORE'))

# Использовать капчу или самостоятельное решение
USE_CAPTHA_SERVICE = True

# КЛЮЧ от капчи
TWO_CAPTHA_API_KEY = os.getenv('API_KEY_2CAPTCHA')
API_KEY_CAPMONSTER = os.getenv('API_KEY_CAPMONSTER')

# DAILY w token
W = os.getenv('W')

# SLEEP BEETWEEN ACTION
FROM = 250
TO = 500

# ADD_TWITTER 
ADD_TWITTER = False
