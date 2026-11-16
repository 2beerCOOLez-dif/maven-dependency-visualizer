"""Формирование Graphviz DOT, отрисовка SVG и показ изображения."""

import json
import shutil
import subprocess
import webbrowser
from pathlib import Path

from .graph import DependencyGraph

RENDER_TIMEOUT_SECONDS = 60
DEFAULT_OUTPUT = Path("output/dependencies")


class VisualizationError(ValueError):
    """Ошибка сохранения, отрисовки или открытия изображения графа."""


def to_dot(graph: DependencyGraph) -> str:
    """Описать вершины и ребра; выделить корень и найденные DFS циклы."""
    identifiers = {node: f"n{index}" for index, node in
                   enumerate(graph.adjacency)}
    cycle_edges = {
        (source, target) for cycle in graph.cycles
        for source, target in zip(cycle, cycle[1:])
    }
    lines = [
        "digraph dependencies {",
        '  graph [rankdir=TB, bgcolor="white", pad="0.3"];',
        '  node [shape=box, style="rounded,filled", fontname="Arial",',
        '        fontsize=11, fillcolor="#f8fafc", color="#475569"];',
        '  edge [color="#475569"];',
    ]
    for node, identifier in identifiers.items():
        label = json.dumps(node, ensure_ascii=False)
        color = ', fillcolor="#dbeafe"' if node == graph.root else ""
        lines.append(f"  {identifier} [label={label}{color}];")
    for source, targets in graph.adjacency.items():
        for target in targets:
            color = ' [color="#dc2626", penwidth=2]' if (
                source, target
            ) in cycle_edges else ""
            edge = f"{identifiers[source]} -> {identifiers[target]}"
            lines.append(f"  {edge}{color};")
    return "\n".join([*lines, "}", ""])


def render_svg(dot_path: Path, image_path: Path) -> None:
    """Вызвать установленный Graphviz через список аргументов без shell."""
    executable = shutil.which("dot")
    if executable is None:
        raise VisualizationError(
            "Graphviz не найден. Установите его и добавьте dot в PATH. "
            f"Текст графа сохранен: {dot_path}"
        )
    try:
        subprocess.run(
            [executable, "-Tsvg", str(dot_path), "-o", str(image_path)],
            check=True, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=RENDER_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as error:
        raise VisualizationError(f"Ошибка Graphviz: {error.stderr}") from error
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VisualizationError(f"Не удалось запустить Graphviz: {error}")


def open_image(image_path: Path) -> None:
    """Открыть SVG в браузере, сообщив путь при отсутствии просмотрщика."""
    try:
        opened = webbrowser.open(image_path.resolve().as_uri(), new=2)
    except (OSError, webbrowser.Error) as error:
        raise VisualizationError(f"Не удалось открыть {image_path}: {error}")
    if not opened:
        raise VisualizationError(
            f"Изображение сохранено: {image_path}. Откройте его вручную "
            "или используйте --no-open."
        )


def create_visualization(
    graph: DependencyGraph, output: Path, show: bool = True,
) -> tuple[Path, Path]:
    """Сохранить DOT и SVG с заданным префиксом и показать готовый граф."""
    dot_path = Path(f"{output}.dot").resolve()
    image_path = Path(f"{output}.svg").resolve()
    try:
        dot_path.parent.mkdir(parents=True, exist_ok=True)
        dot_path.write_text(to_dot(graph), encoding="utf-8")
    except OSError as error:
        message = f"Не удалось сохранить DOT: {error}"
        raise VisualizationError(message) from error
    render_svg(dot_path, image_path)
    if show:
        open_image(image_path)
    return dot_path, image_path
