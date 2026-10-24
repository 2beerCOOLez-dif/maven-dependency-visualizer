"""Автономная проверка загрузки POM, наследования и прямых зависимостей."""

import unittest
from io import BytesIO
from urllib.error import URLError
from unittest.mock import patch

from dependency_visualizer.maven import (
    MavenRepository, build_pom_url, download_pom,
)
from dependency_visualizer.models import Artifact, MavenError
from dependency_visualizer.pom import expand, parse_pom
from http_repository import LocalRepository

PROJECT = Artifact("org.example", "demo", "1.0")
PARENT = Artifact("org.example", "parent", "1.0")
BOM = Artifact("org.example", "bom", "1.0")
SMALL_SIZE_LIMIT = 4


def dependency(artifact="library", version="2.0", extra="") -> str:
    """Создать объявление зависимости для тестового POM."""
    version_xml = f"<version>{version}</version>" if version else ""
    return (
        "<dependency><groupId>org.example</groupId>"
        f"<artifactId>{artifact}</artifactId>{version_xml}{extra}</dependency>"
    )


def parent_xml() -> str:
    """Создать ссылку на родительский POM."""
    return (
        "<parent><groupId>org.example</groupId>"
        "<artifactId>parent</artifactId><version>1.0</version></parent>"
    )


