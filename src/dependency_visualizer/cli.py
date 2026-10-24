"""Командный интерфейс первого этапа."""

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from .config import ConfigError, load_config

EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1


def create_parser() -> argparse.ArgumentParser:
    """Создать интерфейс выбора единственного источника настроек — XML."""
    parser = argparse.ArgumentParser(
        description="Вариант 25. Этап 1: проверка XML-конфигурации Maven."
    )
    parser.add_argument(
        "--config", required=True, type=Path, metavar="FILE.xml",
        help="путь к XML-конфигурации в UTF-8",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Вывести все настройки либо понятную ошибку с ненулевым кодом."""
    arguments = create_parser().parse_args(argv)
    try:
        config = load_config(arguments.config)
    except ConfigError as error:
        print(f"Ошибка конфигурации: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    for key, value in asdict(config).items():
        formatted = str(value).lower() if isinstance(value, bool) else value
        print(f"{key}={formatted}")
    return EXIT_SUCCESS
