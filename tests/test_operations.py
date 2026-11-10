"""Построение транзитивного Maven-графа через настоящий локальный HTTP."""

import unittest

from dependency_visualizer.config import load_config
from dependency_visualizer.models import Artifact, MavenError
from dependency_visualizer.operations import collect_graph
from http_repository import LocalRepository


def dependency(name: str, version: str = "1.0") -> str:
    """Сформировать объявление зависимости для тестового POM."""
    return (
        "<dependency><groupId>org.example</groupId>"
        f"<artifactId>{name}</artifactId><version>{version}</version>"
        "</dependency>"
    )


def put_package(repository, name: str, dependencies: str = "") -> None:
    """Разместить POM пакета с указанным списком зависимостей."""
    repository.put(
        Artifact("org.example", name, "1.0"),
        f"<dependencies>{dependencies}</dependencies>",
    )


class OperationsTests(unittest.TestCase):
    """Проверить транзитивность, циклы, кеш и версии Maven-вершин."""

    def test_http_diamond_and_cycle(self):
        """Обойти ромб и цикл, запросив POM каждого пакета один раз."""
        with LocalRepository() as repository:
            put_package(repository, "a", dependency("b") + dependency("c"))
            put_package(repository, "b", dependency("d"))
            put_package(repository, "c", dependency("d"))
            put_package(repository, "d", dependency("a"))
            config = load_config(repository.config("org.example:a"))
            graph = collect_graph(config)
            requests = repository.server.requests
        self.assertEqual(list(graph.adjacency), [
            f"org.example:{name}:1.0" for name in ("a", "b", "d", "c")
        ])
        self.assertEqual(graph.cycles, [(
            "org.example:a:1.0", "org.example:b:1.0",
            "org.example:d:1.0", "org.example:a:1.0",
        )])
        self.assertEqual(len(requests), len(graph.adjacency))
        self.assertEqual(len(requests), len(set(requests)))

    def test_distinct_versions(self):
        """Сохранить разные версии артефакта как разные вершины."""
        with LocalRepository() as repository:
            put_package(repository, "a", dependency("b") + dependency("c"))
            put_package(repository, "b", dependency("c", "2.0"))
            put_package(repository, "c")
            repository.put(Artifact("org.example", "c", "2.0"))
            graph = collect_graph(load_config(
                repository.config("org.example:a")
            ))
        self.assertIn("org.example:c:1.0", graph.adjacency)
        self.assertIn("org.example:c:2.0", graph.adjacency)

    def test_missing_transitive_pom(self):
        """Не пропустить ошибку загрузки транзитивной зависимости."""
        with LocalRepository() as repository:
            put_package(repository, "a", dependency("b"))
            put_package(repository, "b", dependency("missing"))
            config = load_config(repository.config("org.example:a"))
            with self.assertRaisesRegex(MavenError, "HTTP 404"):
                collect_graph(config)
