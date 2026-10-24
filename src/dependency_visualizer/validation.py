"""Проверка пользовательских значений без сетевых запросов."""

import re
from pathlib import Path
from urllib.parse import urlsplit

MAVEN_NAME = r"[A-Za-z0-9_]+(?:[.-][A-Za-z0-9_]+)*"
MAVEN_PACKAGE = rf"{MAVEN_NAME}:{MAVEN_NAME}"
TEST_PACKAGE = r"[A-Z]+"
VERSION = r"[A-Za-z0-9][A-Za-z0-9_.+\-]*"
ALLOWED_SCHEMES = frozenset({"http", "https"})


class ConfigError(ValueError):
    """Ошибка структуры конфигурации или значения параметра."""


def validate_package(value: str, test_mode: bool) -> str:
    """Проверить координаты Maven либо тестовое имя пакета."""
    pattern = TEST_PACKAGE if test_mode else MAVEN_PACKAGE
    if not re.fullmatch(pattern, value):
        expected = "заглавные буквы A–Z" if test_mode else "groupId:artifactId"
        raise ConfigError(f"package: ожидается {expected}.")
    return value


def validate_version(value: str) -> str:
    """Проверить явную версию; диапазоны и пробелы не поддерживаются."""
    if not re.fullmatch(VERSION, value):
        raise ConfigError(
            "version: ожидается версия из латинских букв, цифр, . _ + -; "
            "первый символ — буква или цифра."
        )
    return value


def parse_test_mode(value: str) -> bool:
    """Принять только явно заданные XML-значения true или false."""
    values = {"true": True, "false": False}
    if value not in values:
        raise ConfigError("test_mode: допустимы только true и false.")
    return values[value]


def validate_url(value: str) -> str:
    """Проверить HTTP(S) URL репозитория, не проверяя доступность сети."""
    try:
        url = urlsplit(value)
        url.port
        valid = all((
            url.scheme in ALLOWED_SCHEMES,
            bool(url.hostname),
            url.username is None,
            url.password is None,
            not url.query,
            not url.fragment,
            not any(character.isspace() for character in value),
            "\\" not in value,
        ))
    except ValueError as error:
        raise ConfigError(f"repository: некорректный URL: {error}.") from error
    if not valid:
        raise ConfigError(
            "repository: нужен HTTP(S) URL без пробелов, учетных данных, "
            "query и fragment."
        )
    return value


def validate_repository(value: str, test_mode: bool, base: Path) -> str:
    """Проверить URL либо существующий читаемый файл относительно XML."""
    if not test_mode:
        return validate_url(value)
    try:
        path = (base / value).resolve()
        if not path.is_file():
            raise ConfigError("repository: тестовый файл не найден.")
        with path.open("rb"):
            pass
    except (OSError, ValueError, RuntimeError) as error:
        message = f"repository: не удалось открыть файл: {error}"
        raise ConfigError(message) from error
    return str(path)
