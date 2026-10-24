"""Наследование POM, свойства и управление версиями зависимостей."""

from .models import Artifact, MavenError, PomModel
from .pom import (
    dependency_key, expand, expand_fields, field_text, read_artifact,
    read_dependencies, read_properties,
)


def project_properties(artifact: Artifact, parent, properties: dict) -> dict:
    """Добавить project.*, pom.* и короткие имена координат проекта."""
    result = dict(properties)
    coordinates = {
        "groupId": artifact.group_id, "artifactId": artifact.artifact_id,
        "version": artifact.version,
    }
    for name, value in coordinates.items():
        for prefix in ("", "project.", "pom."):
            result[prefix + name] = value
    if parent is not None:
        parent_fields = {
            "groupId": parent.group_id, "artifactId": parent.artifact_id,
            "version": parent.version,
        }
        for name, value in parent_fields.items():
            for prefix in ("project.parent.", "pom.parent.", "parent."):
                result[prefix + name] = value
    return result


def merge_dependencies(
    inherited: list, declared: list, properties: dict,
) -> list:
    """Объединить объявления; дочернее заменяет одноименное родительское."""
    result = {}
    for raw in inherited + declared:
        key = dependency_key(expand_fields(raw, properties))
        result[key] = {**result.get(key, {}), **{
            name: value for name, value in raw.items() if value
        }}
    return list(result.values())


def resolve_management(root, model: PomModel, load) -> dict:
    """Объединить parent, импортированные BOM и собственные определения."""
    imported = {}
    local = {}
    declarations = read_dependencies(
        root, "dependencyManagement/dependencies/dependency"
    )
    for raw in declarations:
        values = expand_fields(raw, model.properties)
        if values["scope"] == "import" and values["type"] == "pom":
            bom = load(Artifact(
                values["groupId"], values["artifactId"], values["version"]
            ))
            for entry in bom.management.values():
                resolved = expand_fields(entry, bom.properties)
                imported.setdefault(dependency_key(resolved), resolved)
        else:
            local[dependency_key(values)] = raw
    return {**model.management, **imported, **local}


def check_identity(root, artifact: Artifact, properties: dict) -> None:
    """Убедиться, что скачанный POM описывает запрошенный пакет и версию."""
    declared = {
        "groupId": artifact.group_id, "artifactId": artifact.artifact_id,
        "version": artifact.version,
    }
    for name, expected in declared.items():
        actual = field_text(root, name)
        if actual and expand(actual, properties) != expected:
            raise MavenError(f"POM: {name} не соответствует {artifact}.")
    if not field_text(root, "artifactId"):
        raise MavenError("POM: отсутствует artifactId.")
    if root.find("distributionManagement/relocation") is not None:
        raise MavenError("POM: перенесенные артефакты пока не поддерживаются.")


def build_model(root, artifact: Artifact, load) -> PomModel:
    """Загрузить parent и собрать сведения только об одном проекте."""
    own_properties = read_properties(root)
    parent_element = root.find("parent")
    parent_artifact = None
    parent_model = PomModel()
    if parent_element is not None:
        parent_artifact = read_artifact(parent_element, own_properties)
        parent_model = load(parent_artifact)
    properties = project_properties(artifact, parent_artifact, {
        **parent_model.properties, **own_properties,
    })
    check_identity(root, artifact, properties)
    model = PomModel(properties, dict(parent_model.management))
    model.management = resolve_management(root, model, load)
    model.dependencies = merge_dependencies(
        parent_model.dependencies,
        read_dependencies(root, "dependencies/dependency"), properties,
    )
    return model
