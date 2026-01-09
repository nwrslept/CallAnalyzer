import aiosqlite
import os
from datetime import datetime


class Database:
    """
    Асинхронний менеджер бази даних SQLite.
    Відповідає за зберігання історії оброблених файлів.
    """

    def __init__(self, db_name="bot_db.db"):
        self.db_name = db_name

    async def init(self):
        """Створює таблицю, якщо вона ще не існує."""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_id TEXT PRIMARY KEY,
                    file_name TEXT,
                    manager_score INTEGER,
                    processed_at TIMESTAMP
                )
            """)
            await db.commit()

    async def file_exists(self, file_id: str) -> bool:
        """Перевіряє, чи файл вже був оброблений."""
        async with aiosqlite.connect(self.db_name) as db:
            cursor = await db.execute(
                "SELECT 1 FROM processed_files WHERE file_id = ?", (file_id,)
            )
            return await cursor.fetchone() is not None

    async def add_file(self, file_id: str, file_name: str, score: int):
        """Записує успішно оброблений файл у базу."""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT OR REPLACE INTO processed_files (file_id, file_name, manager_score, processed_at) VALUES (?, ?, ?, ?)",
                (file_id, file_name, score, datetime.now())
            )
            await db.commit()
