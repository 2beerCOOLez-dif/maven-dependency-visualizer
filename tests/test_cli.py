"""Интеграционные проверки запуска CLI в отдельном процессе."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from dependency_visualizer.cli import EXIT_CONFIG_ERROR, EXIT_SUCCESS

PROJECT = Path(__file__).resolve().parent.parent
EXIT_ARGUMENT_ERROR = 2


class CliTests(unittest.TestCase):
    """Проверить потоки вывода и коды завершения приложения."""

    def invoke(self, *arguments):
        """Запустить модуль с контролируемым PYTHONPATH."""
        environment = dict(os.environ, PYTHONPATH=str(PROJECT / "src"))
        return subprocess.run(
            [sys.executable, "-m", "dependency_visualizer", *arguments],
            capture_output=True, text=True, check=False, env=environment,
        )

    def test_success(self):
        """Вывести четыре строки ключ-значение без ошибок."""
        result = self.invoke("--config", str(PROJECT / "examples/maven.xml"))
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), [
            "package=org.apache.commons:commons-lang3",
            "repository=https://repo.maven.apache.org/maven2",
            "test_mode=false", "version=3.14.0",
        ])

    def test_config_error(self):
        """Сообщить об ошибке в stderr без traceback и частичного вывода."""
        result = self.invoke("--config", str(PROJECT / "missing.xml"))
        self.assertEqual(result.returncode, EXIT_CONFIG_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertIn("Ошибка конфигурации", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_help_and_arguments(self):
        """Показать справку и отклонить отсутствие обязательного пути."""
        self.assertEqual(self.invoke("--help").returncode, EXIT_SUCCESS)
        self.assertEqual(self.invoke().returncode, EXIT_ARGUMENT_ERROR)
        self.assertEqual(
            self.invoke("--unknown").returncode, EXIT_ARGUMENT_ERROR
        )
