"""Интеграционные проверки запуска CLI в отдельном процессе."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

from dependency_visualizer.cli import (
    EXIT_CONFIG_ERROR, EXIT_MAVEN_ERROR, EXIT_SUCCESS,
)
from dependency_visualizer.models import Artifact
from http_repository import LocalRepository

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
        """Получить POM через HTTP и вывести прямую зависимость."""
        with LocalRepository() as repository:
            repository.put(Artifact("org.example", "demo", "1.0"), """
                <dependencies><dependency>
                    <groupId>org.example</groupId>
                    <artifactId>library</artifactId>
                    <version>2.0</version>
                </dependency></dependencies>
            """)
            result = self.invoke("--config", str(repository.config()))
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), [
            "org.example:library:2.0 [scope=compile, type=jar]",
        ])

    def test_empty_dependencies(self):
        """Сообщить об отсутствии зависимостей без ошибки."""
        with LocalRepository() as repository:
            repository.put(Artifact("org.example", "demo", "1.0"))
            result = self.invoke("--config", str(repository.config()))
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertEqual(
            result.stdout.strip(), "Прямые зависимости не найдены."
        )

    def test_repository_error(self):
        """Обработать HTTP 404 без traceback и частичного вывода."""
        with LocalRepository() as repository:
            result = self.invoke("--config", str(repository.config()))
        self.assertEqual(result.returncode, EXIT_MAVEN_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertIn("HTTP 404", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_test_mode(self):
        """Явно сообщить, что работа с тестовым графом относится к этапу 3."""
        result = self.invoke("--config", str(PROJECT / "examples/test.xml"))
        self.assertEqual(result.returncode, EXIT_MAVEN_ERROR)
        self.assertIn("этапу 3", result.stderr)

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
