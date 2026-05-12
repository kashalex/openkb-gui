import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.build_service import BuildService, BuildState
from services.chat_service import ChatService


class BuildServiceTests(unittest.TestCase):
    def test_counts_supported_documents_recursively(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            raw = workspace / "raw" / "nested"
            raw.mkdir(parents=True)
            (raw / "doc.md").write_text("# Test\n", encoding="utf-8")
            (raw / "ignored.csv").write_text("no", encoding="utf-8")

            with patch.object(BuildService, "_check_openkb", return_value=False):
                service = BuildService(str(workspace))
            self.assertEqual(service.count_documents(), 1)

    def test_build_fails_when_raw_has_no_supported_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "raw").mkdir()
            with patch.object(BuildService, "_check_openkb", return_value=True):
                service = BuildService(str(workspace))
            service._openkb_available = True

            results = []
            started = service.build(on_complete=results.append)

            self.assertFalse(started)
            self.assertEqual(service.state, BuildState.FAILED)
            self.assertEqual(results[0].exit_code, -3)

    def test_generated_wiki_count_excludes_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            wiki = workspace / "wiki"
            (wiki / "concepts").mkdir(parents=True)
            (wiki / "AGENTS.md").write_text("rules", encoding="utf-8")
            (wiki / "concepts" / "alpha.md").write_text("# Alpha", encoding="utf-8")

            with patch.object(BuildService, "_check_openkb", return_value=False):
                service = BuildService(str(workspace))
            self.assertEqual(service.count_generated_wiki_pages(), 1)

    def test_openkb_module_fallback_uses_python_m_without_cli_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_find_spec(name):
                if name in {"openkb", "openkb.__main__"}:
                    return object()
                return None

            with patch("services.build_service.subprocess.run") as run_mock, \
                 patch("services.build_service.importlib.util.find_spec", side_effect=fake_find_spec), \
                 patch("services.build_service.importlib.metadata.version", return_value="1.2.3"):
                service = BuildService(str(Path(tmp)))

            run_mock.assert_not_called()
            self.assertTrue(service.openkb_available)
            self.assertTrue(service._use_python_m)
            self.assertEqual(service.openkb_version, "1.2.3")

    def test_openkb_module_without_main_is_not_runnable(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fake_find_spec(name):
                if name == "openkb":
                    return object()
                if name == "openkb.__main__":
                    return None
                return None

            completed = __import__("subprocess").CompletedProcess(
                args=["openkb", "--version"],
                returncode=1,
                stdout="",
                stderr="no version",
            )
            with patch("services.build_service.subprocess.run", return_value=completed), \
                 patch("services.build_service.importlib.util.find_spec", side_effect=fake_find_spec), \
                 patch("services.build_service.importlib.metadata.version", return_value="1.2.3"):
                service = BuildService(str(Path(tmp)))

            self.assertFalse(service.openkb_available)
            self.assertFalse(service._use_python_m)


class ChatServiceTests(unittest.TestCase):
    def test_search_wiki_returns_ranked_snippet_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            (wiki / "summaries").mkdir(parents=True)
            (wiki / "summaries" / "project.md").write_text(
                "# Project Plan\nOpenKB GUI uses retrieval before chat answers.",
                encoding="utf-8",
            )

            with patch("services.chat_service.get_litellm") as mocked_litellm:
                mocked_litellm.return_value.set_verbose = False
                mocked_litellm.return_value.drop_params = True
                service = ChatService(str(wiki), api_key="test-key")
            results = service.search_wiki("retrieval chat", limit=3)

            self.assertEqual(results[0].path, "summaries/project.md")
            self.assertIn("retrieval", results[0].snippet.lower())

    def test_load_wiki_context_includes_retrieved_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            wiki = Path(tmp) / "wiki"
            (wiki / "concepts").mkdir(parents=True)
            (wiki / "concepts" / "adapter.md").write_text(
                "# Adapter\nMinimal adaptation includes full text retrieval.",
                encoding="utf-8",
            )

            with patch("services.chat_service.get_litellm") as mocked_litellm:
                mocked_litellm.return_value.set_verbose = False
                mocked_litellm.return_value.drop_params = True
                service = ChatService(str(wiki), api_key="test-key")
            context, sources = service.load_wiki_context("full text retrieval")

            self.assertIn("Retrieved Wiki Excerpts", context)
            self.assertIn("concepts/adapter.md", sources)


if __name__ == "__main__":
    unittest.main()
