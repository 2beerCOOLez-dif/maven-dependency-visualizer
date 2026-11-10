"""Проверки итеративного DFS, повторных вершин и циклов."""

import unittest

from dependency_visualizer.graph import build_graph, format_graph

DEEP_GRAPH_SIZE = 1500


class GraphTests(unittest.TestCase):
    """Проверить полноту ребер и отличие общей вершины от цикла."""

    def test_depth_first_order(self):
        """Обойти первую ветвь целиком до перехода к следующей."""
        source = {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
        graph = build_graph("A", source.__getitem__)
        self.assertEqual(list(graph.adjacency), ["A", "B", "D", "C"])
        self.assertEqual(graph.adjacency["A"], ("B", "C"))

    def test_shared_dependency(self):
        """Загрузить общую зависимость один раз, сохранив оба ребра."""
        source = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
        calls = []

        def neighbors(node):
            """Записать порядок обращений к источнику."""
            calls.append(node)
            return source[node]

        graph = build_graph("A", neighbors)
        self.assertEqual(calls, ["A", "B", "D", "C"])
        self.assertEqual(graph.adjacency["B"], ("D",))
        self.assertEqual(graph.adjacency["C"], ("D",))
        self.assertEqual(graph.cycles, [])

    def test_cycle_keeps_other_branches(self):
        """Замкнуть цикл и продолжить обход остальных зависимостей."""
        source = {"A": ["B"], "B": ["C", "D"], "C": ["A"], "D": []}
        graph = build_graph("A", source.__getitem__)
        self.assertEqual(graph.cycles, [("A", "B", "C", "A")])
        self.assertEqual(graph.adjacency["C"], ("A",))
        self.assertIn("D", graph.adjacency)

    def test_self_cycle(self):
        """Сохранить петлю и не загружать вершину повторно."""
        graph = build_graph("A", {"A": ["A"]}.__getitem__)
        self.assertEqual(graph.cycles, [("A", "A")])
        self.assertIn("Цикл: A -> A", list(format_graph(graph)))

    def test_several_cycles(self):
        """Найти обратные ребра в двух разных ветвях."""
        source = {"A": ["B", "C"], "B": ["A"], "C": ["C"]}
        graph = build_graph("A", source.__getitem__)
        self.assertEqual(graph.cycles, [("A", "B", "A"), ("C", "C")])

    def test_isolated_root_and_unreachable_node(self):
        """Включить корень и исключить недостижимый компонент."""
        graph = build_graph("A", {"A": [], "Z": ["Z"]}.__getitem__)
        self.assertEqual(graph.adjacency, {"A": ()})
        self.assertEqual(graph.cycles, [])

    def test_repeated_edges(self):
        """Убрать повторы одного ребра без изменения порядка."""
        graph = build_graph("A", {"A": ["B", "B"], "B": []}.__getitem__)
        self.assertEqual(graph.adjacency, {"A": ("B",), "B": ()})

    def test_deep_graph(self):
        """Пройти цепочку длиннее обычного предела рекурсии Python."""
        source = {str(i): [str(i + 1)] for i in range(DEEP_GRAPH_SIZE)}
        source[str(DEEP_GRAPH_SIZE)] = []
        graph = build_graph("0", source.__getitem__)
        self.assertEqual(len(graph.adjacency), len(source))
        self.assertEqual(graph.cycles, [])
