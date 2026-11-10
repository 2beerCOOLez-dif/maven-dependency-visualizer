"""Построение ориентированного графа итеративным обходом в глубину."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field


@dataclass
class DependencyGraph:
    """Достижимые вершины, ребра и циклы, найденные обратными ребрами DFS."""

    root: str
    adjacency: dict[str, tuple[str, ...]] = field(default_factory=dict)
    cycles: list[tuple[str, ...]] = field(default_factory=list)


def build_graph(
    root: str, neighbors: Callable[[str], Iterable[str]],
) -> DependencyGraph:
    """Обойти каждый пакет один раз, сохранив ребра и замкнутые пути."""
    graph = DependencyGraph(root)
    graph.adjacency[root] = tuple(dict.fromkeys(neighbors(root)))
    path = [root]
    active = {root: 0}
    stack = [iter(graph.adjacency[root])]
    while stack:
        child = next(stack[-1], None)
        if child is None:
            stack.pop()
            del active[path.pop()]
        elif child in active:
            graph.cycles.append(tuple(path[active[child]:] + [child]))
        elif child not in graph.adjacency:
            graph.adjacency[child] = tuple(dict.fromkeys(neighbors(child)))
            active[child] = len(path)
            path.append(child)
            stack.append(iter(graph.adjacency[child]))
    return graph


def format_graph(graph: DependencyGraph) -> Iterable[str]:
    """Выдать список смежности в порядке DFS и найденные циклы."""
    yield f"Корень: {graph.root}"
    for node, children in graph.adjacency.items():
        yield f"{node} -> {', '.join(children) if children else 'нет'}"
    if not graph.cycles:
        yield "Циклы не обнаружены."
    for cycle in graph.cycles:
        yield "Цикл: " + " -> ".join(cycle)
