import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime
from src.config import Config


class SheetsService:
    """
    Сервіс для роботи з Google Sheets.
    Відповідає за авторизацію, створення структури таблиці, запис результатів аналізу
    та умовне форматування (підсвічування проблемних дзвінків).
    """

    def __init__(self):
        # Визначаємо права доступу (Scopes) для редагування таблиць
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        # Авторизація через Service Account
        self.creds = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_CREDENTIALS_FILE,
            scopes=SCOPES
        )

        # Оновлення токена доступу, якщо він застарів
        if not self.creds.valid:
            self.creds.refresh(Request())

        # Ініціалізація клієнта API
        self.service = build('sheets', 'v4', credentials=self.creds)
        self.spreadsheet_id = Config.SHEET_ID
        self.sheet_name = "Test_Run"

        # Перевірка наявності заголовків при старті
        self.setup_headers()

    def _get_sheet_id_by_name(self, sheet_name: str) -> int:
        """
        Отримує внутрішній числовий ID аркуша (sheetId) за його назвою.
        Необхідний для запитів форматування (batchUpdate).
        """
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            return 0
        except Exception:
            return 0

    def setup_headers(self):
        """
        Перевіряє, чи порожня таблиця. Якщо так — створює заголовки та форматує їх.
        """
        range_name = f"{self.sheet_name}!A1"
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id, range=range_name).execute()

        # Якщо даних немає, створюємо шапку
        if not result.get('values'):
            headers = [
                "Дата", "Назва файлу", "Телефон", "Філія", "Менеджер",
                "Привітання (1/0)", "Дізнався КУЗОВ (1/0)", "Дізнався РІК (1/0)",
                "Дізнався ПРОБІГ (1/0)", "Запроп. ДІАГНОСТ. (1/0)", "Історія авто (1/0)",
                "Прощання (1/0)", "Тип послуги", "Результат",
                "Оцінка (1-10)", "Коментар", "Транскрибація"
            ]

            body = {'values': [headers]}

            # Запис заголовків
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id, range=f"{self.sheet_name}!A1",
                valueInputOption="USER_ENTERED", body=body
            ).execute()

            # Застосування стилю (жирний шрифт, сірий фон)
            self._format_header(self._get_sheet_id_by_name(self.sheet_name))

    def append_analysis(self, file_name: str, ai_data: dict):
        """
        Додає новий рядок з даними аналізу в таблицю та застосовує кольорове маркування.
        """
        today = datetime.now().strftime("%d.%m.%Y")
        row_values = ["-"] * 17

        # --- Заповнення даних ---
        row_values[0] = today
        row_values[1] = file_name

        # Блок KPI (ключові показники ефективності)
        row_values[5] = ai_data.get('kpi_greeting', 0)
        row_values[6] = ai_data.get('kpi_body', 0)
        row_values[7] = ai_data.get('kpi_year', 0)
        row_values[8] = ai_data.get('kpi_mileage', 0)
        row_values[9] = ai_data.get('kpi_upsell', 0)
        row_values[10] = ai_data.get('kpi_history', 0)
        row_values[11] = ai_data.get('kpi_closing', 0)

        # Інформаційний блок
        row_values[12] = ai_data.get('service_type', '-')
        row_values[13] = ai_data.get('result', '-')

        score = ai_data.get('manager_score', 0)
        row_values[14] = score

        row_values[15] = ai_data.get('critical_comment', '')
        row_values[16] = ai_data.get('transcription', '')[:1000]  # Обрізка занадто довгих текстів

        body = {'values': [row_values]}

        try:
            # 1. Запис даних у таблицю
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id, range=f"{self.sheet_name}!A1",
                valueInputOption="USER_ENTERED", body=body
            ).execute()

            # 2. Отримання номера рядка, куди було записано дані
            updated_range = result.get('updates', {}).get('updatedRange', '')
            if updated_range:
                # Парсинг номера рядка з відповіді API (наприклад, 'Sheet1!A2:Q2')
                row_index = int(updated_range.split('!')[1].split(':')[0][1:])
                sheet_id = self._get_sheet_id_by_name(self.sheet_name)

                # --- Логіка умовного форматування ---

                # А) Якщо оцінка низька (<= 6), фарбуємо клітинку оцінки (Колонка O, індекс 14)
                is_low_score = score <= 6
                self._set_cell_format(row_index, sheet_id, is_low_score, 14)

                # Б) Якщо є критична помилка, фарбуємо клітинку коментаря (Колонка P, індекс 15)
                is_critical = ai_data.get('is_critical_fail', False)
                self._set_cell_format(row_index, sheet_id, is_critical, 15)

        except Exception as e:
            print(f"❌ Помилка роботи з Google Sheets: {e}")

    def _format_header(self, sheet_id: int):
        """
        Задає стиль для першого рядка (заголовків): сірий фон та жирний шрифт.
        """
        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                    "startColumnIndex": 0, "endColumnIndex": 17
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8},
                        "textFormat": {"bold": True}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        }]
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={'requests': requests}).execute()

    def _set_cell_format(self, row_index: int, sheet_id: int, is_red: bool, col_index: int):
        """
        Змінює колір комірки.
        Якщо is_red=True: Світло-червоний фон, червоний текст.
        Якщо is_red=False: Білий фон, чорний текст.
        """
        if is_red:
            bg = {"red": 1.0, "green": 0.8, "blue": 0.8}
            txt = {"red": 1.0, "green": 0.0, "blue": 0.0}
            bold = True
        else:
            bg = {"red": 1.0, "green": 1.0, "blue": 1.0}
            txt = {"red": 0.0, "green": 0.0, "blue": 0.0}
            bold = False

        requests = [{
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_index - 1, "endRowIndex": row_index,
                    "startColumnIndex": col_index, "endColumnIndex": col_index + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": bg,
                        "textFormat": {"foregroundColor": txt, "bold": bold}
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)"
            }
        }]
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id, body={'requests': requests}).execute()
