import os
import time
from src.config import Config
from src.google_drive import DriveService
from src.ai_processor import AIProcessor
from src.google_sheets import SheetsService


def main():
    """
    Головна функція запуску бота.
    Виконує послідовну обробку аудіофайлів: скачування -> аналіз (AI) -> запис у таблицю.
    """
    print("🤖 --- ЗАПУСК БОТА --- 🤖")

    # 1. Ініціалізація сервісів (Drive, AI, Sheets)
    try:
        drive = DriveService()
        ai = AIProcessor()
        sheets = SheetsService()
        print("✅ Сервіси успішно підключено.\n")
    except Exception as e:
        print(f"❌ Критична помилка при запуску: {e}")
        return

    # 2. Отримання списку файлів з папки джерела
    files = drive.list_audio_files(Config.SOURCE_FOLDER_ID)
    if not files:
        print("📭 Файлів не знайдено.")
        return

    print(f"📂 Знайдено {len(files)} файлів. Починаємо обробку...\n")

    # 3. Основний цикл обробки кожного файлу
    for i, file_info in enumerate(files, 1):
        file_name = file_info['name']
        print(f"[{i}/{len(files)}] 🔄 Обробка: {file_name}...")

        try:
            # А. Скачування аудіофайлу у локальну тимчасову папку
            local_path = drive.download_file(file_info['id'], file_name)

            # Б. Аналіз розмови за допомогою штучного інтелекту
            result = ai.analyze_call(local_path)

            # Логіка корекції: якщо оцінка висока (>6), знімаємо прапорець критичної помилки,
            # навіть якщо AI помилково його встановив.
            if result.get('manager_score', 0) > 6:
                result['is_critical_fail'] = False
                result['critical_comment'] = ""

            # В. Запис результатів у Google Таблицю
            # (включаючи автоматичне фарбування низьких оцінок у червоний колір)
            sheets.append_analysis(file_name, result)

            # Г. Видалення локального файлу для звільнення місця
            if os.path.exists(local_path):
                os.remove(local_path)

            print(f"   ✅ Готово. Оцінка: {result.get('manager_score')}")

        except Exception as e:
            print(f"   ❌ Помилка під час обробки: {e}")

        # Невелика пауза між запитами для стабільності API
        time.sleep(1)

    print("\n🎉 ВСІ ЗАВДАННЯ ВИКОНАНО!")


if __name__ == "__main__":
    main()
