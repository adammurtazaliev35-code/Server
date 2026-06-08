import sqlite3
import json
import os

DB_NAME = "database.db"

def get_db_connection():
    """Возвращает соединение с БД (с row_factory для удобства)"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создаёт все таблицы, если их нет, и заполняет начальными данными"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # --- Таблицы пользователей и сохранённых промптов (уже были) ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt_type TEXT,
                input_text TEXT,
                output_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # --- Новые таблицы для словаря ---
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                locale TEXT NOT NULL,
                key_name TEXT NOT NULL,
                phrase TEXT NOT NULL,
                UNIQUE(locale, key_name)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_key TEXT UNIQUE NOT NULL,
                rule_text TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                category_id TEXT UNIQUE NOT NULL,
                priority INTEGER NOT NULL,
                keywords TEXT NOT NULL   -- JSON-массив
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS category_localized (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id TEXT NOT NULL,
                locale TEXT NOT NULL,
                role TEXT NOT NULL,
                pos_phrases TEXT NOT NULL,  -- JSON-массив
                neg_phrases TEXT NOT NULL,  -- JSON-массив
                format_phrases TEXT NOT NULL, -- JSON-массив
                FOREIGN KEY (category_id) REFERENCES categories(category_id),
                UNIQUE(category_id, locale)
            )
        ''')
        
        # Если таблицы пустые – загружаем данные из резервного словаря (бывшего dictionary.js)
        cursor.execute("SELECT COUNT(*) FROM connectors")
        if cursor.fetchone()[0] == 0:
            _load_initial_dictionary_data(cursor)
        
        conn.commit()

def _load_initial_dictionary_data(cursor):
    """Заполняет таблицы начальными данными (аналог старого dictionary.js)"""
    # Коннекторы
    connectors_data = [
        ('ru', 'intro', 'Действуй как'),
        ('ru', 'task', 'Твоя главная задача:'),
        ('ru', 'style', 'В процессе работы'),
        ('ru', 'avoid', 'обязательно исключая'),
        ('ru', 'ending', 'Ответ предоставь, используя'),
        ('en', 'intro', 'Act as'),
        ('en', 'task', 'Your main task is to'),
        ('en', 'style', 'While working on this,'),
        ('en', 'avoid', 'strictly avoiding'),
        ('en', 'ending', 'Provide the output using')
    ]
    cursor.executemany(
        "INSERT INTO connectors (locale, key_name, phrase) VALUES (?, ?, ?)",
        connectors_data
    )
    
    # Правила для моделей
    models_rules_data = [
        ('gpt-4o', 'Пиши кратко, структурировано, соблюдай строгую логику и выделяй главное.'),
        ('claude-3.5-sonnet', 'Используй XML-подобную структуру для разделения мыслей, будь максимально детальным.'),
        ('gemini-2.0-pro', 'Делай упор на глубокие рассуждения и предлагай альтернативные пути решения.'),
        ('deepseek-v3', 'Используй технически точный язык и оптимизируй решение под максимальную производительность.'),
        ('default', 'Будь точным и следуй заданным инструкциям.')
    ]
    cursor.executemany(
        "INSERT INTO model_rules (model_key, rule_text) VALUES (?, ?)",
        models_rules_data
    )
    
    # Категории и локализации (сжатый пример – полную версию можно взять из старого dictionary.js)
    categories_data = [
        ('coding', 'gamedev', 50, '["игра","змейка","тетрис","game","unity","unreal","pygame","canvas","движок","snake","геймдев"]'),
        ('coding', 'backend', 40, '["бэкенд","сервер","api","sql","backend","database","node","python","питон","php","go","база данных"]'),
        ('coding', 'frontend', 35, '["фронтенд","react","vue","frontend","html","css","интерфейс","ui","ux","верстка"]'),
        ('creative', 'brainstorm', 30, '["идеи","придумай","креатив","ideas","brainstorm","концепт","генерировать"]'),
        ('creative', 'marketing', 25, '["маркетинг","продажи","бренд","реклама","marketing","ads","seo","копирайтинг"]'),
        ('general', 'improve', 1, '["улучши","перепиши","исправь","доработай","improve","rewrite","refine"]')
    ]
    cursor.executemany(
        "INSERT INTO categories (group_name, category_id, priority, keywords) VALUES (?, ?, ?, ?)",
        categories_data
    )
    
    # Локализованные данные (только ru и en для gamedev, остальные аналогично – для brevity показываю несколько)
    loc_data = [
        # gamedev ru
        ('gamedev', 'ru', 'ведущий разработчик игр',
         '["реализуя плавную игровую логику","оптимизируя цикл обработки кадров (Game Loop)","используя паттерны проектирования для игр","обеспечивая отзывчивое управление"]',
         '["утечки памяти","неэффективную отрисовку","жесткую зависимость логики от графики"]',
         '["полный, готовый к запуску код","инструкцию по управлению","комментарии к ключевым механикам"]'),
        # backend ru
        ('backend', 'ru', 'архитектор серверных решений',
         '["проектируя масштабируемую архитектуру","обеспечивая безопасность данных","соблюдая принципы RESTful"]',
         '["уязвимости к инъекциям","медленные запросы","хардкод настроек"]',
         '["структуру базы данных","код API эндпоинтов","схему валидации"]'),
        # improve ru
        ('improve', 'ru', 'профессиональный редактор',
         '["повышая ясность и лаконичность","исправляя стилистические неточности","улучшая структуру повествования"]',
         '["канцеляризмы","сложные и запутанные обороты","воду"]',
         '["финальный отшлифованный текст","краткое описание правок"]'),
        # можно добавить en версии аналогично...
    ]
    cursor.executemany(
        "INSERT INTO category_localized (category_id, locale, role, pos_phrases, neg_phrases, format_phrases) VALUES (?, ?, ?, ?, ?, ?)",
        loc_data
    )