class MavenTests(unittest.TestCase):
    """Реальный HTTP на loopback без доступа к внешнему Maven-серверу."""

    def setUp(self):
        """Запустить временный сервер и создать клиент репозитория."""
        self.repository = LocalRepository().__enter__()
        self.addCleanup(self.repository.__exit__)
        self.client = MavenRepository(self.repository.url)

    def collect(self, version="1.0") -> list:
        """Получить прямые зависимости тестового проекта."""
        return self.client.direct_dependencies("org.example:demo", version)

    def test_pom_url(self):
        """Проверить структуру Maven URL и экранирование версии."""
        self.assertEqual(
            build_pom_url("https://example.org/repository/", PROJECT),
            "https://example.org/repository/org/example/demo/1.0/demo-1.0.pom",
        )
        self.assertIn(
            "/1.0%2Bbuild/", build_pom_url(
                self.repository.url,
                Artifact("org.example", "demo", "1.0+build"),
            ),
        )

    def test_properties_and_direct_only(self):
        """Раскрыть вложенные свойства и исключить зависимости плагинов."""
        body = (
            "<properties><base>2.0</base><library.version>${base}"
            "</library.version></properties><dependencies>"
            + dependency(version="${library.version}") + "</dependencies>"
            "<build><plugins><plugin><dependencies>"
            + dependency("plugin-only") + "</dependencies></plugin>"
            "</plugins></build>"
        )
        self.repository.put(PROJECT, body)
        result = self.collect()
        self.assertEqual([str(item.artifact) for item in result], [
            "org.example:library:2.0",
        ])
        self.assertEqual(self.repository.server.requests, [
            "/org/example/demo/1.0/demo-1.0.pom",
        ])

    def test_requested_version(self):
        """Две версии одного пакета должны возвращать разные зависимости."""
        for version, library in (("1.0", "old"), ("2.0", "new")):
            self.repository.put(
                Artifact("org.example", "demo", version),
                "<dependencies>" + dependency(library) + "</dependencies>",
            )
        old, = self.collect("1.0")
        new, = self.collect("2.0")
        self.assertEqual(old.artifact.artifact_id, "old")
        self.assertEqual(new.artifact.artifact_id, "new")

    def test_no_namespace_and_empty(self):
        """Принять POM без namespace и без зависимостей."""
        self.repository.put(PROJECT, namespace=False)
        self.assertEqual(self.collect(), [])

    def test_management_is_not_dependency(self):
        """Использовать управляемую версию, не выводя весь management."""
        body = (
            "<dependencyManagement><dependencies>"
            + dependency("library", "3.0") + dependency("unused")
            + "</dependencies></dependencyManagement><dependencies>"
            + dependency(version="") + "</dependencies>"
        )
        self.repository.put(PROJECT, body)
        result = self.collect()
        self.assertEqual([str(item.artifact) for item in result], [
            "org.example:library:3.0",
        ])

    def test_parent_properties_and_dependencies(self):
        """Унаследовать зависимости, management и свойства родителя."""
        self.repository.put(PARENT, (
            "<properties><library.version>2.0</library.version></properties>"
            "<dependencyManagement><dependencies>"
            + dependency(version="${library.version}")
            + "</dependencies></dependencyManagement><dependencies>"
            + dependency("inherited") + "</dependencies>"
        ))
        self.repository.put(PROJECT, (
            parent_xml()
            + "<properties><library.version>3.0</library.version></properties>"
            "<dependencies>" + dependency(version="") + "</dependencies>"
        ))
        self.assertEqual([str(item.artifact) for item in self.collect()], [
            "org.example:inherited:2.0", "org.example:library:3.0",
        ])

    def test_bom_import_and_local_override(self):
        """Импортировать BOM и предпочесть собственную управляемую версию."""
        self.repository.put(BOM, (
            "<properties><v>5.0</v></properties>"
            "<dependencyManagement><dependencies>"
            + dependency(version="${v}") + dependency("second", "4.0")
            + "</dependencies></dependencyManagement>"
        ))
        self.repository.put(PROJECT, (
            "<dependencyManagement><dependencies>"
            + dependency("bom", "1.0", "<type>pom</type><scope>import</scope>")
            + dependency("second", "6.0")
            + "</dependencies></dependencyManagement><dependencies>"
            + dependency(version="") + dependency("second", "")
            + "</dependencies>"
        ))
        self.assertEqual([str(item.artifact) for item in self.collect()], [
            "org.example:library:5.0", "org.example:second:6.0",
        ])

    def test_explicit_version_overrides_management(self):
        """Предпочесть явно заданную версию значению dependencyManagement."""
        self.repository.put(PROJECT, (
            "<dependencyManagement><dependencies>" + dependency(version="3.0")
            + "</dependencies></dependencyManagement><dependencies>"
            + dependency(version="2.0") + "</dependencies>"
        ))
        result, = self.collect()
        self.assertEqual(result.artifact.version, "2.0")

    def test_scopes_optional_and_classifier(self):
        """Сохранить test и optional, учитывать type и classifier."""
        self.repository.put(PROJECT, "<dependencies>" + dependency(extra=(
            "<scope>test</scope><optional>true</optional>"
            "<type>test-jar</type><classifier>tests</classifier>"
        )) + "</dependencies>")
        result, = self.collect()
        self.assertEqual(result.scope, "test")
        self.assertTrue(result.optional)
        self.assertEqual(result.classifier, "tests")
        self.assertEqual(result.artifact_type, "test-jar")

    def test_builtin_properties(self):
        """Раскрыть координаты проекта и родителя в версиях зависимостей."""
        self.repository.put(PARENT)
        self.repository.put(PROJECT, parent_xml() + "<dependencies>"
                            + dependency(version="${project.version}")
                            + dependency("parent-version", "${parent.version}")
                            + "</dependencies>")
        self.assertEqual([item.artifact.version for item in self.collect()], [
            "1.0", "1.0",
        ])

    def test_child_overrides_parent_dependency(self):
        """Заменить версию унаследованной зависимости объявлением потомка."""
        self.repository.put(PARENT, "<dependencies>"
                            + dependency(version="2.0") + "</dependencies>")
        self.repository.put(PROJECT, parent_xml() + "<dependencies>"
                            + dependency(version="3.0") + "</dependencies>")
        self.assertEqual([str(item.artifact) for item in self.collect()], [
            "org.example:library:3.0",
        ])

    def test_distinct_types_are_not_merged(self):
        """Сохранить две зависимости с одинаковыми именами и разными type."""
        self.repository.put(PROJECT, "<dependencies>"
                            + dependency()
                            + dependency(extra="<type>test-jar</type>")
                            + "</dependencies>")
        self.assertEqual([item.artifact_type for item in self.collect()], [
            "jar", "test-jar",
        ])

    def test_missing_version_and_unknown_property(self):
        """Не выдавать неполные зависимости при неизвестной версии."""
        for version in ("", "${missing}"):
            with self.subTest(version=version):
                self.repository.put(PROJECT, "<dependencies>"
                                    + dependency(version=version)
                                    + "</dependencies>")
                self.client = MavenRepository(self.repository.url)
                with self.assertRaises(MavenError):
                    self.collect()

    def test_parent_cycle(self):
        """Обнаружить цикл родительских POM без переполнения стека."""
        self.repository.put(PARENT, parent_xml())
        self.repository.put(PROJECT, parent_xml())
        with self.assertRaisesRegex(MavenError, "Цикл parent/BOM"):
            self.collect()

    def test_bom_cycle(self):
        """Обнаружить циклический импорт BOM."""
        body = (
            "<dependencyManagement><dependencies>"
            + dependency("bom", "1.0", "<type>pom</type><scope>import</scope>")
            + "</dependencies></dependencyManagement>"
        )
        self.repository.put(BOM, body)
        self.repository.put(PROJECT, body)
        with self.assertRaisesRegex(MavenError, "Цикл parent/BOM"):
            self.collect()

    def test_cache(self):
        """Не загружать один и тот же POM повторно."""
        self.repository.put(PROJECT)
        self.collect()
        self.collect()
        self.assertEqual(self.repository.server.requests, [
            "/org/example/demo/1.0/demo-1.0.pom",
        ])

    def test_http_not_found(self):
        """Обработать отсутствие POM заданной версии."""
        with self.assertRaisesRegex(MavenError, "HTTP 404"):
            self.collect()

    def test_wrong_identity(self):
        """Отклонить POM, содержащий другую версию проекта."""
        path = self.repository.put(PROJECT)
        data = path.read_text().replace("<version>1.0", "<version>9.0")
        path.write_text(data)
        with self.assertRaisesRegex(MavenError, "не соответствует"):
            self.collect()


