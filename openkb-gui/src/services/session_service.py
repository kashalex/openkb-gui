"""
Session Service - Управление сессиями чата
Сохранение, загрузка, удаление и экспорт сессий
"""

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """Сессия чата"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": self.messages,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChatSession':
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=data.get("messages", []),
        )


class SessionService:
    """Сервис управления сессиями"""
    
    def __init__(self, sessions_path: str):
        """
        Инициализация session сервиса
        
        Args:
            sessions_path: Путь к директории сессий
        """
        self.sessions_path = Path(sessions_path).resolve()
        self.sessions_path.mkdir(parents=True, exist_ok=True)
        
        # Кэш сессий
        self._sessions_cache: dict[str, ChatSession] = {}
        
        logger.info(f"SessionService инициализирован для: {self.sessions_path}")
    
    def create_session(self, title: Optional[str] = None) -> ChatSession:
        """
        Создание новой сессии
        
        Args:
            title: Заголовок сессии (опционально)
        
        Returns:
            ChatSession: Созданная сессия
        """
        import uuid
        
        session_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        
        if not title:
            title = f"Session {now.strftime('%Y-%m-%d %H:%M')}"
        
        session = ChatSession(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            messages=[]
        )
        
        # Сохраняем в кэш и файл
        self._sessions_cache[session_id] = session
        self._save_session(session)
        
        logger.info(f"Создана сессия: {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Получение сессии по ID
        
        Args:
            session_id: ID сессии
        
        Returns:
            ChatSession: Сессия или None
        """
        # Проверяем кэш
        if session_id in self._sessions_cache:
            return self._sessions_cache[session_id]
        
        # Загружаем из файла
        session = self._load_session(session_id)
        if session:
            self._sessions_cache[session_id] = session
        
        return session
    
    def list_sessions(self) -> list[ChatSession]:
        """
        Получение списка всех сессий
        
        Returns:
            list[ChatSession]: Список сессий
        """
        sessions = []
        
        # Загружаем все файлы сессий
        for session_file in self.sessions_path.glob("*.json"):
            try:
                session_id = session_file.stem
                session = self.get_session(session_id)
                if session:
                    sessions.append(session)
            except Exception as e:
                logger.warning(f"Ошибка загрузки сессии {session_file}: {e}")
        
        # Сортируем по дате обновления (новые первые)
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        
        return sessions
    
    def update_session(self, session: ChatSession) -> bool:
        """
        Обновление сессии
        
        Args:
            session: Сессия для обновления
        
        Returns:
            bool: True если успешно
        """
        session.updated_at = datetime.now()
        self._sessions_cache[session.id] = session
        return self._save_session(session)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Удаление сессии
        
        Args:
            session_id: ID сессии
        
        Returns:
            bool: True если успешно
        """
        # Удаляем из кэша
        if session_id in self._sessions_cache:
            del self._sessions_cache[session_id]
        
        # Удаляем файл
        session_file = self.sessions_path / f"{session_id}.json"
        if session_file.exists():
            try:
                session_file.unlink()
                logger.info(f"Сессия удалена: {session_id}")
                return True
            except Exception as e:
                logger.error(f"Ошибка удаления сессии {session_id}: {e}")
                return False
        
        return True
    
    def export_session(self, session_id: str, format: str = "json") -> Optional[str]:
        """
        Экспорт сессии
        
        Args:
            session_id: ID сессии
            format: Формат экспорта (json, markdown, txt)
        
        Returns:
            str: Экспортированное содержимое
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        if format == "json":
            return json.dumps(session.to_dict(), indent=2, ensure_ascii=False)
        
        elif format == "markdown":
            lines = [
                f"# {session.title}",
                f"",
                f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}",
                f"Updated: {session.updated_at.strftime('%Y-%m-%d %H:%M')}",
                f"",
                "---",
                f"",
            ]
            
            for msg in session.messages:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                lines.append(f"## {role}")
                if timestamp:
                    lines.append(f"*{timestamp}*")
                lines.append(f"")
                lines.append(content)
                lines.append(f"")
                lines.append("---")
                lines.append(f"")
            
            return "\n".join(lines)
        
        elif format == "txt":
            lines = [
                f"Session: {session.title}",
                f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M')}",
                f"",
            ]
            
            for msg in session.messages:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                lines.append(f"[{role}]: {content}")
                lines.append(f"")
            
            return "\n".join(lines)
        
        return None
    
    def import_session(self, data: str, format: str = "json") -> Optional[ChatSession]:
        """
        Импорт сессии
        
        Args:
            data: Данные для импорта
            format: Формат данных
        
        Returns:
            ChatSession: Импортированная сессия
        """
        try:
            if format == "json":
                session_data = json.loads(data)
                session = ChatSession.from_dict(session_data)
                
                # Генерируем новый ID
                import uuid
                session.id = str(uuid.uuid4())[:8]
                session.created_at = datetime.now()
                session.updated_at = datetime.now()
                
                self._sessions_cache[session.id] = session
                self._save_session(session)
                
                logger.info(f"Сессия импортирована: {session.id}")
                return session
            
        except Exception as e:
            logger.error(f"Ошибка импорта сессии: {e}")
            return None
        
        return None
    
    def add_message(self, session_id: str, role: str, content: str, sources: list[str] = None) -> bool:
        """
        Добавление сообщения в сессию
        
        Args:
            session_id: ID сессии
            role: Роль (user, assistant, system)
            content: Содержимое сообщения
            sources: Источники (опционально)
        
        Returns:
            bool: True если успешно
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        
        if sources:
            message["sources"] = sources
        
        session.messages.append(message)
        return self.update_session(session)
    
    def _save_session(self, session: ChatSession) -> bool:
        """Сохранение сессии в файл"""
        session_file = self.sessions_path / f"{session.id}.json"
        
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения сессии {session.id}: {e}")
            return False
    
    def _load_session(self, session_id: str) -> Optional[ChatSession]:
        """Загрузка сессии из файла"""
        session_file = self.sessions_path / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ChatSession.from_dict(data)
        except Exception as e:
            logger.error(f"Ошибка загрузки сессии {session_id}: {e}")
            return None
    
    def clear_all(self) -> bool:
        """Удаление всех сессий"""
        try:
            for session_file in self.sessions_path.glob("*.json"):
                session_file.unlink()
            self._sessions_cache.clear()
            logger.info("Все сессии удалены")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления всех сессий: {e}")
            return False
