"""Командный интерфейс построения графа зависимостей."""

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

from .config import Config, ConfigError, load_config
from .graph import format_graph
from .models import MavenError
from .operations import collect_graph, collect_reverse_dependencies
from .test_repository import GraphError

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_MAVEN_ERROR = 3


def create_parser() -> argparse.ArgumentParser:
    """Создать интерфейс выбора единственного источника настроек — XML."""
    parser = argparse.ArgumentParser(
        description="Вариант 25. Этап 4: граф и обратные зависимости, DFS."
    )
    parser.add_argument(
        "--config", required=True, type=Path, metavar="FILE.xml",
        help="путь к XML-конфигурации в UTF-8",
    )
    parser.add_argument(
        "--reverse", metavar="PACKAGE",
        help=(
            "прямые и косвенные потребители; тест: весь файл, Maven: граф "
            "корня; цель A либо groupId:artifactId:version"
        ),
    )
    return parser


def operation_lines(config: Config, target: str | None) -> Iterable[str]:
    """Полностью выполнить операцию до начала вывода результата."""
    if target is None:
        return format_graph(collect_graph(config))
    dependencies = collect_reverse_dependencies(config, target)
    lines = [f"Обратные зависимости для {target}:"]
    lines.extend(dependencies or ("Обратные зависимости не найдены.",))
    return lines


def main(argv: list[str] | None = None) -> int:
    """Вывести граф, обратные зависимости либо ошибку без части ответа."""
    arguments = create_parser().parse_args(argv)
    try:
        config = load_config(arguments.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        lines = operation_lines(config, arguments.reverse)
    except GraphError as error:
        print(f"Ошибка графа: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    except MavenError as error:
        print(f"Ошибка Maven: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    for line in lines:
        print(line)
    return EXIT_SUCCESS
