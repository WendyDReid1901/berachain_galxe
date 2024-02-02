import inquirer
from termcolor import colored
from inquirer.themes import load_theme_from_dict as loadth


def get_action() -> str:
    """ Пользователь выбирает действие через меню"""

    # Тема
    theme = {
        'Question': {
            'brackets_color': 'bright_yellow'
        },
        'List': {
            'selection_color': 'bright_blue'
        },
    }

    # Варианты для выбора
    question = [
        inquirer.List(
            "action",
            message=colored('Выберете ваше действие', 'light_yellow'),
            choices=[
                '   1) Импорт в базу данных',
                '   2) Получить токены с крана',
                '   3) Репостнуть и подписаться',
                '   4) Проверить баланс на кошельках',
                '   5) daily mint на galxe',
                '   6) Базовые действия galxe (ончейн)',
                '   7) Claim galxe 70 points',
                '   8) Claim galxe 50 points (без твиттера)',
            ]
        )
    ]

    return inquirer.prompt(question, theme=loadth(theme))['action']
