import re
from data.config import TWITTER_TOKENS


def get_accounts_info(path):
    with open(path, 'r', encoding='utf-8-sig') as file:
        if path == TWITTER_TOKENS:
            info: list[str] = [validate_token(input_string=row.strip()) for row in file]
        else:
            info: list[str] = [row.strip() for row in file]
    return info


def validate_token(input_string: str) -> str | None:
    word_pattern = r'^[a-z0-9]{40}$'
    words = re.split(r'[\s,:;.()\[\]{}<>]', input_string)

    for word in words:
        if re.match(word_pattern, word):
            return word

    return None
