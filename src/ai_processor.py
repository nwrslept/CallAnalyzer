import json
import time
from google import genai
from google.genai import types
from src.config import Config
from src.logger import logger

class AIProcessor:
    """
    Клас для взаємодії з Google Gemini API через новий SDK 'google-genai'.
    Відповідає за завантаження аудіо, генерацію промптів та парсинг відповідей.
    """

    def __init__(self):
        # Перевірка наявності ключа API у конфігурації
        if not Config.GEMINI_API_KEY:
            logger.error("❌ Відсутній API ключ Gemini у конфігурації!")
            raise ValueError("Відсутній API ключ Gemini у конфігурації!")

        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = "gemini-2.0-flash"

    def _clean_json_string(self, text_response: str) -> str:
        """
        Очищує рядок відповіді від маркерів форматування Markdown (```json ... ```),
        щоб підготувати його для парсингу через json.loads.
        """
        if text_response.startswith("```json"):
            text_response = text_response[7:-3]
        elif text_response.startswith("```"):
            text_response = text_response[3:-3]

        return text_response.strip()

    def analyze_call(self, audio_path: str) -> dict:
        """
        Основний метод аналізу дзвінка.
        Завантажує файл, відправляє запит до AI та повертає структуровані дані.
        """
        logger.info(f"DEBUG: Завантаження {audio_path} у Gemini...")

        try:
            # 1. Завантаження аудіофайлу на сервери Google
            with open(audio_path, "rb") as f:
                file_ref = self.client.files.upload(
                    file=f,
                    config={'mime_type': 'audio/mp3'}
                )

            services_str = ", ".join(Config.SERVICES_LIST)

            # 2. Формування системного промпту
            prompt = f"""
            Ти — QA в автосервісі. Проаналізуй дзвінок українською.

            1. Транскрибація (дослівна).
            2. Тип послуги: ТІЛЬКИ ОДИН з [{services_str}].
            3. KPI (1 - так, 0 - ні):
               - Привітання?
               - КУЗОВ?
               - РІК?
               - ПРОБІГ?
               - Запропонував діагностику (Upsell)?
               - Історія авто?
               - Прощання?
            4. Оцінка (1-10).
            5. Результат (Записався/Думає/Відмова).
            6. Критичні помилки.

            Output format: Pure JSON object.
            Keys: transcription, service_type, manager_score, result, is_critical_fail, critical_comment, kpi_greeting, kpi_body, kpi_year, kpi_mileage, kpi_upsell, kpi_history, kpi_closing.
            """

            # 3. Генерація відповіді з механізмом повторних спроб (Retry)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=[file_ref, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        )
                    )

                    # Очищення та парсинг JSON
                    clean_text = self._clean_json_string(response.text)

                    # strict=False дозволяє коректно обробляти спецсимволи (наприклад, переноси рядків)
                    parsed_data = json.loads(clean_text, strict=False)

                    # Обробка випадку, коли AI повертає список замість словника
                    if isinstance(parsed_data, list):
                        if len(parsed_data) > 0:
                            parsed_data = parsed_data[0]
                        else:
                            return self._get_error_object("AI повернув порожній список")

                    return parsed_data

                except Exception as e:
                    # Обробка лімітів API (429 Too Many Requests)
                    if "429" in str(e) or "quota" in str(e).lower():
                        wait_time = 40
                        logger.warning(f"⚠️ Вичерпано квоту API. Очікування {wait_time} с...")
                        time.sleep(wait_time)

                    # Обробка помилок структури JSON (спробуємо ще раз)
                    elif isinstance(e, json.JSONDecodeError):
                        logger.warning(f"⚠️ Помилка парсингу JSON (спроба {attempt + 1}): {e}")
                        continue
                    else:
                        raise e

            return self._get_error_object("Не вдалося проаналізувати файл після всіх спроб")

        except Exception as e:
            logger.error(f"❌ Критична помилка AI: {e}")
            return self._get_error_object(str(e))

    def _get_error_object(self, msg):
        """Повертає структуру даних за замовчуванням (заглушку) у разі помилки."""
        return {
            "transcription": f"Error: {msg}", "service_type": "Error",
            "manager_score": 0, "is_critical_fail": True, "critical_comment": "System Error",
            "kpi_greeting": 0, "kpi_body": 0, "kpi_year": 0, "kpi_mileage": 0,
            "kpi_upsell": 0, "kpi_history": 0, "kpi_closing": 0, "result": "Error"
        }
