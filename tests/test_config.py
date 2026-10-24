"""Проверки всех полей и ошибок XML средствами unittest."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from dependency_visualizer.config import ConfigError, FIELDS, load_config
from dependency_visualizer.validation import validate_repository


class ConfigTests(unittest.TestCase):
    """Изолированные конфигурации и тестовый репозиторий."""

    def setUp(self):
        """Создать временную директорию с корректными настройками."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.path = self.base / "config.xml"
        self.values = {
            "package": "org.example:demo", "repository": "https://example.org",
            "test_mode": "false", "version": "1.0-SNAPSHOT",
        }

    def write_config(self, values=None):
        """Записать конфигурацию, сохраняя экранирование XML."""
        root = ElementTree.Element("configuration")
        for key, value in (self.values if values is None else values).items():
            ElementTree.SubElement(root, key).text = value
        ElementTree.ElementTree(root).write(self.path, encoding="utf-8")
        return self.path

    def test_valid_maven(self):
        """Принять все поля обычного режима без сетевого обращения."""
        config = load_config(self.write_config())
        self.assertEqual(config.package, self.values["package"])
        self.assertEqual(config.repository, self.values["repository"])
        self.assertEqual(config.version, self.values["version"])
        self.assertFalse(config.test_mode)

    def test_relative_test_repository(self):
        """Разрешить путь относительно XML, а не текущего каталога."""
        repository = self.base / "repo.txt"
        repository.write_text("A: B\nB:\n", encoding="utf-8")
        self.values.update(
            package="A", repository="repo.txt", test_mode="true"
        )
        config = load_config(self.write_config())
        self.assertEqual(config.repository, str(repository.resolve()))
        self.assertTrue(config.test_mode)

    def test_missing_and_empty_fields(self):
        """Отклонить отсутствие и пустое значение каждого параметра."""
        for field in FIELDS:
            for blank in (None, "", "   "):
                with self.subTest(field=field, blank=blank):
                    values = self.values.copy()
                    if blank is None:
                        del values[field]
                    else:
                        values[field] = blank
                    with self.assertRaises(ConfigError):
                        load_config(self.write_config(values))

    def test_invalid_values(self):
        """Отклонить неверные форматы всех четырех параметров."""
        cases = {
            "package": ("demo", "g:a:b", "g:bad name", "g:../a"),
            "repository": (
                "repo.txt", "ftp://example.org", "https://", "https://[bad",
                "https://host:bad", "https://host:99999", "https://a b",
                "https://u:p@host", "https://host?q=a", "https://host/#x",
                "https://host\\path",
            ),
            "test_mode": ("yes", "1", "TRUE"),
            "version": ("[1,2)", "bad version", "../1", "версия"),
        }
        for field, invalid_values in cases.items():
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    values = dict(self.values, **{field: value})
                    with self.assertRaisesRegex(ConfigError, field):
                        load_config(self.write_config(values))

    def test_invalid_test_settings(self):
        """Проверить имена и отсутствующие либо нечитаемые файлы."""
        self.values.update(package="A", test_mode="true")
        for repository in ("missing.txt", "."):
            with self.subTest(repository=repository):
                self.values["repository"] = repository
                with self.assertRaisesRegex(ConfigError, "repository"):
                    load_config(self.write_config())
        self.values["repository"] = str(self.write_config())
        for package in ("a", "A1", "A:B", "А"):
            self.values["package"] = package
            with self.subTest(package=package):
                with self.assertRaisesRegex(ConfigError, "package"):
                    load_config(self.write_config())

    def test_unreadable_repository(self):
        """Имитировать отказ доступа именно к файлу репозитория."""
        repository = self.base / "repo.txt"
        repository.touch()
        with patch.object(Path, "open", side_effect=PermissionError("denied")):
            with self.assertRaisesRegex(ConfigError, "repository"):
                validate_repository(str(repository), True, self.base)

    def test_xml_structure(self):
        """Отклонить сломанный XML, DTD и нарушения схемы полей."""
        valid = self.write_config().read_text(encoding="utf-8")
        cases = (
            "<configuration>", "<other/>",
            valid.replace("<configuration>", '<configuration extra="x">'),
            valid.replace("</configuration>", "<unknown/></configuration>"),
            valid.replace("</configuration>", "<package>A</package>"
                          "</configuration>"),
            valid.replace("<package>", '<package extra="x">'),
            valid.replace("<package>", "<package><nested/>"),
            valid.replace("<configuration>", "<configuration>stray"),
            valid.replace("</package>", "</package>stray"),
            '<!DOCTYPE configuration [<!ENTITY x "A">]>' + valid,
        )
        for text in cases:
            with self.subTest(xml=text):
                self.path.write_text(text, encoding="utf-8")
                with self.assertRaises(ConfigError):
                    load_config(self.path)

    def test_duplicate_each_field(self):
        """Отклонить повторение любого параметра."""
        for field in FIELDS:
            root = ElementTree.parse(self.write_config()).getroot()
            ElementTree.SubElement(root, field).text = self.values[field]
            ElementTree.ElementTree(root).write(self.path, encoding="utf-8")
            with self.subTest(field=field):
                with self.assertRaisesRegex(ConfigError, field):
                    load_config(self.path)

    def test_file_errors(self):
        """Обработать отсутствие XML, каталог и неверную кодировку."""
        for path in (self.path, self.base):
            with self.subTest(path=path):
                with self.assertRaises(ConfigError):
                    load_config(path)
        self.path.write_bytes(b"\xff")
        with self.assertRaises(ConfigError):
            load_config(self.path)
