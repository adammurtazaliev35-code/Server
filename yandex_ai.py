import os
import requests
import json
import re
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
            # 1. Извлекаем инструкции из текста (то, что в кавычках или скобках)
            instructions = ""
            if use_instructions:
                # Находим всё, что в (...) или "..."
                found = re.findall(r'[\(\"\'](.*?)[\)\"\']', user_input)
                if found:
                    instructions = ", ".join(found)
                    # Удаляем инструкции из основного текста задачи, чтобы не дублировались
                    clean_task = re.sub(r'[\(\"\'].*?[\)\"\']', '', user_input).strip()
                else:
                    clean_task = user_input
            else:
                clean_task = user_input
    
            # 2. Очищаем задачу от "[Контекст модели]: ..."
            clean_task = re.sub(r'\[.*?\]', '', clean_task).strip()
    
            # 3. Формируем "Архитектурный" системный промпт
            system_prompt = (
                f"Ты — профессиональный инженер промптов. Твоя задача — создать идеальный промпт для модели {model_key}. "
                f"Используй следующий запрос пользователя: '{clean_task}'. "
                f"Если есть инструкции: '{instructions}', добавь их в структуру промпта. "
                "Ответ должен содержать: Роль ИИ, саму задачу, ограничения и требуемый формат ответа. "
                "Не используй пояснения от себя, выдай только готовый промпт."
            )
    
            body = {
                "modelUri": f"gpt://{self.folder_id}/{self.model}",
                "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": 500},
                "messages": [
                    {"role": "system", "text": system_prompt},
                    {"role": "user", "text": f"Задача: {clean_task}. Инструкции: {instructions}" if instructions else f"Задача: {clean_task}"}
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

def generate_with_ai(user_input: str, model_key: str, locale: str = 'ru', use_instructions: bool = False) -> Optional[str]:
    if yandex_client is None:
        print("YandexGPT клиент не инициализирован")
        return None
    return yandex_client.generate_prompt(user_input, model_key, locale, use_instructions)
