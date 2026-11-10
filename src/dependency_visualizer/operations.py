"""Выбор источника прямых зависимостей для единого алгоритма DFS."""

from pathlib import Path

from .config import Config
from .graph import DependencyGraph, build_graph
from .maven import MavenRepository
from .test_repository import FileRepository


def collect_graph(config: Config) -> DependencyGraph:
    """Построить граф тестовых имен либо точных Maven-координат."""
    if config.test_mode:
        test_repository = FileRepository(Path(config.repository))
        return build_graph(config.package, test_repository.neighbors)
    repository = MavenRepository(config.repository)

    def neighbors(node: str) -> list[str]:
        """Загрузить POM вершины, сохранив явно объявленные версии."""
        package, version = node.rsplit(":", maxsplit=1)
        return [
            str(dependency.artifact) for dependency in
            repository.direct_dependencies(package, version)
        ]

    return build_graph(f"{config.package}:{config.version}", neighbors)
