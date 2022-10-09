import logging
import requests
import telegram
import time
import os
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log', maxBytes=50000000, backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError():
        logger.error(f'Сообщение не отправлено "{message}"')
    else:
        logger.info(f'Сообщение успешно отправлено "{message}"')


def get_api_answer(current_timestamp):
    """Получаем АПИ ответ."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, params=params)
    except Exception as error:
        message = f'Другая ошибка {error}'
        logger.error(message)
    if homeworks.status_code == 200:
        return homeworks.json()
    else:
        raise Exception(
            f'Сбой в работе программы: Эндпоинт {ENDPOINT} не доступен.'
            f'Код ответа API {homeworks.status_code}'
        )


def check_response(response):
    """Проверяет ответ API на корректность."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        raise KeyError(f'{error} не верный ответ')
    if not homeworks:
        logger.debug('Статус не изменился')
    if not isinstance(homeworks, list):
        logger.error('Неверный список работ.')
        raise TypeError('Неверный список работ.')
    return homeworks


def parse_status(homeworks):
    """Извлекает из инф о конкретной домашней работе статус этой работы."""
    try:
        homework_name = homeworks.get('homework_name')
        homework_status = homeworks.get('status')
    except KeyError as error:
        logger.error(f'{error} не верный ответ')
        raise KeyError('Статус работы не документирован')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error('Работа не проверена')
        raise KeyError('Ваша работа еще не проверена')

    verdict = HOMEWORK_STATUSES.get(homework_status)

    if homework_status in HOMEWORK_STATUSES:
        return (f'Статус изменился {homework_name},{verdict}')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    test_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for key, value in test_tokens.items():
        if value is None:
            logger.critical(f'Отсутствует необходиый токен {key}')
            return False
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                verdict = parse_status(homework)
                send_message(bot, verdict)
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(TELEGRAM_CHAT_ID, message)
            time.sleep(RETRY_TIME)
        else:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
