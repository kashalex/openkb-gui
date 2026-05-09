"""
Lint Service - Диагностика и проверка состояния базы знаний
Запуск openkb lint и анализ результатов
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LintSeverity(Enum):
    """Уровни серьёзности проблем"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintIssue:
    """Проблема, найденная при lint"""
    severity: LintSeverity
    issue_type: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    
    def __str__(self) -> str:
        location = ""
        if self.file_path:
            location = f" [{self.file_path}"
            if self.line_number:
                location += f":{self.line_number}"
            location += "]"
        return f"[{self.severity.value.upper()}] {self.issue_type}: {self.message}{location}"


@dataclass
class LintReport:
    """Отчёт о lint проверке"""
    total_issues: int
    errors: int
    warnings: int
    info: int
    issues: list[LintIssue] = field(default_factory=list)
    
    def has_errors(self) -> bool:
        return self.errors > 0
    
    def has_warnings(self) -> bool:
        return self.warnings > 0


class LintService:
    """Сервис диагностики базы знаний"""
    
    def __init__(self, workspace_path: str):
        """
        Инициализация lint сервиса
        
        Args:
            workspace_path: Путь к workspace
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.wiki_path = self.workspace_path / "wiki"
        
        logger.info(f"LintService инициализирован для: {self.workspace_path}")
    
    def run_lint(self) -> LintReport:
        """
        Запуск lint проверки через openkb lint
        
        Returns:
            LintReport: Отчёт о проверке
        """
        issues: list[LintIssue] = []
        
        # Запускаем openkb lint
        try:
            result = subprocess.run(
                ["openkb", "lint", str(self.workspace_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 минут
                cwd=str(self.workspace_path)
            )
            
            # Парсим вывод
            output = result.stdout + result.stderr
            issues.extend(self._parse_lint_output(output))
            
        except FileNotFoundError:
            logger.warning("OpenKB не найден, используется встроенная проверка")
            issues.extend(self._builtin_lint())
        except subprocess.TimeoutExpired:
            issues.append(LintIssue(
                severity=LintSeverity.ERROR,
                issue_type="timeout",
                message="Lint проверка превысила таймаут"
            ))
        except Exception as e:
            issues.append(LintIssue(
                severity=LintSeverity.ERROR,
                issue_type="execution_error",
                message=f"Ошибка выполнения lint: {e}"
            ))
        
        # Подсчёт статистики
        errors = sum(1 for i in issues if i.severity == LintSeverity.ERROR)
        warnings = sum(1 for i in issues if i.severity == LintSeverity.WARNING)
        info = sum(1 for i in issues if i.severity == LintSeverity.INFO)
        
        return LintReport(
            total_issues=len(issues),
            errors=errors,
            warnings=warnings,
            info=info,
            issues=issues
        )
    
    def _parse_lint_output(self, output: str) -> list[LintIssue]:
        """Парсинг вывода openkb lint"""
        issues = []
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Определяем severity
            severity = LintSeverity.INFO
            if 'error' in line.lower():
                severity = LintSeverity.ERROR
            elif 'warning' in line.lower() or 'warn' in line.lower():
                severity = LintSeverity.WARNING
            
            # Определяем тип проблемы
            issue_type = "unknown"
            if 'broken link' in line.lower():
                issue_type = "broken_link"
            elif 'orphan' in line.lower():
                issue_type = "orphan_concept"
            elif 'stale' in line.lower():
                issue_type = "stale_page"
            elif 'contradiction' in line.lower():
                issue_type = "contradiction"
            
            if issue_type != "unknown" or severity != LintSeverity.INFO:
                issues.append(LintIssue(
                    severity=severity,
                    issue_type=issue_type,
                    message=line
                ))
        
        return issues
    
    def _builtin_lint(self) -> list[LintIssue]:
        """Встроенная проверка (fallback)"""
        issues = []
        
        if not self.wiki_path.exists():
            issues.append(LintIssue(
                severity=LintSeverity.ERROR,
                issue_type="missing_wiki",
                message="Wiki директория не существует"
            ))
            return issues
        
        # Проверка orphan concepts
        issues.extend(self._check_orphan_concepts())
        
        # Проверка broken links
        issues.extend(self._check_broken_links())
        
        # Проверка stale pages
        issues.extend(self._check_stale_pages())
        
        return issues
    
    def _check_orphan_concepts(self) -> list[LintIssue]:
        """Проверка orphan concepts"""
        issues = []
        concepts_path = self.wiki_path / "concepts"
        
        if not concepts_path.exists():
            return issues
        
        # Получаем все wikilinks из wiki
        all_links = set()
        for md_file in self.wiki_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                import re
                links = re.findall(r'\[\[([^\]]+)\]\]', content)
                all_links.update(link.lower() for link in links)
            except Exception:
                continue
        
        # Проверяем, есть ли ссылки на каждый concept
        for concept_file in concepts_path.glob("*.md"):
            concept_name = concept_file.stem.lower()
            if concept_name not in all_links:
                issues.append(LintIssue(
                    severity=LintSeverity.WARNING,
                    issue_type="orphan_concept",
                    message=f"Concept '{concept_file.stem}' не имеет входящих ссылок",
                    file_path=str(concept_file.relative_to(self.workspace_path))
                ))
        
        return issues
    
    def _check_broken_links(self) -> list[LintIssue]:
        """Проверка broken links"""
        issues = []
        
        # Собираем все существующие страницы
        existing_pages = set()
        for md_file in self.wiki_path.rglob("*.md"):
            existing_pages.add(md_file.stem.lower())
        
        # Ищем ссылки на несуществующие страницы
        for md_file in self.wiki_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                import re
                links = re.findall(r'\[\[([^\]]+)\]\]', content)
                
                for link in links:
                    link_lower = link.lower()
                    if link_lower not in existing_pages:
                        issues.append(LintIssue(
                            severity=LintSeverity.WARNING,
                            issue_type="broken_link",
                            message=f"Broken link: [[{link}]]",
                            file_path=str(md_file.relative_to(self.workspace_path))
                        ))
            except Exception:
                continue
        
        return issues
    
    def _check_stale_pages(self) -> list[LintIssue]:
        """Проверка stale pages"""
        issues = []
        import time
        
        # Страницы, не обновлявшиеся более 30 дней
        stale_threshold = time.time() - (30 * 24 * 60 * 60)
        
        for md_file in self.wiki_path.rglob("*.md"):
            mtime = md_file.stat().st_mtime
            if mtime < stale_threshold:
                from datetime import datetime
                last_modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                issues.append(LintIssue(
                    severity=LintSeverity.INFO,
                    issue_type="stale_page",
                    message=f"Страница не обновлялась с {last_modified}",
                    file_path=str(md_file.relative_to(self.workspace_path))
                ))
        
        return issues
    
    def check_health(self) -> dict:
        """
        Быстрая проверка здоровья базы знаний
        
        Returns:
            dict: Статистика здоровья
        """
        stats = {
            "wiki_exists": self.wiki_path.exists(),
            "concepts_count": 0,
            "summaries_count": 0,
            "explorations_count": 0,
            "total_pages": 0,
            "agents_exists": False,
            "issues": [],
        }
        
        if not self.wiki_path.exists():
            stats["issues"].append("Wiki директория не существует")
            return stats
        
        # Подсчёт страниц
        concepts_path = self.wiki_path / "concepts"
        if concepts_path.exists():
            stats["concepts_count"] = len(list(concepts_path.glob("*.md")))
        
        summaries_path = self.wiki_path / "summaries"
        if summaries_path.exists():
            stats["summaries_count"] = len(list(summaries_path.glob("*.md")))
        
        explorations_path = self.wiki_path / "explorations"
        if explorations_path.exists():
            stats["explorations_count"] = len(list(explorations_path.glob("*.md")))
        
        stats["total_pages"] = len(list(self.wiki_path.rglob("*.md")))
        
        # Проверка AGENTS.md
        agents_path = self.wiki_path / "AGENTS.md"
        stats["agents_exists"] = agents_path.exists()
        
        if stats["total_pages"] == 0:
            stats["issues"].append("Wiki пуста - запустите build")
        
        return stats
