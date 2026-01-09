import logging
import sys
import os


def setup_logger():
    """
    Налаштовує логер, який пише одночасно:
    1. У файл 'bot.log' (з датою і часом)
    2. У консоль
    """
    # Створюємо логер
    logger = logging.getLogger("CallAnalyzer")
    logger.setLevel(logging.INFO)

    # Очищуємо старі хендлери, щоб не було дублювання при перезапуску
    if logger.handlers:
        logger.handlers.clear()

    # Налаштування запису у ФАЙЛ
    file_handler = logging.FileHandler("bot.log", encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    # Формат: [Час] [Рівень] Повідомлення
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)

    # Налаштування виводу в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)

    # Додаємо обидва обробники до логера
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Створюємо глобальний об'єкт логера, який будемо імпортувати
logger = setup_logger()
