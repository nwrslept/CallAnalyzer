import os
import asyncio
import time
from src.config import Config
from src.google_drive import DriveService
from src.ai_processor import AIProcessor
from src.google_sheets import SheetsService
from src.database import Database
from src.logger import logger


async def main():
    """
    Головна функція запуску бота.
    Працює ПОСЛІДОВНО, але використовує асинхронну базу даних
    для пропуску вже оброблених файлів.
    Веде запис подій у файл bot.log та консоль.
    """
    logger.info("🤖 --- ЗАПУСК БОТА --- 🤖")

    # 1. Ініціалізація сервісів
    try:
        # Синхронні сервіси (Drive, AI, Sheets)
        drive = DriveService()
        ai = AIProcessor()
        sheets = SheetsService()

        # Асинхронна база даних
        db = Database()
        await db.init()

        logger.info("✅ Сервіси успішно підключено.\n")
    except Exception as e:
        logger.error(f"❌ Критична помилка при запуску: {e}")
        return

    # 2. Отримання списку файлів
    try:
        files = drive.list_audio_files(Config.SOURCE_FOLDER_ID)
    except Exception as e:
        logger.error(f"❌ Помилка доступу до Google Drive: {e}")
        return

    if not files:
        logger.info("📭 Файлів не знайдено.")
        return

    logger.info(f"📂 Знайдено {len(files)} файлів. Перевірка бази даних...\n")

    # 3. Основний цикл обробки (ПО ЧЕРЗІ)
    for i, file_info in enumerate(files, 1):
        file_name = file_info['name']
        file_id = file_info['id']

        # Перевірка в базі даних (чи обробляли ми цей файл раніше?)
        if await db.file_exists(file_id):
            logger.info(f"[{i}/{len(files)}] ⏭️  Пропуск: {file_name} (вже є в базі)")
            continue

        logger.info(f"[{i}/{len(files)}] 🔄 Обробка: {file_name}...")

        try:
            # Скачування
            local_path = drive.download_file(file_id, file_name)

            # Аналіз AI
            result = ai.analyze_call(local_path)

            # Логіка корекції оцінки
            if result.get('manager_score', 0) > 6:
                result['is_critical_fail'] = False
                result['critical_comment'] = ""

            # Запис у Таблицю
            sheets.append_analysis(file_name, result)

            # Запис успіху в Базу Даних
            await db.add_file(file_id, file_name, result.get('manager_score', 0))

            # Видалення локального файлу
            if os.path.exists(local_path):
                os.remove(local_path)

            logger.info(f"   ✅ Готово. Оцінка: {result.get('manager_score')}")

        except Exception as e:
            logger.error(f"   ❌ Помилка під час обробки {file_name}: {e}")
            # Видаляємо файл, якщо він залишився пошкодженим
            local_path = os.path.join(Config.TEMP_FOLDER, file_name)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass

        # Пауза для стабільності API
        time.sleep(1)

    logger.info("\n🎉 ВСІ ЗАВДАННЯ ВИКОНАНО!")


if __name__ == "__main__":
    asyncio.run(main())
