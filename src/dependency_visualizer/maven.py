"""Загрузка Maven POM по HTTP(S) без менеджеров пакетов и библиотек."""

from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import Artifact, MavenError, PomModel
from .pom import make_dependency, parse_pom
from .pom_model import build_model

REQUEST_TIMEOUT_SECONDS = 15
MAX_POM_BYTES = 2_097_152
READ_OVERFLOW_BYTES = 1
MAX_METADATA_DEPTH = 64
USER_AGENT = "MavenDependencyVisualizer/2"
MAVEN_PARTS_SEPARATOR = ":"


def build_pom_url(repository: str, artifact: Artifact) -> str:
    """Построить URL group/path/artifact/version/artifact-version.pom."""
    group_path = artifact.group_id.replace(".", "/")
    name = quote(artifact.artifact_id, safe="")
    version = quote(artifact.version, safe="")
    return (
        f"{repository.rstrip('/')}/{group_path}/{name}/{version}/"
        f"{name}-{version}.pom"
    )


def download_pom(url: str) -> bytes:
    """Скачать один POM с таймаутом и ограничением размера ответа."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = response.read(MAX_POM_BYTES + READ_OVERFLOW_BYTES)
    except HTTPError as error:
        message = f"HTTP {error.code}: не удалось получить {url}"
        raise MavenError(message) from error
    except (URLError, OSError, HTTPException) as error:
        message = f"Сетевая ошибка при загрузке {url}: {error}"
        raise MavenError(message) from error
    if len(data) > MAX_POM_BYTES:
        raise MavenError(f"POM превышает допустимый размер: {url}")
    return data


class MavenRepository:
    """Чтение метаданных одного репозитория с кешем parent и BOM."""

    def __init__(self, repository: str):
        """Создать кеш моделей и список загружаемых метаданных."""
        self.repository = repository
        self.cache: dict[Artifact, PomModel] = {}
        self.active: set[Artifact] = set()

    def load(self, artifact: Artifact) -> PomModel:
        """Собрать модель, выявив циклы и слишком длинные цепочки POM."""
        if artifact in self.cache:
            return self.cache[artifact]
        if artifact in self.active:
            raise MavenError(f"Цикл parent/BOM: {artifact}")
        if len(self.active) >= MAX_METADATA_DEPTH:
            raise MavenError("Превышена глубина цепочки parent/BOM.")
        self.active.add(artifact)
        try:
            data = download_pom(build_pom_url(self.repository, artifact))
            model = build_model(parse_pom(data), artifact, self.load)
            self.cache[artifact] = model
            return model
        finally:
            self.active.remove(artifact)

    def direct_dependencies(self, package: str, version: str) -> list:
        """Получить прямые зависимости заданной версии, без их обхода."""
        group_id, artifact_id = package.split(MAVEN_PARTS_SEPARATOR)
        model = self.load(Artifact(group_id, artifact_id, version))
        return [make_dependency(raw, model) for raw in model.dependencies]
