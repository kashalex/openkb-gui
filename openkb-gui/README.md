# OpenKB GUI

Локальная система управления знаниями на базе OpenKB и LLM-провайдеров через LiteLLM.

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 🆕 Новые возможности v1.1.0

### 🌳 Wiki Browser
- **Tree View** — иерархическое дерево файлов с иконками
- **Поиск** — фильтрация файлов в реальном времени
- **Wikilinks навигация** — клик по `[[link]]` открывает файл
- **Markdown подсветка** — заголовки, ссылки, код
- **Backlinks** — просмотр входящих ссылок
- **История навигации** — кнопки назад/вперёд
- **Контекстное меню** — правый клик для действий

### 💡 Concepts Management
- **Таблица концептов** — сортируемый список с метаданными
- **Просмотр содержимого** — панель предпросмотра
- **Backlinks** — список ссылающихся страниц
- **Метаданные** — дата создания, изменения, слово-количество
- **Удаление** — с подтверждением

### 💬 Chat Sessions
- **Управление сессиями** — создание, переключение, удаление
- **Экспорт** — JSON, Markdown, TXT
- **Импорт** — загрузка сессий из файла
- **Автосохранение** — история сохраняется автоматически
- **История сообщений** — с временными метками

### 🎨 UI/UX
- **Переключатель темы** — Dark / Light / System
- **Статус-бар** — информация о workspace и API
- **Иконки вкладок** — визуальное обозначение
- **Горячие клавиши** — быстрые действия
- **Toast-уведомления** — всплывающие сообщения
- **Прогресс-бар** — визуальный индикатор сборки

## ⌨️ Горячие клавиши

| Сочетание | Действие |
|-----------|----------|
| `Ctrl+B` | Запуск Build |
| `Ctrl+S` | Сохранить настройки |
| `F5` | Обновить все вкладки |
| `Escape` | Остановить процесс |
| `Ctrl+1-7` | Переключение вкладок |

## Установка

### 1. Клонирование

```bash
git clone https://github.com/your-repo/openkb-gui.git
cd openkb-gui
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
python -m pip install -r requirements.txt
```

### 4. Настройка конфигурации

Скопируйте `.env.example` в `.env` и укажите ваш API ключ:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```
LLM_MODEL=zai/glm-4.5-flash
LLM_API_KEY=your_api_key_here
# или provider-specific ключи:
ZAI_API_KEY=your_zai_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
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
├── .env                     # Конфигурация
├── src/
│   ├── gui/
│   │   ├── main_window.py   # Главное окно
│   │   ├── wiki_tab.py      # Wiki Browser
│   │   ├── concepts_tab.py  # Concepts Management
│   │   ├── chat_tab.py      # Chat с сессиями
│   │   └── components.py    # UI компоненты
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
    │   ├── concepts/        # Извлечённые концепты
    │   ├── summaries/       # Сводки по документам
    │   ├── explorations/    # Результаты исследований
    │   └── AGENTS.md        # Конфигурация знаний
    ├── sessions/            # Сессии чата
    └── logs/                # Логи
```

## Использование

### 1. Настройка

Откройте вкладку **⚙️ Settings** и укажите:
- API Key (обязательно)
- Model (выберите из списка или введите вручную)
- Workspace Path (по умолчанию ./workspace)

Нажмите **💾 Save Settings**.

### 2. Добавление документов

Поместите ваши документы в папку `workspace/raw/`:
- PDF (текстовые и сканы)
- DOCX
- TXT
- Markdown

### 3. Компиляция базы знаний

Перейдите на вкладку **🔨 Build** и нажмите **Build**.

После завершения в папке `workspace/wiki/` появится скомпилированная база знаний:
- `concepts/` - автоматически извлечённые концепты
- `summaries/` - сводки по документам
- `explorations/` - результаты исследований
- `sources/` - исходные документы

### 4. Просмотр Wiki

Вкладка **📁 Wiki Browser** позволяет:
- Просматривать иерархию файлов wiki
- Искать по содержимому
- Переходить по wikilinks `[[Concept Name]]`
- Смотреть backlinks

### 5. Управление концептами

Вкладка **💡 Concepts** показывает:
- Список всех концептов
- Количество backlinks и слов
- Содержимое выбранного концепта
- Страницы, ссылающиеся на концепт

### 6. Диалог с базой знаний

Вкладка **💬 Chat** позволяет:
- Создавать и переключать сессии
- Задавать вопросы по базе знаний
- Видеть источники ответов
- Экспортировать историю

### 7. Диагностика

Вкладка **🏥 Health** позволяет запустить lint проверку для выявления:
- Orphan concepts (концепты без входящих ссылок)
- Broken links (битые ссылки)
- Stale pages (устаревшие страницы)

## Поддерживаемые модели

| Провайдер | Модели |
|-----------|--------|
| **Z.ai** | glm-4.5-flash, glm-4-plus, glm-4 |
| **OpenRouter** | deepseek-chat, claude-3.5-sonnet, gpt-4o-mini и др. |
| **Custom** | Любые OpenAI-compatible API |

## Требования

- Python 3.10+
- OpenKB (`pip install openkb`)
- CustomTkinter (`pip install customtkinter`)
- LiteLLM (`pip install litellm`)

## Troubleshooting

### Windows/venv: `customtkinter` установлен, но не импортируется

Используйте pip через тот же интерпретатор:

```bash
python -m pip install -r requirements.txt
python -m pip install customtkinter
```

### OpenKB not found

```bash
python -m pip install openkb
```

Без установленного OpenKB реальная сборка не запускается.

### API Key invalid

Проверьте правильность API ключа в `.env` файле.

## Changelog

### v1.1.0
- ✨ Новый Wiki Browser с tree view и wikilinks навигацией
- ✨ Полноценный Concepts Management
- ✨ Управление Chat Sessions с экспортом/импортом
- ✨ Переключатель темы (Dark/Light/System)
- ✨ Статус-бар с информацией
- ✨ Горячие клавиши
- ✨ Toast-уведомления
- ✨ Прогресс-бар для Build

### v1.0.0
- 🎉 Начальный релиз
- 7 вкладок GUI
- Интеграция с OpenKB
- Поддержка нескольких LLM провайдеров

## Лицензия

MIT
