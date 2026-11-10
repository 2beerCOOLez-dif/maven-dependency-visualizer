"""Командный интерфейс построения графа зависимостей."""

import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .graph import format_graph
from .models import MavenError
from .operations import collect_graph
from .test_repository import GraphError

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_MAVEN_ERROR = 3


def create_parser() -> argparse.ArgumentParser:
    """Создать интерфейс выбора единственного источника настроек — XML."""
    parser = argparse.ArgumentParser(
        description="Вариант 25. Этап 3: граф зависимостей и циклы, DFS."
    )
    parser.add_argument(
        "--config", required=True, type=Path, metavar="FILE.xml",
        help="путь к XML-конфигурации в UTF-8",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Вывести полный граф либо ошибку без частичного результата."""
    arguments = create_parser().parse_args(argv)
    try:
        config = load_config(arguments.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        graph = collect_graph(config)
    except GraphError as error:
        print(f"Ошибка графа: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    except MavenError as error:
        print(f"Ошибка Maven: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    for line in format_graph(graph):
        print(line)
    return EXIT_SUCCESS
