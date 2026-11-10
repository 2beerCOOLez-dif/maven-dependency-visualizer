"""Чтение локального тестового репозитория в формате A: B C."""

import re
from pathlib import Path

from .validation import TEST_PACKAGE

FIRST_LINE_NUMBER = 1


class GraphError(ValueError):
    """Ошибка формата или неполное описание тестового репозитория."""


def parse_line(line: str, number: int) -> tuple[str, tuple[str, ...]]:
    """Разобрать одну непустую строку с единственным двоеточием."""
    node, separator, tail = line.partition(":")
    node = node.strip()
    children = tail.split()
    names = [node, *children]
    valid_names = all(re.fullmatch(TEST_PACKAGE, name) for name in names)
    if not separator or not valid_names:
        raise GraphError(f"Строка {number}: ожидается A: B C, имена A–Z.")
    return node, tuple(dict.fromkeys(children))


def parse_repository(text: str) -> dict[str, tuple[str, ...]]:
    """Проверить имена, уникальность строк и наличие всех вершин."""
    adjacency = {}
    for number, line in enumerate(text.splitlines(), FIRST_LINE_NUMBER):
        if not line.strip():
            continue
        node, children = parse_line(line, number)
        if node in adjacency:
            raise GraphError(f"Строка {number}: пакет {node} указан повторно.")
        adjacency[node] = children
    if not adjacency:
        raise GraphError("Тестовый репозиторий пуст.")
    referenced = {
        child for children in adjacency.values() for child in children
    }
    missing = referenced - adjacency.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise GraphError(f"Не описаны пакеты: {names}. Добавьте строки NAME:.")
    return adjacency


class FileRepository:
    """Проверенный граф без сетевых запросов и версий отдельных пакетов."""

    def __init__(self, path: Path):
        """Прочитать UTF-8 файл, разрешив BOM и пустые строки."""
        try:
            self.adjacency = parse_repository(path.read_text("utf-8-sig"))
        except (OSError, UnicodeError) as error:
            raise GraphError(f"Не удалось прочитать граф: {error}") from error

    def neighbors(self, node: str) -> tuple[str, ...]:
        """Вернуть зависимости или сообщить об отсутствующем корне."""
        if node not in self.adjacency:
            message = f"Пакет {node} отсутствует в тестовом репозитории."
            raise GraphError(message)
        return self.adjacency[node]
