# chat-bot
"""tg-bot"""
import logging
import time
import os
from logging.handlers import RotatingFileHandler
from http import HTTPStatus
import requests
import telegram
from dotenv import load_dotenv


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

RETRY_TIME = 600
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
        logger.error(f'Сообщение не отправлено "{message}".')
    else:
        logger.info(f'Сообщение успешно отправлено "{message}".')


def get_api_answer(current_timestamp):
    """Получаем АПИ ответ."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homeworks = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.ConnectionError as error:
        message = f'Другая ошибка {error}.'
        logger.error(message)
    if homeworks.status_code == HTTPStatus.OK:
        return homeworks.json()
    raise Exception(
        f'Сбой в работе программы: Эндпоинт {ENDPOINT} не доступен.'
        f'Код ответа API {homeworks.status_code}.'
    )


def check_response(response):
    """Проверяет ответ API на корректность."""
    homeworks = response['homeworks']
    if not isinstance(response, dict):
        logger.error('Ответ API тип данных не "словарь".')
        raise TypeError('Ответ API тип данных не "словарь".')
    if 'homeworks' not in dict(response):
        raise KeyError('Отсутствует ключ "homeworks" в ответе API.')
    if not homeworks:
        logger.debug('Статус не изменился.')
    if not isinstance(homeworks, list):
        logger.error('Неверный список работ.')
        raise TypeError('Неверный список работ.')
    return homeworks


def parse_status(homework):
    """Получаем информацию о конкретной домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API.')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API.')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception(f'Неизвестный статус работы: {homework_status}.')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}.'



def check_tokens():
    """Проверяет доступность переменных окружения."""
    test_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    for key, value in test_tokens.items():
        if not value[PRACTICUM_TOKEN] in test_tokens:
            logger.critical(f'Отсутствует необходиый токен {key}')
            return False
        if not value[TELEGRAM_TOKEN] in test_tokens:
            logger.critical(f'Отсутствует необходиый токен {key}')
            return False
        if not value[TELEGRAM_CHAT_ID] in test_tokens:
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
            message = f'Сбой в работе программы: {error}.'
            send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
