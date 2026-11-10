"""Проверки формата и ошибок локального тестового репозитория."""

import tempfile
import unittest
from pathlib import Path

from dependency_visualizer.test_repository import (
    FileRepository, GraphError, parse_repository,
)


class FileRepositoryTests(unittest.TestCase):
    """Проверить строгие заглавные имена и полноту описания."""

    def test_whitespace_and_duplicates(self):
        """Принять пробелы, пустые строки и повтор одного ребра."""
        result = parse_repository("\n A : B B CC\n B:\n CC :\n")
        self.assertEqual(result, {"A": ("B", "CC"), "B": (), "CC": ()})

    def test_invalid_descriptions(self):
        """Отклонить пустой файл, плохие имена и повторные определения."""
        cases = (
            "", " \n", "A B", "a:", "А:", "A1:", "A: b",
            "A: B: C", "A:\nA:", "A: B", ": A", "A: # comment",
        )
        for text in cases:
            with self.subTest(text=text), self.assertRaises(GraphError):
                parse_repository(text)

    def test_utf8_bom_and_missing_root(self):
        """Прочитать BOM и сообщить об отсутствии выбранного пакета."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.txt"
            path.write_text("A:\n", encoding="utf-8-sig")
            repository = FileRepository(path)
            self.assertEqual(repository.neighbors("A"), ())
            with self.assertRaisesRegex(GraphError, "Z отсутствует"):
                repository.neighbors("Z")

    def test_file_errors(self):
        """Обработать исчезнувший файл и недопустимую кодировку."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.txt"
            with self.assertRaises(GraphError):
                FileRepository(path)
            path.write_bytes(b"\xff\xfe")
            with self.assertRaises(GraphError):
                FileRepository(path)
