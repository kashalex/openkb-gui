# OpenKB GUI

Локальная система управления знаниями на базе OpenKB и GLM-4.7-Flash.

## Установка

### 1. Клонирование / Распаковка

```bash
cd /path/to/openkb-gui
```

### 2. Создание виртуального окружения

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка конфигурации

Скопируйте `.env.example` в `.env` и укажите ваш API ключ:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```
OPENAI_API_KEY=your_api_key_here
```

## Запуск

```bash
python main.py
```

## Структура проекта

```
openkb-gui/
├── main.py                  # Точка входа
├── requirements.txt         # Зависимости
├── .env                     # Конфигурация (создаётся из .env.example)
├── src/
│   ├── gui/
│   │   └── main_window.py   # Главное окно с 7 вкладками
│   ├── services/
│   │   ├── config_service.py    # Управление настройками
│   │   ├── build_service.py     # Компиляция базы знаний
│   │   ├── watch_service.py     # Автоматическое отслеживание
│   │   ├── chat_service.py      # Интеллектуальный диалог
│   │   ├── wiki_service.py      # Работа с wiki
│   │   ├── lint_service.py      # Диагностика
│   │   └── session_service.py   # Управление сессиями
│   ├── models/
│   │   └── models.py        # Модели данных
│   └── utils/
│       └── helpers.py       # Вспомогательные функции
└── workspace/
    ├── raw/                 # Документы пользователя
    ├── wiki/                # Скомпилированная wiki
    ├── sessions/            # Сессии чата
    └── logs/                # Логи
```

## Использование

### 1. Настройка

Откройте вкладку **Settings** и укажите:
- API Key (обязательно)
- Workspace Path (по умолчанию ./workspace)

Нажмите **Save Settings**.

### 2. Добавление документов

Поместите ваши документы в папку `workspace/raw/`:
- PDF
- DOCX
- TXT
- Markdown

### 3. Компиляция базы знаний

Перейдите на вкладку **Build** и нажмите **Build**.

После завершения в папке `workspace/wiki/` появится скомпилированная база знаний:
- `concepts/` - автоматически извлечённые концепты
- `summaries/` - сводки по документам
- `explorations/` - результаты исследований

### 4. Просмотр Wiki

Вкладка **Wiki Browser** позволяет:
- Просматривать структуру wiki
- Читать markdown страницы
- Переходить по wikilinks

### 5. Диалог с базой знаний

Вкладка **Chat** позволяет задавать вопросы на основе скомпилированной wiki.

### 6. Диагностика

Вкладка **Health** позволяет запустить lint проверку для выявления:
- Orphan concepts
- Broken links
- Stale pages

## Требования

- Python 3.10+
- OpenKB (`pip install openkb`)
- CustomTkinter (`pip install customtkinter`)
- LiteLLM (`pip install litellm`)

## Troubleshooting

### OpenKB not found

```
pip install openkb
```

### CustomTkinter not found

```
pip install customtkinter
```

### API Key invalid

Проверьте правильность API ключа в `.env` файле.

## Лицензия

MIT
