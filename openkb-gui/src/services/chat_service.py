"""
Chat Service - Интеллектуальный диалог поверх compiled wiki.

Сервис не строит vector RAG, но перед каждым LLM-запросом выполняет
полнотекстовый retrieval по markdown-страницам wiki и передаёт найденные
фрагменты как grounded-контекст.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)

# Lazy import для litellm
_litellm = None


SUPPORTED_WIKI_SUFFIXES = {".md", ".markdown", ".txt"}
MAX_CONTEXT_CHARS = 10_000
MAX_SNIPPET_CHARS = 900


def get_litellm():
    """Ленивый импорт litellm."""
    global _litellm
    if _litellm is None:
        import litellm
        _litellm = litellm
    return _litellm


@dataclass
class ChatMessage:
    """Сообщение в чате."""
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
    def from_dict(cls, data: dict) -> "ChatMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            sources=data.get("sources", []),
        )


@dataclass
class ChatResponse:
    """Ответ от чата."""
    content: str
    sources: list[str]
    model: str
    usage: dict
    finish_reason: str


@dataclass
class WikiSearchResult:
    """Результат полнотекстового поиска по wiki."""
    path: str
    title: str
    score: int
    snippet: str


class ChatService:
    """Сервис чата с базой знаний."""

    def __init__(
        self,
        wiki_path: str,
        model: str = "zai/glm-4.5-flash",
        api_base: str = "",
        api_key: str = "",
    ):
        """
        Args:
            wiki_path: Путь к wiki директории.
            model: LiteLLM model id в формате provider/model-name.
            api_base: URL API, если нужен провайдеру.
            api_key: API ключ текущего провайдера.
        """
        self.wiki_path = Path(wiki_path).resolve()
        self.model = model or "zai/glm-4.5-flash"
        self.api_base = api_base or ""
        self.api_key = api_key or ""
        self.messages: list[ChatMessage] = []
        self.system_prompt = self._build_system_prompt()
        self._configure_litellm()
        logger.info("ChatService инициализирован для: %s", self.wiki_path)

    @classmethod
    def from_config(cls, wiki_path: str, config) -> "ChatService":
        """Создание ChatService из AppConfig без дублирования provider-логики."""
        provider = config.get_current_provider()
        api_key = config.get_api_key_for_provider(provider) or config.llm_api_key
        return cls(
            wiki_path=wiki_path,
            model=config.get_litellm_model(),
            api_base=config.llm_api_base,
            api_key=api_key,
        )

    def _configure_litellm(self):
        """Конфигурация LiteLLM и совместимых env-переменных."""
        litellm = get_litellm()
        litellm.set_verbose = False
        litellm.drop_params = True

        if not self.api_key:
            return

        os.environ["LLM_MODEL"] = self.model
        os.environ["LLM_API_KEY"] = self.api_key
        if self.api_base:
            os.environ["LLM_API_BASE"] = self.api_base

        if self.model.startswith("zai/"):
            os.environ["ZAI_API_KEY"] = self.api_key
        elif self.model.startswith("openrouter/"):
            os.environ["OPENROUTER_API_KEY"] = self.api_key
            os.environ.setdefault("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
        else:
            # Совместимость с OpenAI-compatible endpoint'ами.
            os.environ["OPENAI_API_KEY"] = self.api_key
            if self.api_base:
                os.environ["OPENAI_API_BASE"] = self.api_base

    def _build_system_prompt(self) -> str:
        """Построение системного промпта."""
        return """You are an assistant answering questions using a compiled local knowledge base.

