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
        """Получить POM через HTTP и вывести граф с листовой вершиной."""
        with LocalRepository() as repository:
            repository.put(Artifact("org.example", "demo", "1.0"), """
                <dependencies><dependency>
                    <groupId>org.example</groupId>
                    <artifactId>library</artifactId>
                    <version>2.0</version>
                </dependency></dependencies>
            """)
            repository.put(Artifact("org.example", "library", "2.0"))
            result = self.invoke("--config", str(repository.config()))
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), [
            "Корень: org.example:demo:1.0",
            "org.example:demo:1.0 -> org.example:library:2.0",
            "org.example:library:2.0 -> нет",
            "Циклы не обнаружены.",
        ])

    def test_empty_dependencies(self):
        """Сохранить корень без зависимостей как отдельную вершину."""
        with LocalRepository() as repository:
            repository.put(Artifact("org.example", "demo", "1.0"))
            result = self.invoke("--config", str(repository.config()))
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertIn("org.example:demo:1.0 -> нет", result.stdout)

    def test_repository_error(self):
        """Обработать HTTP 404 без traceback и частичного вывода."""
        with LocalRepository() as repository:
            result = self.invoke("--config", str(repository.config()))
        self.assertEqual(result.returncode, EXIT_MAVEN_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertIn("HTTP 404", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_test_mode(self):
        """Вывести тестовый граф с общей транзитивной зависимостью."""
        result = self.invoke("--config", str(PROJECT / "examples/test.xml"))
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), [
            "Корень: A", "A -> B, C", "B -> C", "C -> нет",
            "Циклы не обнаружены.",
        ])

    def test_cycle(self):
        """Завершить обход цикла успешно и показать замкнутый путь."""
        result = self.invoke(
            "--config", str(PROJECT / "examples/test_cycle.xml")
        )
        self.assertEqual(result.returncode, EXIT_SUCCESS)
        self.assertIn("Цикл: A -> B -> C -> A", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_graph_error(self):
        """Отказать неполному тестовому графу без частичного вывода."""
        result = self.invoke(
            "--config", str(PROJECT / "examples/test_invalid.xml")
        )
        self.assertEqual(result.returncode, EXIT_MAVEN_ERROR)
        self.assertEqual(result.stdout, "")
        self.assertIn("Ошибка графа: Не описаны пакеты: B", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

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
