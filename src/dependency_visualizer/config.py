"""Чтение строгой XML-конфигурации приложения."""

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from .validation import (
    ConfigError,
    parse_test_mode,
    validate_package,
    validate_repository,
    validate_version,
)

ROOT_TAG = "configuration"
FIELDS = ("package", "repository", "test_mode", "version")


@dataclass(frozen=True)
class Config:
    """Проверенные настройки; repository в тестовом режиме — полный путь."""

    package: str
    repository: str
    test_mode: bool
    version: str


def read_xml(path: Path) -> ElementTree.Element:
    """Прочитать UTF-8 XML, запретив DTD и объявления сущностей."""
    try:
        text = path.read_text(encoding="utf-8-sig")
        if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
            raise ConfigError("XML: DTD и сущности запрещены.")
        return ElementTree.fromstring(text)
    except (OSError, UnicodeError, ValueError, ElementTree.ParseError) as error:
        message = f"Не удалось прочитать XML {path}: {error}"
        raise ConfigError(message) from error


def validate_root(root: ElementTree.Element) -> None:
    """Проверить корневой элемент и отсутствие постороннего текста."""
    if root.tag != ROOT_TAG or root.attrib:
        raise ConfigError("XML: нужен корень <configuration> без атрибутов.")
    if root.text and root.text.strip():
        raise ConfigError("XML: текст между параметрами запрещен.")


def read_field(child: ElementTree.Element) -> str:
    """Проверить известное простое поле и извлечь непустой текст."""
    if child.tag not in FIELDS:
        raise ConfigError(f"XML: неизвестный параметр {child.tag}.")
    if child.attrib or list(child):
        raise ConfigError(f"{child.tag}: нужен текст без вложенных тегов.")
    if child.tail and child.tail.strip():
        raise ConfigError("XML: текст между параметрами запрещен.")
    value = (child.text or "").strip()
    if not value:
        raise ConfigError(f"{child.tag}: значение не должно быть пустым.")
    return value


def extract_fields(root: ElementTree.Element) -> dict[str, str]:
    """Проверить уникальность и наличие всех полей конфигурации."""
    validate_root(root)
    values = {}
    for child in root:
        if child.tag in values:
            raise ConfigError(f"{child.tag}: параметр указан повторно.")
        values[child.tag] = read_field(child)
    missing = set(FIELDS) - values.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise ConfigError(f"XML: отсутствуют параметры: {names}.")
    return values


def load_config(path: Path) -> Config:
    """Загрузить и проверить все четыре параметра конфигурации."""
    values = extract_fields(read_xml(path))
    test_mode = parse_test_mode(values["test_mode"])
    return Config(
        package=validate_package(values["package"], test_mode),
        repository=validate_repository(
            values["repository"], test_mode, path.absolute().parent
        ),
        test_mode=test_mode,
        version=validate_version(values["version"]),
    )