Grounding rules:
1. Use the retrieved wiki excerpts provided in the context first.
2. Cite sources with their wiki paths exactly as provided, for example: [sources/foo.md].
3. If the retrieved excerpts do not contain enough information, say that the knowledge base does not contain enough evidence.
4. Do not invent document names, facts, or citations.
5. Be concise and practical."""

    def _iter_wiki_files(self) -> list[Path]:
        if not self.wiki_path.exists():
            return []
        return sorted(
            path for path in self.wiki_path.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_WIKI_SUFFIXES
        )

    def _extract_title(self, content: str, fallback: str) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip() or fallback
        return fallback

    def _query_terms(self, query: str) -> list[str]:
        terms = re.findall(r"[\wА-Яа-яЁё]{3,}", query.lower())
        seen = set()
        return [term for term in terms if not (term in seen or seen.add(term))]

    def _make_snippet(self, content: str, terms: list[str]) -> str:
        compact = re.sub(r"\s+", " ", content).strip()
        if not compact:
            return ""

        lower = compact.lower()
        positions = [lower.find(term) for term in terms if term and lower.find(term) >= 0]
        start = max(0, min(positions) - 220) if positions else 0
        end = min(len(compact), start + MAX_SNIPPET_CHARS)
        snippet = compact[start:end]
        if start > 0:
            snippet = "…" + snippet
        if end < len(compact):
            snippet += "…"
        return snippet

    def search_wiki(self, query: str, limit: int = 6) -> list[WikiSearchResult]:
        """Полнотекстовый поиск по wiki с простым lexical scoring."""
        terms = self._query_terms(query)
        if not terms:
            return []

        results: list[WikiSearchResult] = []
        for md_file in self._iter_wiki_files():
            try:
                content = md_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception as exc:
                logger.warning("Не удалось прочитать wiki-файл %s: %s", md_file, exc)
                continue

            content_lower = content.lower()
            path_text = str(md_file.relative_to(self.wiki_path)).lower()
            score = 0
            for term in terms:
                score += content_lower.count(term) * 3
                score += path_text.count(term) * 5

            if score <= 0:
                continue

            rel_path = str(md_file.relative_to(self.wiki_path))
            results.append(WikiSearchResult(
                path=rel_path,
                title=self._extract_title(content, md_file.stem),
                score=score,
                snippet=self._make_snippet(content, terms),
            ))

        results.sort(key=lambda item: (-item.score, item.path))
        return results[:limit]

    def load_wiki_context(self, query: str = "") -> tuple[str, list[str]]:
        """Загрузка retrieval-контекста wiki для промпта."""
        context_parts = []
        sources: list[str] = []

        if not self.wiki_path.exists():
            return "", []

        agents_path = self.wiki_path / "AGENTS.md"
        if agents_path.exists():
            try:
                content = agents_path.read_text(encoding="utf-8")[:2000]
                context_parts.append(f"# Knowledge Base Configuration\n\n{content}\n")
                sources.append("AGENTS.md")
            except Exception as exc:
                logger.warning("Не удалось прочитать AGENTS.md: %s", exc)

        search_results = self.search_wiki(query, limit=8) if query else []
        if search_results:
            blocks = ["# Retrieved Wiki Excerpts"]
            used_chars = 0
            for result in search_results:
                block = (
                    f"\n## Source: {result.path}\n"
                    f"Title: {result.title}\n"
                    f"Score: {result.score}\n"
                    f"Excerpt: {result.snippet}\n"
                )
                if used_chars + len(block) > MAX_CONTEXT_CHARS:
                    break
                blocks.append(block)
                used_chars += len(block)
                sources.append(result.path)
            context_parts.append("\n".join(blocks))
        else:
            pages = self._iter_wiki_files()
            if pages:
                page_list = ", ".join(str(path.relative_to(self.wiki_path)) for path in pages[:30])
                context_parts.append(f"# Available Wiki Pages\n\n{page_list}\n")

        return "\n".join(context_parts), list(dict.fromkeys(sources))

    def send_message(self, user_message: str, stream: bool = False) -> ChatResponse | Generator[str, None, None]:
        """Отправка сообщения пользователя в LLM с retrieval-контекстом."""
        if not self.api_key:
            raise ValueError("API key is not configured for the selected provider")

        self.messages.append(ChatMessage(role="user", content=user_message))

        api_messages = [{"role": "system", "content": self.system_prompt}]
        wiki_context, retrieval_sources = self.load_wiki_context(user_message)
        if wiki_context:
            api_messages.append({
                "role": "system",
                "content": f"Current knowledge base context:\n\n{wiki_context}",
            })
        else:
            api_messages.append({
                "role": "system",
                "content": "No wiki context was found. Be explicit that the local knowledge base is empty or unavailable.",
            })

        for msg in self.messages[-10:]:
            api_messages.append({"role": msg.role, "content": msg.content})

        try:
            if stream:
                return self._stream_response(api_messages, retrieval_sources)
            return self._complete_response(api_messages, retrieval_sources)
        except Exception as exc:
            logger.error("Ошибка при запросе к LLM: %s", exc)
            raise

    def _complete_response(self, messages: list[dict], retrieval_sources: list[str]) -> ChatResponse:
        """Получение полного ответа."""
        litellm = get_litellm()
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
        )

        choice = response.choices[0]
        content = choice.message.content
        sources = list(dict.fromkeys(self._extract_sources(content) + retrieval_sources))
        self.messages.append(ChatMessage(role="assistant", content=content, sources=sources))

        usage_obj = getattr(response, "usage", None)
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0) if usage_obj else 0,
            "completion_tokens": getattr(usage_obj, "completion_tokens", 0) if usage_obj else 0,
            "total_tokens": getattr(usage_obj, "total_tokens", 0) if usage_obj else 0,
        }

        return ChatResponse(
            content=content,
            sources=sources,
            model=getattr(response, "model", self.model),
            usage=usage,
            finish_reason=getattr(choice, "finish_reason", "unknown"),
        )

    def _stream_response(self, messages: list[dict], retrieval_sources: list[str]) -> Generator[str, None, None]:
        """Стриминг ответа."""
        litellm = get_litellm()
        response = litellm.completion(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=2000,
            stream=True,
        )

        full_content = ""
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_content += delta.content
                yield delta.content

        sources = list(dict.fromkeys(self._extract_sources(full_content) + retrieval_sources))
        self.messages.append(ChatMessage(role="assistant", content=full_content, sources=sources))

    def _extract_sources(self, content: str) -> list[str]:
        """Извлечение упомянутых источников из ответа."""
        wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)
        bracket_paths = re.findall(r"\[([^\]]+\.md)\]", content)
        return list(dict.fromkeys(wikilinks + bracket_paths))

    def clear_history(self):
        """Очистка истории чата."""
        self.messages.clear()
        logger.info("История чата очищена")

    def get_history(self) -> list[ChatMessage]:
        """Получение истории чата."""
        return self.messages.copy()

    def export_history(self) -> str:
        """Экспорт истории в JSON."""
        return json.dumps([msg.to_dict() for msg in self.messages], indent=2, ensure_ascii=False)

    def import_history(self, json_data: str):
        """Импорт истории из JSON."""
        data = json.loads(json_data)
        self.messages = [ChatMessage.from_dict(msg) for msg in data]
        logger.info("Импортировано %s сообщений", len(self.messages))

    def read_concept(self, concept_name: str) -> Optional[str]:
        """Чтение страницы концепта."""
        concept_path = self.wiki_path / "concepts" / f"{concept_name}.md"
        if concept_path.exists():
            return concept_path.read_text(encoding="utf-8")
        return None

    def read_summary(self, summary_name: str) -> Optional[str]:
        """Чтение summary."""
        summary_path = self.wiki_path / "summaries" / f"{summary_name}.md"
        if summary_path.exists():
            return summary_path.read_text(encoding="utf-8")
        return None