class PomErrorTests(unittest.TestCase):
    """Граничные случаи XML, свойств и сетевых ошибок."""

    def test_bad_xml(self):
        """Отклонить поврежденный XML, DTD и неподдерживаемую модель."""
        for data in (
            b"<project>", b"<other/>", b"\xff", b"<project/>",
            b'<!DOCTYPE project [<!ENTITY x "x">]><project/>',
        ):
            with self.subTest(data=data):
                with self.assertRaises(MavenError):
                    parse_pom(data)

    def test_property_errors(self):
        """Отклонить неизвестные и циклические свойства."""
        cases = (
            ("${missing}", {}), ("${a}", {"a": "${a}"}),
            ("${a}", {"a": "${b}", "b": "${a}"}),
        )
        for value, properties in cases:
            with self.subTest(properties=properties):
                with self.assertRaises(MavenError):
                    expand(value, properties)

    def test_network_errors(self):
        """Преобразовать таймаут и ошибку DNS в MavenError."""
        for error in (TimeoutError("timeout"), URLError("DNS failed")):
            with self.subTest(error=error):
                with patch("dependency_visualizer.maven.urlopen",
                           side_effect=error):
                    with self.assertRaisesRegex(MavenError, "Сетевая ошибка"):
                        download_pom("https://example.org/demo.pom")

    def test_size_limit(self):
        """Отклонить слишком большой ответ, не читая его целиком."""
        with patch(
            "dependency_visualizer.maven.MAX_POM_BYTES", SMALL_SIZE_LIMIT,
        ):
            with patch("dependency_visualizer.maven.urlopen",
                       return_value=BytesIO(b"POM!!")):
                with self.assertRaisesRegex(MavenError, "размер"):
                    download_pom("https://example.org/demo.pom")
