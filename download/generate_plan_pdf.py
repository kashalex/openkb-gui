#!/usr/bin/env python3
"""
План разработки системы OpenKB GUI
Генерация PDF документа с поэтапным планом внедрения модулей
"""

import sys
import os

# Setup paths
PDF_SKILL_DIR = "/home/z/my-project/skills/pdf"
_scripts = os.path.join(PDF_SKILL_DIR, "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# ============================================================================
# COLOR PALETTE (auto-generated)
# ============================================================================
ACCENT       = colors.HexColor('#197999')
TEXT_PRIMARY = colors.HexColor('#191b1c')
TEXT_MUTED   = colors.HexColor('#6e757a')
BG_SURFACE   = colors.HexColor('#dbe0e3')
BG_PAGE      = colors.HexColor('#edeeef')

TABLE_HEADER_COLOR = ACCENT
TABLE_HEADER_TEXT  = colors.white
TABLE_ROW_EVEN     = colors.white
TABLE_ROW_ODD      = BG_SURFACE

# ============================================================================
# FONT REGISTRATION
# ============================================================================
pdfmetrics.registerFont(TTFont('NotoSerifSC', '/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NotoSerifSCBold', '/usr/share/fonts/truetype/noto-serif-sc/NotoSerifSC-Bold.ttf'))

registerFontFamily('NotoSerifSC', normal='NotoSerifSC', bold='NotoSerifSCBold')

# ============================================================================
# DOCUMENT SETUP
# ============================================================================
OUTPUT_PATH = "/home/z/my-project/download/OpenKB_GUI_Plan.pdf"
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 2.0 * cm
RIGHT_MARGIN = 2.0 * cm
TOP_MARGIN = 2.0 * cm
BOTTOM_MARGIN = 2.0 * cm
AVAILABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

# ============================================================================
# STYLES
# ============================================================================
styles = getSampleStyleSheet()

# Title style
styles.add(ParagraphStyle(
    name='DocTitle',
    fontName='NotoSerifSC',
    fontSize=28,
    leading=36,
    alignment=TA_CENTER,
    textColor=ACCENT,
    spaceAfter=20,
))

# Subtitle
styles.add(ParagraphStyle(
    name='DocSubtitle',
    fontName='NotoSerifSC',
    fontSize=14,
    leading=20,
    alignment=TA_CENTER,
    textColor=TEXT_MUTED,
    spaceAfter=40,
))

# H1
styles.add(ParagraphStyle(
    name='H1',
    fontName='NotoSerifSC',
    fontSize=18,
    leading=26,
    alignment=TA_LEFT,
    textColor=ACCENT,
    spaceBefore=24,
    spaceAfter=12,
))

# H2
styles.add(ParagraphStyle(
    name='H2',
    fontName='NotoSerifSC',
    fontSize=14,
    leading=20,
    alignment=TA_LEFT,
    textColor=TEXT_PRIMARY,
    spaceBefore=18,
    spaceAfter=8,
))

# H3
styles.add(ParagraphStyle(
    name='H3',
    fontName='NotoSerifSC',
    fontSize=12,
    leading=18,
    alignment=TA_LEFT,
    textColor=TEXT_PRIMARY,
    spaceBefore=12,
    spaceAfter=6,
))

# Body
styles.add(ParagraphStyle(
    name='BodyRU',
    fontName='NotoSerifSC',
    fontSize=11,
    leading=18,
    alignment=TA_JUSTIFY,
    textColor=TEXT_PRIMARY,
    spaceBefore=0,
    spaceAfter=8,
    wordWrap='CJK',
))

# Bullet
styles.add(ParagraphStyle(
    name='BulletRU',
    fontName='NotoSerifSC',
    fontSize=11,
    leading=16,
    alignment=TA_LEFT,
    textColor=TEXT_PRIMARY,
    leftIndent=20,
    spaceBefore=2,
    spaceAfter=2,
    wordWrap='CJK',
))

# Table header
styles.add(ParagraphStyle(
    name='TableHeader',
    fontName='NotoSerifSC',
    fontSize=10,
    leading=14,
    alignment=TA_CENTER,
    textColor=colors.white,
))

# Table cell
styles.add(ParagraphStyle(
    name='TableCell',
    fontName='NotoSerifSC',
    fontSize=9,
    leading=13,
    alignment=TA_LEFT,
    textColor=TEXT_PRIMARY,
    wordWrap='CJK',
))

# ============================================================================
# CONTENT DATA
# ============================================================================

def create_phase_table(phase_num, title, duration, tasks, deliverables, dependencies):
    """Create a phase information table."""
    data = [
        [Paragraph('<b>Этап</b>', styles['TableHeader']),
         Paragraph(f'<b>{phase_num}: {title}</b>', styles['TableHeader'])],
        [Paragraph('<b>Длительность</b>', styles['TableCell']),
         Paragraph(duration, styles['TableCell'])],
        [Paragraph('<b>Зависимости</b>', styles['TableCell']),
         Paragraph(dependencies, styles['TableCell'])],
    ]
    
    col_widths = [AVAILABLE_WIDTH * 0.25, AVAILABLE_WIDTH * 0.75]
    table = Table(data, colWidths=col_widths, hAlign='CENTER')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table

def build_document():
    """Build the complete PDF document."""
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
    )
    
    story = []
    
    # =========================================================================
    # COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 80))
    story.append(Paragraph('ПЛАН РАЗРАБОТКИ', styles['DocTitle']))
    story.append(Spacer(1, 10))
    story.append(Paragraph('Локальная система управления знаниями<br/>на базе OpenKB и GLM-4.7-Flash', styles['DocSubtitle']))
    story.append(Spacer(1, 60))
    
    # Info table
    info_data = [
        [Paragraph('<b>Проект</b>', styles['TableCell']),
         Paragraph('OpenKB GUI — Desktop-приложение для управления базой знаний', styles['TableCell'])],
        [Paragraph('<b>Тип</b>', styles['TableCell']),
         Paragraph('Desktop Application (Python + CustomTkinter)', styles['TableCell'])],
        [Paragraph('<b>Язык</b>', styles['TableCell']),
         Paragraph('Python 3.10+', styles['TableCell'])],
        [Paragraph('<b>GUI</b>', styles['TableCell']),
         Paragraph('CustomTkinter', styles['TableCell'])],
        [Paragraph('<b>Количество этапов</b>', styles['TableCell']),
         Paragraph('7 этапов', styles['TableCell'])],
    ]
    
    info_table = Table(info_data, colWidths=[AVAILABLE_WIDTH * 0.35, AVAILABLE_WIDTH * 0.65], hAlign='CENTER')
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), BG_SURFACE),
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    
    story.append(PageBreak())
    
    # =========================================================================
    # TABLE OF CONTENTS
    # =========================================================================
    story.append(Paragraph('Содержание', styles['H1']))
    story.append(Spacer(1, 12))
    
    toc_items = [
        ('1. Обзор проекта', 'Цели и задачи системы'),
        ('2. Архитектурные принципы', 'Философия OpenKB, ключевые отличия от RAG'),
        ('3. Этап 1: Инфраструктура', 'Подготовка окружения и базовая структура проекта'),
        ('4. Этап 2: Конфигурация', 'Сервисы настроек и управление workspace'),
        ('5. Этап 3: Build Service', 'Компиляция базы знаний и интеграция OpenKB'),
        ('6. Этап 4: Watch Mode', 'Автоматическое отслеживание изменений'),
        ('7. Этап 5: Wiki Browser', 'Просмотр и навигация по wiki'),
        ('8. Этап 6: Chat Module', 'Интеллектуальный диалог с базой знаний'),
        ('9. Этап 7: Health & Lint', 'Диагностика и мониторинг состояния'),
        ('10. Сводная таблица этапов', 'Хронология и зависимости'),
        ('11. Риски и митигация', 'Потенциальные проблемы и решения'),
        ('12. Заключение', 'Итоги и следующие шаги'),
    ]
    
    for title, desc in toc_items:
        story.append(Paragraph(f'<b>{title}</b> — {desc}', styles['BodyRU']))
    
    story.append(PageBreak())
    
    # =========================================================================
    # SECTION 1: PROJECT OVERVIEW
    # =========================================================================
    story.append(Paragraph('1. Обзор проекта', styles['H1']))
    
    story.append(Paragraph('1.1 Назначение системы', styles['H2']))
    story.append(Paragraph(
        'Проект представляет собой desktop-приложение на Python, которое служит графической оболочкой (GUI) '
        'для системы OpenKB. Основная цель — создание инструмента для построения и сопровождения локальной '
        'компилируемой базы знаний, работающей по архитектуре OpenKB. Система предназначена для '
        'преобразования неструктурированных документов в interlinked markdown wiki с автоматическим '
        'синтезом concept pages, summaries и поддержкой knowledge accumulation.',
        styles['BodyRU']
    ))
    
    story.append(Paragraph('1.2 Ключевые функции', styles['H2']))
    functions = [
        'Импорт локальных документов (PDF, DOCX, TXT, Markdown)',
        'Компиляция документов в interlinked markdown wiki',
        'Автоматический синтез concepts pages и summaries',
        'Накопление знаний с расширением cross-links',
        'Интеллектуальный диалог поверх compiled wiki',
        'Watch mode для автоматического обновления',
        'Lint/health checking для диагностики состояния',
        'Интеграция с Obsidian для просмотра wiki',
    ]
    for f in functions:
        story.append(Paragraph(f'• {f}', styles['BulletRU']))
    
    story.append(Paragraph('1.3 Технический стек', styles['H2']))
    
    stack_data = [
        [Paragraph('<b>Компонент</b>', styles['TableHeader']),
         Paragraph('<b>Технология</b>', styles['TableHeader']),
         Paragraph('<b>Назначение</b>', styles['TableHeader'])],
        [Paragraph('Язык', styles['TableCell']),
         Paragraph('Python 3.10+', styles['TableCell']),
         Paragraph('Основной язык разработки', styles['TableCell'])],
        [Paragraph('GUI', styles['TableCell']),
         Paragraph('CustomTkinter', styles['TableCell']),
         Paragraph('Графический интерфейс пользователя', styles['TableCell'])],
        [Paragraph('Knowledge Engine', styles['TableCell']),
         Paragraph('OpenKB', styles['TableCell']),
         Paragraph('Компиляция базы знаний', styles['TableCell'])],
        [Paragraph('LLM Layer', styles['TableCell']),
         Paragraph('LiteLLM', styles['TableCell']),
         Paragraph('Унифицированный API к LLM', styles['TableCell'])],
        [Paragraph('Модель', styles['TableCell']),
         Paragraph('GLM-4.7-Flash', styles['TableCell']),
         Paragraph('Основная AI-модель', styles['TableCell'])],
        [Paragraph('Markdown', styles['TableCell']),
         Paragraph('tkinterweb', styles['TableCell']),
         Paragraph('Рендеринг markdown в GUI', styles['TableCell'])],
        [Paragraph('Packaging', styles['TableCell']),
         Paragraph('PyInstaller', styles['TableCell']),
         Paragraph('Сборка standalone executable', styles['TableCell'])],
    ]
    
    stack_table = Table(stack_data, colWidths=[AVAILABLE_WIDTH * 0.20, AVAILABLE_WIDTH * 0.30, AVAILABLE_WIDTH * 0.50], hAlign='CENTER')
    stack_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 5), (-1, 5), colors.white),
        ('BACKGROUND', (0, 6), (-1, 6), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 7), (-1, 7), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(stack_table)
    story.append(Spacer(1, 18))
    
    # =========================================================================
    # SECTION 2: ARCHITECTURE PRINCIPLES
    # =========================================================================
    story.append(Paragraph('2. Архитектурные принципы', styles['H1']))
    
    story.append(Paragraph('2.1 Философия OpenKB', styles['H2']))
    story.append(Paragraph(
        'OpenKB используется как knowledge compiler, evolving wiki system, knowledge graph over markdown '
        'и long-term accumulated knowledge storage. Это означает, что система не просто индексирует '
        'документы, а компилирует их в связную структуру знаний с автоматическим созданием связей '
        'между концептами. Каждая страница wiki может ссылаться на другие через wikilinks, образуя '
        'граф знаний, который развивается с каждым новым документом.',
        styles['BodyRU']
    ))
    
    story.append(Paragraph('2.2 Ключевые отличия от классического RAG', styles['H2']))
    story.append(Paragraph(
        'Система принципиально отличается от классических RAG-решений. Вместо векторных баз данных, '
        'embeddings retrieval и chunk-based поиска используется подход на основе компилированных wiki pages. '
        'Это обеспечивает более точные ответы за счёт работы с целостными концептами, а не фрагментами текста.',
        styles['BodyRU']
    ))
    
    # Comparison table
    compare_data = [
        [Paragraph('<b>Аспект</b>', styles['TableHeader']),
         Paragraph('<b>Классический RAG</b>', styles['TableHeader']),
         Paragraph('<b>OpenKB подход</b>', styles['TableHeader'])],
        [Paragraph('Хранение', styles['TableCell']),
         Paragraph('Vector database', styles['TableCell']),
         Paragraph('Compiled markdown wiki', styles['TableCell'])],
        [Paragraph('Поиск', styles['TableCell']),
         Paragraph('Embeddings similarity', styles['TableCell']),
         Paragraph('Wiki navigation + concepts', styles['TableCell'])],
        [Paragraph('Структура', styles['TableCell']),
         Paragraph('Chunks без связей', styles['TableCell']),
         Paragraph('Interlinked knowledge graph', styles['TableCell'])],
        [Paragraph('Обновление', styles['TableCell']),
         Paragraph('Re-index embeddings', styles['TableCell']),
         Paragraph('Incremental wiki rebuild', styles['TableCell'])],
        [Paragraph('Накопление', styles['TableCell']),
         Paragraph('Добавление chunks', styles['TableCell']),
         Paragraph('Knowledge accumulation', styles['TableCell'])],
    ]
    
    compare_table = Table(compare_data, colWidths=[AVAILABLE_WIDTH * 0.25, AVAILABLE_WIDTH * 0.375, AVAILABLE_WIDTH * 0.375], hAlign='CENTER')
    compare_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 5), (-1, 5), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(compare_table)
    story.append(Spacer(1, 18))
    
    story.append(Paragraph('2.3 Структура workspace', styles['H2']))
    story.append(Paragraph(
        'Workspace организован по нативной структуре OpenKB с чётким разделением сырых документов '
        'и скомпилированной wiki. Папка raw/ содержит исходные документы пользователя, которые '
        'подвергаются обработке. Папка wiki/ содержит сгенерированные страницы: concepts/ для '
        'автоматически синтезированных концептов, summaries/ для обобщений, explorations/ для '
        'результатов исследований, reports/ для отчётов и sources/ для исходных материалов.',
        styles['BodyRU']
    ))
    
    # =========================================================================
    # PHASES
    # =========================================================================
    
    # PHASE 1
    story.append(PageBreak())
    story.append(Paragraph('3. Этап 1: Инфраструктура', styles['H1']))
    story.append(create_phase_table('1', 'Инфраструктура и базовая структура', '3-4 дня',
        'Создание структуры проекта, настройка окружения',
        'Структура проекта, requirements.txt, базовый GUI',
        'Нет'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('3.1 Задачи', styles['H2']))
    tasks1 = [
        'Создание файловой структуры проекта согласно ТЗ',
        'Настройка виртуального окружения Python 3.10+',
        'Установка зависимостей: openkb, customtkinter, litellm, python-dotenv, tkinterweb, watchdog',
        'Создание базового main.py с точкой входа',
        'Разработка main_window.py с главным окном CustomTkinter',
        'Реализация системы вкладок (7 вкладок по ТЗ)',
        'Настройка .env файла с параметрами LLM',
    ]
    for t in tasks1:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    story.append(Paragraph('3.2 Результаты', styles['H2']))
    story.append(Paragraph(
        'После завершения этапа будет создана базовая структура проекта с главным окном приложения, '
        'системой вкладок и настроенным окружением. Приложение запускается и отображает пустой интерфейс '
        'с placeholder-контентом на каждой вкладке.',
        styles['BodyRU']
    ))
    
    # PHASE 2
    story.append(Paragraph('4. Этап 2: Конфигурация', styles['H1']))
    story.append(create_phase_table('2', 'Сервисы конфигурации', '2-3 дня',
        'Разработка config_service.py и управление workspace',
        'Загрузка настроек, UI вкладки Settings',
        'Этап 1'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('4.1 Задачи', styles['H2']))
    tasks2 = [
        'Разработка config_service.py для загрузки/сохранения настроек из .env',
        'Реализация UI вкладки Settings (API Key, Base URL, Model, workspace paths)',
        'Создание логики валидации API ключей',
        'Реализация выбора и создания workspace директории',
        'Настройка PAGEINDEX_API_KEY для OCR',
        'Сохранение состояния настроек между сессиями',
    ]
    for t in tasks2:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    story.append(Paragraph('4.2 Результаты', styles['H2']))
    story.append(Paragraph(
        'Пользователь может настраивать все параметры системы через UI вкладки Settings. '
        'Настройки сохраняются в .env файл и загружаются при старте приложения. '
        'Валидация API ключей обеспечивает информативные сообщения об ошибках.',
        styles['BodyRU']
    ))
    
    # PHASE 3
    story.append(PageBreak())
    story.append(Paragraph('5. Этап 3: Build Service', styles['H1']))
    story.append(create_phase_table('3', 'Build Service — Компиляция базы знаний', '4-5 дней',
        'Интеграция OpenKB, subprocess management, UI Build tab',
        'Запуск openkb build, логи в реальном времени',
        'Этапы 1, 2'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('5.1 Задачи', styles['H2']))
    tasks3 = [
        'Разработка build_service.py для запуска openkb build через subprocess.Popen',
        'Реализация queue-based stdout reading для логов в реальном времени',
        'Создание UI вкладки Build (Build button, Watch button, Stop button, logs, progress)',
        'Реализация thread-safe GUI updates через after()',
        'Обработка документов: PDF, PDF scans, DOCX, TXT, Markdown',
        'Интеграция PageIndex для длинных документов (>20 страниц)',
        'Fallback mode при отсутствии PAGEINDEX_API_KEY',
    ]
    for t in tasks3:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    story.append(Paragraph('5.2 Ключевые технические решения', styles['H2']))
    story.append(Paragraph(
        'Build процесс выполняется в отдельном потоке через subprocess.Popen, что предотвращает '
        'зависание GUI. Вывод процесса читается через queue и отображается в текстовом виджете '
        'в реальном времени. Кнопка Stop позволяет прервать процесс компиляции. Прогресс-индикатор '
        'отображает текущий статус (idle/building/watching/linting).',
        styles['BodyRU']
    ))
    
    # PHASE 4
    story.append(Paragraph('6. Этап 4: Watch Mode', styles['H1']))
    story.append(create_phase_table('4', 'Watch Mode — Автоматическое отслеживание', '2-3 дня',
        'Автоматическое обновление wiki при изменениях',
        'Watch_service.py, интеграция с Build tab',
        'Этап 3'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('6.1 Задачи', styles['H2']))
    tasks4 = [
        'Разработка watch_service.py для запуска openkb watch',
        'Мониторинг папки raw/ на наличие новых документов',
        'Автоматическое обновление concepts, summaries, knowledge graph при изменениях',
        'Интеграция с UI вкладки Build (Watch button, status indicator)',
        'Обработка ошибок watch process',
        'Корректная остановка watch mode',
    ]
    for t in tasks4:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    # PHASE 5
    story.append(PageBreak())
    story.append(Paragraph('7. Этап 5: Wiki Browser', styles['H1']))
    story.append(create_phase_table('5', 'Wiki Browser — Просмотр wiki', '4-5 дней',
        'Tree view, markdown preview, wikilinks navigation',
        'Полноценный браузер wiki-страниц',
        'Этапы 1, 3'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('7.1 Задачи', styles['H2']))
    tasks5 = [
        'Разработка wiki_service.py для работы с wiki-файлами',
        'Создание UI вкладки Wiki Browser (tree view, markdown preview)',
        'Интеграция tkinterweb для рендеринга markdown',
        'Реализация переходов по wikilinks [[Concept Name]]',
        'Отображение concepts pages и summaries',
        'Реализация поиска по wiki',
        'Отображение AGENTS.md в отдельном редакторе',
    ]
    for t in tasks5:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    story.append(Paragraph('7.2 Результаты', styles['H2']))
    story.append(Paragraph(
        'Пользователь получает полноценный браузер wiki с древовидной структурой файлов, '
        'предпросмотром markdown и навигацией по wikilinks. Все сгенерированные страницы '
        '(concepts, summaries, explorations) доступны для просмотра.',
        styles['BodyRU']
    ))
    
    # PHASE 6
    story.append(Paragraph('8. Этап 6: Chat Module', styles['H1']))
    story.append(create_phase_table('6', 'Chat Module — Интеллектуальный диалог', '5-6 дней',
        'Чат поверх compiled wiki, не vector RAG',
        'Chat_service.py, sessions management, UI Chat tab',
        'Этапы 2, 3, 5'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('8.1 Задачи', styles['H2']))
    tasks6 = [
        'Разработка chat_service.py для работы с LLM через LiteLLM',
        'Реализация reasoning over compiled wiki (не vector RAG)',
        'Создание UI вкладки Chat (sessions panel, message history, input, sources)',
        'Разработка session_service.py для persistent sessions',
        'Отображение source pages, concepts, wiki pages в ответах',
        'Сохранение/загрузка/удаление/экспорт chat sessions',
        'Сохранение explorations (результаты исследований)',
    ]
    for t in tasks6:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    story.append(Paragraph('8.2 Архитектура чата', styles['H2']))
    story.append(Paragraph(
        'Чат работает поверх compiled wiki, используя reasoning over wiki structure. '
        'Ответы формируются на основе concepts pages, summaries, wiki links и knowledge graph. '
        'Источники ответов (source pages, concepts, wiki pages) отображаются в sources panel. '
        'Сессии сохраняются в папку sessions/ в формате JSON.',
        styles['BodyRU']
    ))
    
    # PHASE 7
    story.append(PageBreak())
    story.append(Paragraph('9. Этап 7: Health & Lint', styles['H1']))
    story.append(create_phase_table('7', 'Health & Lint — Диагностика', '2-3 дня',
        'Интеграция openkb lint, UI Health tab',
        'Отчёты о состоянии wiki, broken links detection',
        'Этапы 3, 5'))
    story.append(Spacer(1, 12))
    
    story.append(Paragraph('9.1 Задачи', styles['H2']))
    tasks7 = [
        'Разработка lint_service.py для запуска openkb lint',
        'Создание UI вкладки Health (lint reports, stale pages, warnings)',
        'Отображение orphan concepts, stale pages, contradictions',
        'Обнаружение broken links и compilation warnings',
        'Интеграция с AGENTS.md editor (редактирование конфигурации)',
        'Кнопка Open in Obsidian для внешнего просмотра',
    ]
    for t in tasks7:
        story.append(Paragraph(f'• {t}', styles['BulletRU']))
    
    # =========================================================================
    # SUMMARY TABLE
    # =========================================================================
    story.append(Paragraph('10. Сводная таблица этапов', styles['H1']))
    
    summary_data = [
        [Paragraph('<b>Этап</b>', styles['TableHeader']),
         Paragraph('<b>Название</b>', styles['TableHeader']),
         Paragraph('<b>Длительность</b>', styles['TableHeader']),
         Paragraph('<b>Зависимости</b>', styles['TableHeader'])],
        [Paragraph('1', styles['TableCell']),
         Paragraph('Инфраструктура', styles['TableCell']),
         Paragraph('3-4 дня', styles['TableCell']),
         Paragraph('—', styles['TableCell'])],
        [Paragraph('2', styles['TableCell']),
         Paragraph('Конфигурация', styles['TableCell']),
         Paragraph('2-3 дня', styles['TableCell']),
         Paragraph('Этап 1', styles['TableCell'])],
        [Paragraph('3', styles['TableCell']),
         Paragraph('Build Service', styles['TableCell']),
         Paragraph('4-5 дней', styles['TableCell']),
         Paragraph('Этапы 1, 2', styles['TableCell'])],
        [Paragraph('4', styles['TableCell']),
         Paragraph('Watch Mode', styles['TableCell']),
         Paragraph('2-3 дня', styles['TableCell']),
         Paragraph('Этап 3', styles['TableCell'])],
        [Paragraph('5', styles['TableCell']),
         Paragraph('Wiki Browser', styles['TableCell']),
         Paragraph('4-5 дней', styles['TableCell']),
         Paragraph('Этапы 1, 3', styles['TableCell'])],
        [Paragraph('6', styles['TableCell']),
         Paragraph('Chat Module', styles['TableCell']),
         Paragraph('5-6 дней', styles['TableCell']),
         Paragraph('Этапы 2, 3, 5', styles['TableCell'])],
        [Paragraph('7', styles['TableCell']),
         Paragraph('Health & Lint', styles['TableCell']),
         Paragraph('2-3 дня', styles['TableCell']),
         Paragraph('Этапы 3, 5', styles['TableCell'])],
    ]
    
    summary_table = Table(summary_data, colWidths=[AVAILABLE_WIDTH * 0.10, AVAILABLE_WIDTH * 0.35, AVAILABLE_WIDTH * 0.25, AVAILABLE_WIDTH * 0.30], hAlign='CENTER')
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 5), (-1, 5), colors.white),
        ('BACKGROUND', (0, 6), (-1, 6), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 7), (-1, 7), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))
    
    story.append(Paragraph(
        '<b>Общая длительность проекта:</b> 22-29 рабочих дней (при последовательном выполнении). '
        'Возможно сокращение за счёт параллельного выполнения независимых этапов (например, Этап 4 и Этап 5 '
        'могут разрабатываться параллельно после завершения Этапа 3).',
        styles['BodyRU']
    ))
    
    # =========================================================================
    # RISKS
    # =========================================================================
    story.append(Paragraph('11. Риски и митигация', styles['H1']))
    
    risks_data = [
        [Paragraph('<b>Риск</b>', styles['TableHeader']),
         Paragraph('<b>Вероятность</b>', styles['TableHeader']),
         Paragraph('<b>Влияние</b>', styles['TableHeader']),
         Paragraph('<b>Митигация</b>', styles['TableHeader'])],
        [Paragraph('OpenKB API изменения', styles['TableCell']),
         Paragraph('Средняя', styles['TableCell']),
         Paragraph('Высокое', styles['TableCell']),
         Paragraph('Абстракция через build_service', styles['TableCell'])],
        [Paragraph('GUI зависание при build', styles['TableCell']),
         Paragraph('Высокая', styles['TableCell']),
         Paragraph('Среднее', styles['TableCell']),
         Paragraph('subprocess + threading + after()', styles['TableCell'])],
        [Paragraph('OCR fallback при отсутствии API key', styles['TableCell']),
         Paragraph('Средняя', styles['TableCell']),
         Paragraph('Низкое', styles['TableCell']),
         Paragraph('Предупреждение пользователя', styles['TableCell'])],
        [Paragraph('Проблемы совместимости с Obsidian', styles['TableCell']),
         Paragraph('Низкая', styles['TableCell']),
         Paragraph('Среднее', styles['TableCell']),
         Paragraph('Тестирование экспорта', styles['TableCell'])],
        [Paragraph('Ошибки API LLM', styles['TableCell']),
         Paragraph('Средняя', styles['TableCell']),
         Paragraph('Высокое', styles['TableCell']),
         Paragraph('Retry logic + graceful degradation', styles['TableCell'])],
    ]
    
    risks_table = Table(risks_data, colWidths=[AVAILABLE_WIDTH * 0.30, AVAILABLE_WIDTH * 0.18, AVAILABLE_WIDTH * 0.17, AVAILABLE_WIDTH * 0.35], hAlign='CENTER')
    risks_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 1), (-1, 1), colors.white),
        ('BACKGROUND', (0, 2), (-1, 2), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 3), (-1, 3), colors.white),
        ('BACKGROUND', (0, 4), (-1, 4), TABLE_ROW_ODD),
        ('BACKGROUND', (0, 5), (-1, 5), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, TEXT_MUTED),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(risks_table)
    story.append(Spacer(1, 18))
    
    # =========================================================================
    # CONCLUSION
    # =========================================================================
    story.append(Paragraph('12. Заключение', styles['H1']))
    
    story.append(Paragraph(
        'План разработки охватывает все ключевые аспекты создания desktop-приложения для системы '
        'управления знаниями на базе OpenKB. Поэтапный подход позволяет контролировать прогресс и '
        'обеспечивает возможность раннего тестирования каждого модуля. Критически важным является '
        'правильная реализация Build Service (Этап 3), который является ядром всей системы.',
        styles['BodyRU']
    ))
    
    story.append(Paragraph(
        'После завершения всех этапов система будет представлять собой полнофункциональное '
        'desktop-приложение с возможностью импорта документов, компиляции базы знаний, '
        'интеллектуального диалога и диагностики состояния. Готовое приложение может быть '
        'упаковано в standalone executable через PyInstaller для распространения.',
        styles['BodyRU']
    ))
    
    # Build document
    doc.build(story)
    print(f"PDF успешно создан: {OUTPUT_PATH}")
    return OUTPUT_PATH

if __name__ == "__main__":
    build_document()
