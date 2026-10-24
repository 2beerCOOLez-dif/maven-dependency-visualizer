"""Запуск тестов из любого каталога без ручной настройки PYTHONPATH."""

import sys
import unittest
from pathlib import Path

PROJECT_DIRECTORY = Path(__file__).resolve().parent
SOURCE_PATH_POSITION = 0
TEST_VERBOSITY = 2
EXIT_SUCCESS = 0
EXIT_TEST_FAILURE = 1


def main() -> int:
    """Добавить src в пути импорта, обнаружить и выполнить тесты."""
    sys.path.insert(SOURCE_PATH_POSITION, str(PROJECT_DIRECTORY / "src"))
    suite = unittest.defaultTestLoader.discover(
        str(PROJECT_DIRECTORY / "tests")
    )
    result = unittest.TextTestRunner(verbosity=TEST_VERBOSITY).run(suite)
    return EXIT_SUCCESS if result.wasSuccessful() else EXIT_TEST_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())
