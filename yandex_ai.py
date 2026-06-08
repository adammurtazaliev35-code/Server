# yandex_ai.py
import os
import requests
import json
from typing import Optional

class YandexGPTClient:
    def __init__(self, api_key: str, folder_id: str, model: str = "yandexgpt"):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model = model
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        self.headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "x-folder-id": self.folder_id,
            "Content-Type": "application/json"
        }

def generate_prompt(self, user_input: str, model_key: str, locale: str = 'ru', use_instructions: bool = False) -> Optional[str]:
    # Добавляем условие для системного промпта
    instruction_rule = "Обязательно выдели дополнительные инструкции в кавычки или скобки." if use_instructions else "Инструкции не нужно выделять специальными символами."

    system_prompt = (
        f"Ты — эксперт по созданию промптов для LLM. "
        f"Пользователь хочет улучшить свой запрос для модели {model_key}. "
        f"Ответь только готовым промптом на языке {locale} без лишних пояснений. "
        f"Промпт должен быть чётким, структурированным, содержать роль, инструкции, "
        f"ограничения (если нужно) и требуемый формат ответа. {instruction_rule}"
    )

        body = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.6,
                "maxTokens": 500
            },
            "messages": [
                {"role": "system", "text": system_prompt},
                {"role": "user", "text": f"Мой запрос: {user_input}"}
            ]
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=body, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["result"]["alternatives"][0]["message"]["text"]
        except Exception as e:
            print(f"YandexGPT API error: {e}")
            return None

# Глобальный экземпляр клиента (будет инициализирован в app.py)
yandex_client: Optional[YandexGPTClient] = None

def init_yandex_gpt(api_key: str, folder_id: str):
    global yandex_client
    yandex_client = YandexGPTClient(api_key, folder_id)

def generate_with_ai(user_input: str, model_key: str, locale: str = 'ru') -> Optional[str]:
    if yandex_client is None:
        print("YandexGPT клиент не инициализирован")
        return None
    return yandex_client.generate_prompt(user_input, model_key, locale)
