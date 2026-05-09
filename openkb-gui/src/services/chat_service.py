"""
Chat Service - Интеллектуальный диалог поверх compiled wiki
Работа с LLM через LiteLLM, не vector RAG
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Generator
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy import для litellm
_litellm = None


def get_litellm():
    """Ленивый импорт litellm"""
    global _litellm
    if _litellm is None:
        import litellm
        _litellm = litellm
    return _litellm


@dataclass
class ChatMessage:
    """Сообщение в чате"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    sources: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "sources": self.sources,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ChatMessage':
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sources=data.get("sources", []),
        )


@dataclass
class ChatResponse:
    """Ответ от чата"""
    content: str
    sources: list[str]
    model: str
    usage: dict
    finish_reason: str


class ChatService:
    """Сервис чата с базой знаний"""
    
    def __init__(self, 
                 wiki_path: str,
                 model: str = "openai/glm-4.7-flash",
                 api_base: str = "https://api.z.ai/api/paas/v4",
                 api_key: str = ""):
        """
        Инициализация chat сервиса
        
        Args:
            wiki_path: Путь к wiki директории
            model: Модель LLM
            api_base: URL API
            api_key: API ключ
        """
        self.wiki_path = Path(wiki_path).resolve()
        self.model = model
        self.api_base = api_base
        self.api_key = api_key
        
        # История сообщений
        self.messages: list[ChatMessage] = []
        
        # Системный промпт
        self.system_prompt = self._build_system_prompt()
        
        # Конфигурация litellm
        self._configure_litellm()
        
        logger.info(f"ChatService инициализирован для: {self.wiki_path}")
    
    def _configure_litellm(self):
        """Конфигурация LiteLLM"""
        litellm = get_litellm()
        
        # Устанавливаем переменные окружения для API
        os.environ["OPENAI_API_KEY"] = self.api_key
        os.environ["OPENAI_API_BASE"] = self.api_base
        
        # Отключаем логирование litellm
        litellm.set_verbose = False
    
    def _build_system_prompt(self) -> str:
        """Построение системного промпта"""
        return """You are an intelligent assistant that helps users explore and understand a compiled knowledge base.

IMPORTANT: You are NOT using vector RAG or embeddings search. You work with:
- Compiled wiki pages in markdown format
- Concept pages that synthesize related information
- Summaries that provide overviews
- Cross-linked knowledge graph

When answering questions:
1. Navigate through concepts and their relationships
2. Use summaries for overviews
3. Reference specific wiki pages when relevant
4. Build answers based on the compiled knowledge structure

Always cite your sources by mentioning the concept names or wiki page titles you used.

Be concise, accurate, and helpful. If you cannot find relevant information in the knowledge base, say so honestly."""
    
    def load_wiki_context(self) -> str:
        """Загрузка контекста wiki для промпта"""
        context_parts = []
        
        # Загружаем AGENTS.md
        agents_path = self.wiki_path / "AGENTS.md"
        if agents_path.exists():
            try:
                content = agents_path.read_text(encoding="utf-8")
                context_parts.append(f"# Knowledge Base Configuration\n\n{content[:2000]}\n")
            except Exception as e:
                logger.warning(f"Не удалось прочитать AGENTS.md: {e}")
        
        # Загружаем concepts
        concepts_path = self.wiki_path / "concepts"
        if concepts_path.exists():
            concepts = list(concepts_path.glob("*.md"))[:20]  # Первые 20
            concept_names = [c.stem for c in concepts]
            if concept_names:
                context_parts.append(f"# Available Concepts\n\n{', '.join(concept_names)}\n")
        
        # Загружаем summaries
        summaries_path = self.wiki_path / "summaries"
        if summaries_path.exists():
            summaries = list(summaries_path.glob("*.md"))[:10]
            summary_names = [s.stem for s in summaries]
            if summary_names:
                context_parts.append(f"# Available Summaries\n\n{', '.join(summary_names)}\n")
        
        return "\n".join(context_parts)
    
    def send_message(self, 
                     user_message: str,
                     stream: bool = False) -> ChatResponse:
        """
        Отправка сообщения пользователю
        
        Args:
            user_message: Сообщение пользователя
            stream: Использовать стриминг
        
        Returns:
            ChatResponse: Ответ от модели
        """
        litellm = get_litellm()
        
        # Добавляем сообщение пользователя
        self.messages.append(ChatMessage(
            role="user",
            content=user_message
        ))
        
        # Формируем сообщения для API
        api_messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # Добавляем контекст wiki
        wiki_context = self.load_wiki_context()
        if wiki_context:
            api_messages.append({
                "role": "system",
                "content": f"Current knowledge base context:\n\n{wiki_context}"
            })
        
        # Добавляем историю
        for msg in self.messages[-10:]:  # Последние 10 сообщений
            api_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        try:
            if stream:
                return self._stream_response(api_messages)
            else:
                return self._complete_response(api_messages)
                
        except Exception as e:
            logger.error(f"Ошибка при запросе к LLM: {e}")
            raise
    
    def _complete_response(self, messages: list[dict]) -> ChatResponse:
        """Получение полного ответа"""
        litellm = get_litellm()
        
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
        )
        
        choice = response.choices[0]
        content = choice.message.content
        
        # Добавляем ответ в историю
        self.messages.append(ChatMessage(
            role="assistant",
            content=content,
            sources=self._extract_sources(content)
        ))
        
        return ChatResponse(
            content=content,
            sources=self._extract_sources(content),
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    def _stream_response(self, messages: list[dict]) -> Generator[str, None, None]:
        """Стриминг ответа"""
        litellm = get_litellm()
        
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000,
            stream=True,
        )
        
        full_content = ""
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_content += delta.content
                yield delta.content
        
        # Добавляем полный ответ в историю
        self.messages.append(ChatMessage(
            role="assistant",
            content=full_content,
            sources=self._extract_sources(full_content)
        ))
    
    def _extract_sources(self, content: str) -> list[str]:
        """Извлечение упомянутых источников из ответа"""
        import re
        
        # Ищем wikilinks [[Concept Name]]
        wikilinks = re.findall(r'\[\[([^\]]+)\]\]', content)
        
        # Ищем упоминания concept names
        # Простая эвристика: слова с заглавной буквы
        # В реальном проекте здесь была бы более сложная логика
        
        return list(set(wikilinks))
    
    def clear_history(self):
        """Очистка истории чата"""
        self.messages.clear()
        logger.info("История чата очищена")
    
    def get_history(self) -> list[ChatMessage]:
        """Получение истории чата"""
        return self.messages.copy()
    
    def export_history(self) -> str:
        """Экспорт истории в JSON"""
        return json.dumps(
            [msg.to_dict() for msg in self.messages],
            indent=2,
            ensure_ascii=False
        )
    
    def import_history(self, json_data: str):
        """Импорт истории из JSON"""
        data = json.loads(json_data)
        self.messages = [ChatMessage.from_dict(msg) for msg in data]
        logger.info(f"Импортировано {len(self.messages)} сообщений")
    
    def read_concept(self, concept_name: str) -> Optional[str]:
        """Чтение страницы концепта"""
        concept_path = self.wiki_path / "concepts" / f"{concept_name}.md"
        if concept_path.exists():
            return concept_path.read_text(encoding="utf-8")
        return None
    
    def read_summary(self, summary_name: str) -> Optional[str]:
        """Чтение summary"""
        summary_path = self.wiki_path / "summaries" / f"{summary_name}.md"
        if summary_path.exists():
            return summary_path.read_text(encoding="utf-8")
        return None
    
    def search_wiki(self, query: str) -> list[str]:
        """Простой поиск по wiki (поиск в содержимом файлов)"""
        results = []
        query_lower = query.lower()
        
        for md_file in self.wiki_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    results.append(str(md_file.relative_to(self.wiki_path)))
            except Exception:
                continue
        
        return results
