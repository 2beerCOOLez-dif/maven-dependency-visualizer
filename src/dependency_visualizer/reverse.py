"""Поиск прямых и транзитивных обратных зависимостей через прежний DFS."""

from .graph import build_graph
from .test_repository import GraphError


def reverse_edges(
    adjacency: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    """Развернуть каждое ребро, сохранив также изолированные вершины."""
    incoming = {node: [] for node in adjacency}
    for source, targets in adjacency.items():
        for target in targets:
            incoming.setdefault(target, []).append(source)
    return {
        node: tuple(dict.fromkeys(parents))
        for node, parents in incoming.items()
    }


def find_reverse_dependencies(
    adjacency: dict[str, tuple[str, ...]], target: str,
) -> tuple[str, ...]:
    """Найти всех потребителей, исключив сам пакет даже внутри цикла."""
    reversed_adjacency = reverse_edges(adjacency)
    if target not in reversed_adjacency:
        raise GraphError(f"Пакет {target} отсутствует в анализируемом графе.")
    traversal = build_graph(target, reversed_adjacency.__getitem__)
    return tuple(sorted(
        node for node in traversal.adjacency if node != target
    ))
