"""
Models - Модели данных приложения
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class AppState(Enum):
    """Состояния приложения"""
    IDLE = "idle"
    BUILDING = "building"
    WATCHING = "watching"
    LINTING = "linting"
    CHATTING = "chatting"
    ERROR = "error"


@dataclass
class Document:
    """Документ в raw/"""
    path: str
    filename: str
    extension: str
    size_bytes: int
    modified_time: datetime
    processed: bool = False
    page_count: Optional[int] = None
    
    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


@dataclass
class Concept:
    """Концепт в wiki"""
    name: str
    path: str
    content_preview: str
    wikilinks: list[str] = field(default_factory=list)
    backlinks: list[str] = field(default_factory=list)
    created_time: Optional[datetime] = None
    modified_time: Optional[datetime] = None


@dataclass
class Summary:
    """Summary в wiki"""
    name: str
    path: str
    content_preview: str
    source_documents: list[str] = field(default_factory=list)
    created_time: Optional[datetime] = None


@dataclass
class Exploration:
    """Exploration (результат исследования)"""
    name: str
    path: str
    query: str
    result: str
    created_time: datetime
    sources: list[str] = field(default_factory=list)


@dataclass
class HealthIssue:
    """Проблема здоровья wiki"""
    severity: str  # error, warning, info
    issue_type: str
    message: str
    file_path: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class BuildProgress:
    """Прогресс build"""
    current_step: str
    total_steps: int
    completed_steps: int
    current_file: Optional[str] = None
    
    @property
    def percentage(self) -> float:
        if self.total_steps == 0:
            return 0
        return (self.completed_steps / self.total_steps) * 100
