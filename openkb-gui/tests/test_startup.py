import builtins
import importlib.util
import io
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = ROOT / "main.py"

spec = importlib.util.spec_from_file_location("openkb_gui_main", MAIN_PATH)
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)


class StartupDependencyMessageTests(unittest.TestCase):
    def test_missing_dependency_message_points_to_current_interpreter(self):
        message = main_module._missing_dependency_message("customtkinter", "customtkinter")

        self.assertIn(sys.executable, message)
        self.assertIn("-m pip install -r requirements.txt", message)
        self.assertIn("-m pip install customtkinter", message)
        self.assertIn("your `pip` command is installing into another Python", message)

    def test_import_customtkinter_exits_with_actionable_message(self):
        original_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "customtkinter":
                raise ModuleNotFoundError("No module named 'customtkinter'", name="customtkinter")
            return original_import(name, *args, **kwargs)

        stderr = io.StringIO()
        with patch("builtins.__import__", side_effect=fake_import):
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as ctx:
                    main_module.import_customtkinter_or_exit()

        self.assertEqual(ctx.exception.code, 1)
        output = stderr.getvalue()
        self.assertIn("Python package 'customtkinter' is not installed", output)
        self.assertIn("python and pip point to the same environment", output)


if __name__ == "__main__":
    unittest.main()
