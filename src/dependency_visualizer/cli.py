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
from .visualization import (
    DEFAULT_OUTPUT, VisualizationError, create_visualization,
)

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_MAVEN_ERROR = 3
EXIT_VISUALIZATION_ERROR = 4


def create_parser() -> argparse.ArgumentParser:
    """Создать интерфейс выбора единственного источника настроек — XML."""
    parser = argparse.ArgumentParser(
        description="Вариант 25. Этап 5: визуализация графа через Graphviz."
    )
    parser.add_argument(
        "--config", required=True, type=Path, metavar="FILE.xml",
        help="путь к XML-конфигурации в UTF-8",
    )
    add_operation_arguments(parser)
    return parser


def add_operation_arguments(parser: argparse.ArgumentParser) -> None:
    """Добавить выбор операции и параметры сохранения изображения."""
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument(
        "--reverse", metavar="PACKAGE",
        help=(
            "прямые и косвенные потребители; тест: весь файл, Maven: граф "
            "корня; цель A либо groupId:artifactId:version"
        ),
    )
    operations.add_argument(
        "--visualize", action="store_true", help="сохранить DOT и открыть SVG",
    )
    parser.add_argument(
        "--output", type=Path, metavar="PREFIX",
        help="префикс файлов .dot и .svg (по умолчанию output/dependencies)",
    )
    parser.add_argument(
        "--no-open", action="store_true", help="сохранить SVG без браузера",
    )


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    """Проверить, что параметры изображения используются с --visualize."""
    parser = create_parser()
    arguments = parser.parse_args(argv)
    if not arguments.visualize and (
        arguments.output is not None or arguments.no_open
    ):
        parser.error("--output и --no-open требуют --visualize")
    return arguments


def operation_lines(
    config: Config, arguments: argparse.Namespace,
) -> Iterable[str]:
    """Полностью выполнить операцию до начала вывода результата."""
    if arguments.visualize:
        dot_path, image_path = create_visualization(
            collect_graph(config), arguments.output or DEFAULT_OUTPUT,
            show=not arguments.no_open,
        )
        return (f"Graphviz: {dot_path}", f"Изображение: {image_path}")
    target = arguments.reverse
    if target is None:
        return format_graph(collect_graph(config))
    dependencies = collect_reverse_dependencies(config, target)
    lines = [f"Обратные зависимости для {target}:"]
    lines.extend(dependencies or ("Обратные зависимости не найдены.",))
    return lines


def main(argv: list[str] | None = None) -> int:
    """Вывести граф, обратные зависимости либо ошибку без части ответа."""
    arguments = parse_arguments(argv)
    try:
        config = load_config(arguments.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        lines = operation_lines(config, arguments)
    except GraphError as error:
        print(f"Ошибка графа: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    except MavenError as error:
        print(f"Ошибка Maven: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    except VisualizationError as error:
        print(f"Ошибка визуализации: {error}", file=sys.stderr)
        return EXIT_VISUALIZATION_ERROR
    for line in lines:
        print(line)
    return EXIT_SUCCESS
