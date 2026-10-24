"""Локальный HTTP-репозиторий для автономных интеграционных тестов."""

import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from xml.etree import ElementTree

from dependency_visualizer.maven import build_pom_url
from dependency_visualizer.pom import POM_NAMESPACE

AUTO_PORT = 0
POLL_INTERVAL_SECONDS = 0.01
THREAD_JOIN_TIMEOUT_SECONDS = 5


class QuietHandler(SimpleHTTPRequestHandler):
    """Обработчик статических POM с учетом выполненных запросов."""

    def log_message(self, format, *args):
        """Отключить служебные HTTP-сообщения во время тестов."""
        pass

    def do_GET(self):
        """Записать путь запроса и отдать файл стандартным обработчиком."""
        self.server.requests.append(self.path)
        super().do_GET()


class LocalRepository:
    """Временные файлы Maven и HTTP-сервер на свободном порту."""

    def __enter__(self):
        """Создать временную директорию и запустить сервер в потоке."""
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        handler = partial(QuietHandler, directory=str(self.root))
        self.server = ThreadingHTTPServer(("127.0.0.1", AUTO_PORT), handler)
        self.server.requests = []
        host, port = self.server.server_address
        self.url = f"http://{host}:{port}"
        self.thread = Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": POLL_INTERVAL_SECONDS}, daemon=True,
        )
        self.thread.start()
        return self

    def __exit__(self, *error):
        """Остановить сервер, закрыть сокет и удалить временные файлы."""
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)
        self.temporary.cleanup()

    def put(self, artifact, body="", namespace=True):
        """Разместить POM с указанными координатами в структуре Maven."""
        prefix = f' xmlns="{POM_NAMESPACE}"' if namespace else ""
        text = (
            f"<project{prefix}><modelVersion>4.0.0</modelVersion>"
            f"<groupId>{artifact.group_id}</groupId>"
            f"<artifactId>{artifact.artifact_id}</artifactId>"
            f"<version>{artifact.version}</version>{body}</project>"
        )
        path = self.root / build_pom_url("", artifact).lstrip("/")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def config(self, package="org.example:demo", version="1.0") -> Path:
        """Создать XML-конфигурацию, указывающую на локальный сервер."""
        path = self.root / "config.xml"
        root = ElementTree.Element("configuration")
        values = {
            "package": package, "repository": self.url,
            "test_mode": "false", "version": version,
        }
        for key, value in values.items():
            ElementTree.SubElement(root, key).text = value
        ElementTree.ElementTree(root).write(path, encoding="utf-8")
        return path
