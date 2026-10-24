"""Командный интерфейс получения прямых зависимостей Maven."""

import argparse
import sys
from pathlib import Path

from .config import ConfigError, load_config
from .maven import MavenRepository
from .models import MavenError

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_MAVEN_ERROR = 3


def create_parser() -> argparse.ArgumentParser:
    """Создать интерфейс выбора единственного источника настроек — XML."""
    parser = argparse.ArgumentParser(
        description="Вариант 25. Этап 2: прямые зависимости Maven-пакета."
    )
    parser.add_argument(
        "--config", required=True, type=Path, metavar="FILE.xml",
        help="путь к XML-конфигурации в UTF-8",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Вывести прямые зависимости или сообщение об ошибке."""
    arguments = create_parser().parse_args(argv)
    try:
        config = load_config(arguments.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    try:
        if config.test_mode:
            raise MavenError(
                "Сбор зависимостей из тестового графа относится к этапу 3."
            )
        dependencies = MavenRepository(config.repository).direct_dependencies(
            config.package, config.version
        )
    except MavenError as error:
        print(f"Ошибка Maven: {error}", file=sys.stderr)
        return EXIT_MAVEN_ERROR
    if not dependencies:
        print("Прямые зависимости не найдены.")
    for dependency in dependencies:
        print(dependency)
    return EXIT_SUCCESS
