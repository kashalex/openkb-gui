"""
Wiki Service - Работа с wiki файлами и навигация
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WikiPage:
    """Страница wiki"""
    path: Path
    title: str
    content: str
    wikilinks: list[str]
    backlinks: list[str]
    modified_time: datetime
    word_count: int
    category: str  # concepts, summaries, explorations, etc.
    
    @property
    def relative_path(self) -> str:
        return str(self.path.relative_to(self.path.parents[2]))  # workspace/wiki/...


class WikiService:
    """Сервис работы с wiki"""
    
    def __init__(self, wiki_path: str):
        """
        Инициализация wiki сервиса
        
        Args:
            wiki_path: Путь к wiki директории
        """
        self.wiki_path = Path(wiki_path).resolve()
        
        # Кэш backlinks
        self._backlinks_cache: dict[str, list[str]] = {}
        
        logger.info(f"WikiService инициализирован для: {self.wiki_path}")
    
    def get_tree(self) -> dict:
        """
        Получение дерева файлов wiki
        
        Returns:
            dict: Дерево файлов
        """
        tree = {
            "name": "wiki",
            "type": "directory",
            "children": []
        }
        
        if not self.wiki_path.exists():
            return tree
        
        # Определяем категории
        categories = {
            "concepts": {"name": "Concepts", "children": []},
            "summaries": {"name": "Summaries", "children": []},
            "explorations": {"name": "Explorations", "children": []},
            "reports": {"name": "Reports", "children": []},
            "sources": {"name": "Sources", "children": []},
        }
        
        # Корневые файлы
        root_files = []
        
        for item in self.wiki_path.iterdir():
            if item.is_file() and item.suffix == ".md":
                root_files.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.wiki_path)),
                    "type": "file"
                })
            elif item.is_dir() and item.name in categories:
                for md_file in item.glob("*.md"):
                    categories[item.name]["children"].append({
                        "name": md_file.stem,
                        "path": str(md_file.relative_to(self.wiki_path)),
                        "type": "file"
                    })
        
        tree["children"] = [
            {"name": cat_name, "type": "directory", "children": cat_data["children"]}
            for cat_name, cat_data in categories.items()
            if cat_data["children"]
        ]
        
        if root_files:
            tree["children"].insert(0, {
                "name": "Root Files",
                "type": "directory",
                "children": root_files
            })
        
        return tree
    
    def get_page(self, relative_path: str) -> Optional[WikiPage]:
        """
        Получение страницы wiki
        
        Args:
            relative_path: Относительный путь к файлу
        
        Returns:
            WikiPage: Страница wiki или None
        """
        full_path = self.wiki_path / relative_path
        
        if not full_path.exists() or not full_path.is_file():
            return None
        
        try:
            content = full_path.read_text(encoding="utf-8")
            
            # Извлекаем wikilinks
            wikilinks = self._extract_wikilinks(content)
            
            # Определяем категорию
            category = self._get_category(full_path)
            
            # Получаем backlinks
            backlinks = self.get_backlinks(full_path.stem)
            
            # Статистика
            stat = full_path.stat()
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            word_count = len(content.split())
            
            # Заголовок
            title = self._extract_title(content) or full_path.stem
            
            return WikiPage(
                path=full_path,
                title=title,
                content=content,
                wikilinks=wikilinks,
                backlinks=backlinks,
                modified_time=modified_time,
                word_count=word_count,
                category=category
            )
            
        except Exception as e:
            logger.error(f"Ошибка чтения страницы {relative_path}: {e}")
            return None
    
    def _extract_wikilinks(self, content: str) -> list[str]:
        """Извлечение wikilinks из контента"""
        pattern = r'\[\[([^\]]+)\]\]'
        return list(set(re.findall(pattern, content)))
    
    def _extract_title(self, content: str) -> Optional[str]:
        """Извлечение заголовка из контента"""
        lines = content.strip().split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return None
    
    def _get_category(self, path: Path) -> str:
        """Определение категории страницы"""
        relative = path.relative_to(self.wiki_path)
        if len(relative.parts) > 1:
            return relative.parts[0]
        return "root"
    
    def get_backlinks(self, page_name: str) -> list[str]:
        """
        Получение backlinks для страницы
        
        Args:
            page_name: Имя страницы (без .md)
        
        Returns:
            list[str]: Список страниц, ссылающихся на данную
        """
        page_name_lower = page_name.lower()
        
        # Проверяем кэш
        if page_name_lower in self._backlinks_cache:
            return self._backlinks_cache[page_name_lower]
        
        backlinks = []
        
        # Ищем ссылки во всех файлах
        for md_file in self.wiki_path.rglob("*.md"):
            if md_file.stem.lower() == page_name_lower:
                continue
            
            try:
                content = md_file.read_text(encoding="utf-8")
                links = self._extract_wikilinks(content)
                
                if any(link.lower() == page_name_lower for link in links):
                    backlinks.append(str(md_file.relative_to(self.wiki_path)))
            except Exception:
                continue
        
        self._backlinks_cache[page_name_lower] = backlinks
        return backlinks
    
    def clear_cache(self):
        """Очистка кэша backlinks"""
        self._backlinks_cache.clear()
    
    def search(self, query: str) -> list[dict]:
        """
        Поиск по wiki
        
        Args:
            query: Поисковый запрос
        
        Returns:
            list[dict]: Результаты поиска
        """
        results = []
        query_lower = query.lower()
        
        for md_file in self.wiki_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                content_lower = content.lower()
                
                if query_lower in content_lower:
                    # Находим контекст
                    idx = content_lower.find(query_lower)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 50)
                    context = content[start:end]
                    
                    results.append({
                        "path": str(md_file.relative_to(self.wiki_path)),
                        "title": self._extract_title(content) or md_file.stem,
                        "context": context,
                        "category": self._get_category(md_file),
                    })
            except Exception:
                continue
        
        return results
    
    def list_concepts(self) -> list[dict]:
        """Список всех concepts"""
        concepts_path = self.wiki_path / "concepts"
        
        if not concepts_path.exists():
            return []
        
        concepts = []
        for md_file in concepts_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                concepts.append({
                    "name": md_file.stem,
                    "path": str(md_file.relative_to(self.wiki_path)),
                    "title": self._extract_title(content) or md_file.stem,
                    "word_count": len(content.split()),
                    "backlinks_count": len(self.get_backlinks(md_file.stem)),
                })
            except Exception:
                continue
        
        return concepts
    
    def list_summaries(self) -> list[dict]:
        """Список всех summaries"""
        summaries_path = self.wiki_path / "summaries"
        
        if not summaries_path.exists():
            return []
        
        summaries = []
        for md_file in summaries_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                summaries.append({
                    "name": md_file.stem,
                    "path": str(md_file.relative_to(self.wiki_path)),
                    "title": self._extract_title(content) or md_file.stem,
                    "word_count": len(content.split()),
                })
            except Exception:
                continue
        
        return summaries
    
    def get_agents_content(self) -> Optional[str]:
        """Получение содержимого AGENTS.md"""
        agents_path = self.wiki_path / "AGENTS.md"
        
        if not agents_path.exists():
            return None
        
        return agents_path.read_text(encoding="utf-8")
    
    def save_agents_content(self, content: str) -> bool:
        """Сохранение AGENTS.md"""
        agents_path = self.wiki_path / "AGENTS.md"
        
        try:
            agents_path.write_text(content, encoding="utf-8")
            logger.info("AGENTS.md сохранён")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения AGENTS.md: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """Статистика wiki"""
        stats = {
            "total_pages": 0,
            "concepts": 0,
            "summaries": 0,
            "explorations": 0,
            "reports": 0,
            "sources": 0,
            "total_words": 0,
            "total_links": 0,
        }
        
        if not self.wiki_path.exists():
            return stats
        
        for md_file in self.wiki_path.rglob("*.md"):
            stats["total_pages"] += 1
            
            # Категория
            category = self._get_category(md_file)
            if category in stats:
                stats[category] += 1
            
            try:
                content = md_file.read_text(encoding="utf-8")
                stats["total_words"] += len(content.split())
                stats["total_links"] += len(self._extract_wikilinks(content))
            except Exception:
                continue
        
        return stats
