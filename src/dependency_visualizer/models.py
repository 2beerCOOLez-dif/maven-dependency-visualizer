"""Модели Maven-координат, зависимостей и содержимого POM."""

from dataclasses import dataclass, field

from .validation import ConfigError, validate_package, validate_version

DEFAULT_TYPE = "jar"
DEFAULT_SCOPE = "compile"
DEPENDENCY_SCOPES = frozenset({
    "compile", "provided", "runtime", "test", "system",
})


class MavenError(ValueError):
    """Ошибка загрузки или интерпретации метаданных Maven."""


@dataclass(frozen=True)
class Artifact:
    """Точные координаты POM: группа, артефакт и версия."""

    group_id: str
    artifact_id: str
    version: str

    def __post_init__(self):
        """Запретить некорректные координаты и пути из полученного POM."""
        try:
            validate_package(f"{self.group_id}:{self.artifact_id}", False)
            validate_version(self.version)
        except ConfigError as error:
            raise MavenError(str(error)) from error

    def __str__(self) -> str:
        """Представить координаты строкой groupId:artifactId:version."""
        return f"{self.group_id}:{self.artifact_id}:{self.version}"


@dataclass(frozen=True)
class Dependency:
    """Прямая зависимость с областью использования и типом артефакта."""

    artifact: Artifact
    scope: str = DEFAULT_SCOPE
    optional: bool = False
    artifact_type: str = DEFAULT_TYPE
    classifier: str = ""

    def __str__(self) -> str:
        """Сформировать строку вывода с существенными атрибутами."""
        attributes = f"scope={self.scope}, type={self.artifact_type}"
        if self.classifier:
            attributes += f", classifier={self.classifier}"
        if self.optional:
            attributes += ", optional=true"
        return f"{self.artifact} [{attributes}]"


@dataclass
class PomModel:
    """Свойства, управляемые версии и объявления прямых зависимостей."""

    properties: dict[str, str] = field(default_factory=dict)
    management: dict[tuple, dict[str, str]] = field(default_factory=dict)
    dependencies: list[dict[str, str]] = field(default_factory=list)
