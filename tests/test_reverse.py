"""Проверки разворота ребер и нерекурсивного поиска потребителей."""

import unittest

from dependency_visualizer.reverse import (
    find_reverse_dependencies, reverse_edges,
)
from dependency_visualizer.test_repository import GraphError

DEEP_GRAPH_SIZE = 1500


class ReverseTests(unittest.TestCase):
    """Проверить направление ребер, транзитивность и завершение в циклах."""

    def test_reverse_edges(self):
        """Развернуть каждое ребро и сохранить изолированную вершину."""
        source = {"A": ("B", "C"), "B": ("C",), "C": (), "Z": ()}
        self.assertEqual(reverse_edges(source), {
            "A": (), "B": ("A",), "C": ("A", "B"), "Z": (),
        })

    def test_chain(self):
        """Найти прямого и косвенного потребителей листа цепочки."""
        source = {"A": ("B",), "B": ("C",), "C": ()}
        self.assertEqual(find_reverse_dependencies(source, "C"), ("A", "B"))
        self.assertEqual(find_reverse_dependencies(source, "B"), ("A",))

    def test_direction_and_no_consumers(self):
        """Не принять исходящие зависимости за обратные."""
        source = {"A": ("B",), "B": (), "Z": ()}
        self.assertEqual(find_reverse_dependencies(source, "A"), ())
        self.assertEqual(find_reverse_dependencies(source, "Z"), ())

    def test_diamond_and_other_root(self):
        """Не потерять общий пакет и потребителя из другой ветви."""
        source = {
            "A": ("B", "C"), "B": ("D",), "C": ("D",),
            "D": (), "E": ("D",), "F": (),
        }
        self.assertEqual(
            find_reverse_dependencies(source, "D"), ("A", "B", "C", "E")
        )

    def test_cycle(self):
        """Завершить цикл и исключить целевую вершину из результата."""
        source = {"A": ("B",), "B": ("C",), "C": ("A",), "D": ("A",)}
        self.assertEqual(
            find_reverse_dependencies(source, "A"), ("B", "C", "D")
        )

    def test_self_cycle(self):
        """Не считать целевой пакет своим собственным потребителем."""
        self.assertEqual(find_reverse_dependencies({"A": ("A",)}, "A"), ())

    def test_duplicates_and_unchanged_source(self):
        """Удалить повтор ребра, не изменяя исходный граф."""
        source = {"A": ("B", "B"), "B": ()}
        self.assertEqual(find_reverse_dependencies(source, "B"), ("A",))
        self.assertEqual(source, {"A": ("B", "B"), "B": ()})

    def test_missing_target(self):
        """Сообщить об неизвестном пакете, включая пустой граф."""
        for source in ({}, {"A": ()}):
            with self.subTest(source=source):
                with self.assertRaisesRegex(GraphError, "Z отсутствует"):
                    find_reverse_dependencies(source, "Z")

    def test_deep_chain(self):
        """Найти всех предков в цепочке из 1501 вершины без рекурсии."""
        source = {
            str(number): (str(number + 1),)
            for number in range(DEEP_GRAPH_SIZE)
        }
        source[str(DEEP_GRAPH_SIZE)] = ()
        result = find_reverse_dependencies(source, str(DEEP_GRAPH_SIZE))
        self.assertEqual(set(result), {str(n) for n in range(DEEP_GRAPH_SIZE)})
