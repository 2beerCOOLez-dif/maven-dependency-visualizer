"""Разбор POM и раскрытие свойств средствами стандартной библиотеки."""

import re
from xml.etree import ElementTree

from .models import (
    Artifact, DEFAULT_SCOPE, DEFAULT_TYPE, DEPENDENCY_SCOPES,
    Dependency, MavenError,
)

POM_NAMESPACE = "http://maven.apache.org/POM/4.0.0"
PROPERTY_PATTERN = re.compile(r"\$\{([^{}]+)\}")
PROPERTY_NAME_GROUP = 1
MAX_PROPERTY_PASSES = 32
DEPENDENCY_FIELDS = (
    "groupId", "artifactId", "version", "scope", "optional", "type",
    "classifier",
)


def parse_pom(data: bytes) -> ElementTree.Element:
    """Прочитать UTF-8 POM, запретить DTD и убрать Maven namespace."""
    try:
        text = data.decode("utf-8-sig")
        if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
            raise MavenError("POM: DTD и сущности запрещены.")
        root = ElementTree.fromstring(text)
    except (UnicodeError, ElementTree.ParseError) as error:
        raise MavenError(f"POM: некорректный UTF-8 XML: {error}") from error
    for element in root.iter():
        element.tag = element.tag.removeprefix(f"{{{POM_NAMESPACE}}}")
    if root.tag != "project":
        raise MavenError("POM: ожидается корневой элемент project.")
    if field_text(root, "modelVersion") != "4.0.0":
        raise MavenError("POM: поддерживается modelVersion 4.0.0.")
    return root


def field_text(element: ElementTree.Element, name: str) -> str:
    """Получить текст непосредственного поля либо пустую строку."""
    return (element.findtext(name) or "").strip()


def expand(value: str, properties: dict[str, str]) -> str:
    """Раскрыть вложенные свойства, обнаружив цикл или неизвестное имя."""
    seen = set()

    def replace(match: re.Match) -> str:
        """Подставить одно известное свойство."""
        name = match.group(PROPERTY_NAME_GROUP)
        if name not in properties:
            raise MavenError(f"POM: неизвестное свойство ${{{name}}}.")
        return properties[name]

    for _ in range(MAX_PROPERTY_PASSES):
        if not PROPERTY_PATTERN.search(value):
            return value
        if value in seen:
            raise MavenError(f"POM: цикл свойств при раскрытии {value}.")
        seen.add(value)
        value = PROPERTY_PATTERN.sub(replace, value)
    raise MavenError("POM: превышена глубина раскрытия свойств.")


def expand_fields(values: dict, properties: dict) -> dict[str, str]:
    """Раскрыть свойства во всех полях объявления зависимости."""
    return {key: expand(value, properties) for key, value in values.items()}


def read_properties(root: ElementTree.Element) -> dict[str, str]:
    """Получить пользовательские свойства непосредственного блока POM."""
    element = root.find("properties")
    if element is None:
        return {}
    return {child.tag: (child.text or "").strip() for child in element}


def read_dependencies(root: ElementTree.Element, path: str) -> list[dict]:
    """Прочитать только зависимости указанного блока, исключая плагины."""
    return [
        {name: field_text(element, name) for name in DEPENDENCY_FIELDS}
        for element in root.findall(path)
    ]


def dependency_key(values: dict) -> tuple:
    """Получить Maven-ключ с учетом type и classifier."""
    return (
        values.get("groupId", ""), values.get("artifactId", ""),
        values.get("type") or DEFAULT_TYPE, values.get("classifier", ""),
    )


def read_artifact(element: ElementTree.Element, properties: dict) -> Artifact:
    """Прочитать точные координаты parent либо импортируемого BOM."""
    return Artifact(
        expand(field_text(element, "groupId"), properties),
        expand(field_text(element, "artifactId"), properties),
        expand(field_text(element, "version"), properties),
    )


def make_dependency(raw: dict, model) -> Dependency:
    """Применить dependencyManagement к реально объявленной зависимости."""
    values = expand_fields(raw, model.properties)
    managed = model.management.get(dependency_key(values), {})
    merged = expand_fields(managed, model.properties)
    merged.update({key: value for key, value in values.items() if value})
    artifact = Artifact(
        merged.get("groupId", ""), merged.get("artifactId", ""),
        merged.get("version", ""),
    )
    scope = merged.get("scope") or DEFAULT_SCOPE
    optional = merged.get("optional") or "false"
    if scope not in DEPENDENCY_SCOPES:
        raise MavenError(f"POM: неизвестная область зависимости {scope}.")
    if optional not in {"true", "false"}:
        raise MavenError("POM: optional должен быть true или false.")
    return Dependency(
        artifact, scope, optional == "true",
        merged.get("type") or DEFAULT_TYPE, merged.get("classifier", ""),
    )
