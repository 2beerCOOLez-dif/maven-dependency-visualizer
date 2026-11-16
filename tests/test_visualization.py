"""Проверки DOT, запуска Graphviz, сохранения и открытия изображения."""

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from dependency_visualizer.cli import EXIT_VISUALIZATION_ERROR, main
from dependency_visualizer.graph import build_graph
from dependency_visualizer.visualization import (
    VisualizationError, create_visualization, open_image, render_svg, to_dot,
)

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ROOT_NODE_COUNT = 1


class DotTests(unittest.TestCase):
    """Проверить направление связей и сохранение всех типов вершин."""

    def test_diamond(self):
        """Сохранить все ребра ромба и одну общую вершину."""
        source = {"A": ("B", "C"), "B": ("D",), "C": ("D",), "D": ()}
        graph = build_graph("A", source.__getitem__)
        dot = to_dot(graph)
        self.assertTrue(dot.startswith("digraph dependencies {"))
        self.assertIn("n0 -> n1;", dot)
        self.assertIn("n0 -> n3;", dot)
        self.assertIn("n1 -> n2;", dot)
        self.assertIn("n3 -> n2;", dot)
        self.assertEqual(dot.count('label="D"'), ROOT_NODE_COUNT)
        self.assertIn('label="A", fillcolor="#dbeafe"', dot)

    def test_leaf_and_self_cycle(self):
        """Показать одиночную вершину и выделить петлю красным цветом."""
        leaf = to_dot(build_graph("A", {"A": ()}.__getitem__))
        self.assertIn('label="A"', leaf)
        self.assertNotIn("->", leaf)
        loop = to_dot(build_graph("A", {"A": ("A",)}.__getitem__))
        self.assertIn('n0 -> n0 [color="#dc2626", penwidth=2];', loop)

    def test_cycle(self):
        """Выделить ребра обнаруженного цикла, сохранив другую ветвь."""
        source = {"A": ("B", "D"), "B": ("C",), "C": ("A",), "D": ()}
        dot = to_dot(build_graph("A", source.__getitem__))
        self.assertIn('n0 -> n1 [color="#dc2626", penwidth=2];', dot)
        self.assertIn('n1 -> n2 [color="#dc2626", penwidth=2];', dot)
        self.assertIn('n2 -> n0 [color="#dc2626", penwidth=2];', dot)
        self.assertIn('n0 -> n3;', dot)

    def test_escaped_labels(self):
        """Экранировать кавычки и обратную косую черту в подписи."""
        name = 'Пакет "A" \\ test'
        dot = to_dot(build_graph(name, {name: ()}.__getitem__))
        self.assertIn(f"label={json.dumps(name, ensure_ascii=False)}", dot)


class RenderingTests(unittest.TestCase):
    """Проверить ошибки внешней программы и запуск просмотрщика."""

    def test_missing_graphviz_keeps_dot(self):
        """Сохранить DOT и объяснить отсутствие Graphviz."""
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "graph"
            graph = build_graph("A", {"A": ()}.__getitem__)
            with patch("dependency_visualizer.visualization.shutil.which",
                       return_value=None):
                with self.assertRaisesRegex(VisualizationError, "не найден"):
                    create_visualization(graph, prefix, show=False)
            self.assertTrue(prefix.with_suffix(".dot").is_file())

    def test_renderer_failures(self):
        """Преобразовать сбой, таймаут и ошибку запуска в понятную ошибку."""
        failures = (
            subprocess.CalledProcessError(1, "dot", stderr="invalid DOT"),
            subprocess.TimeoutExpired("dot", 1),
            OSError("unavailable"),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                with patch(
                    "dependency_visualizer.visualization.shutil.which",
                    return_value="dot",
                ), patch(
                    "dependency_visualizer.visualization.subprocess.run",
                    side_effect=failure,
                ):
                    with self.assertRaises(VisualizationError):
                        render_svg(Path("graph.dot"), Path("graph.svg"))

    def test_browser_open(self):
        """Передать абсолютный URI изображения браузеру."""
        path = Path("граф с пробелом.svg")
        with patch("dependency_visualizer.visualization.webbrowser.open",
                   return_value=True) as browser:
            open_image(path)
        browser.assert_called_once_with(path.resolve().as_uri(), new=2)

    def test_browser_failure(self):
        """Сообщить путь к изображению при отсутствии браузера."""
        with patch("dependency_visualizer.visualization.webbrowser.open",
                   return_value=False):
            with self.assertRaisesRegex(VisualizationError, "вручную"):
                open_image(Path("graph.svg"))

    def test_write_failure(self):
        """Обработать невозможность создать каталог результата."""
        graph = build_graph("A", {"A": ()}.__getitem__)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file"
            path.write_text("occupied", encoding="utf-8")
            with self.assertRaisesRegex(VisualizationError, "сохранить DOT"):
                create_visualization(graph, path / "graph", show=False)

    @unittest.skipUnless(shutil.which("dot"), "Graphviz не установлен")
    def test_actual_svg_and_default_open(self):
        """Отрисовать настоящий SVG и по умолчанию открыть просмотрщик."""
        source = {"A": ("B", "C"), "B": ("D",), "C": ("D",), "D": ()}
        graph = build_graph("A", source.__getitem__)
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "папка с пробелом" / "graph"
            target = "dependency_visualizer.visualization.open_image"
            with patch(target) as view:
                dot_path, image_path = create_visualization(graph, prefix)
            view.assert_called_once_with(image_path)
            self.assertEqual(dot_path.read_text("utf-8"), to_dot(graph))
            root = ElementTree.parse(image_path).getroot()
            self.assertEqual(root.tag, f"{{{SVG_NAMESPACE}}}svg")
            nodes = root.findall(f".//{{{SVG_NAMESPACE}}}g[@class='node']")
            self.assertEqual(len(nodes), len(source))

    def test_cli_visualization_failure(self):
        """Вернуть отдельный код ошибки визуализации без частичного вывода."""
        project = Path(__file__).resolve().parent.parent
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("dependency_visualizer.cli.create_visualization",
                   side_effect=VisualizationError("renderer failed")):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main([
                    "--config", str(project / "examples/test.xml"),
                    "--visualize", "--no-open",
                ])
        self.assertEqual(code, EXIT_VISUALIZATION_ERROR)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Ошибка визуализации: renderer failed", stderr.getvalue())
