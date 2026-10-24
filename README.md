# Визуализатор зависимостей Maven — вариант №25

## Общее описание

Инструмент командной строки на Python для анализа и визуализации графа
зависимостей Java-пакетов Maven. Вариант практической работы — №25.
Настройки задаются XML-файлом. Для получения зависимостей не используются
менеджеры пакетов и готовые сторонние библиотеки.

Проект развивается поэтапно. Этот README является общей документацией:
при реализации следующих этапов обновляются статус, настройки, описание
функций, команды и примеры использования в этом же файле.

## Состояние реализации

| Этап | Содержание | Статус |
| --- | --- | --- |
| 1 | CLI, XML-конфигурация, проверка параметров, вывод ключ-значение | Реализован |
| 2 | Получение прямых зависимостей заданной версии Maven-пакета | Запланирован |
| 3 | Граф транзитивных зависимостей, итеративный DFS, циклы, тестовый режим | Запланирован |
| 4 | Вывод обратных зависимостей | Запланирован |
| 5 | Graphviz, изображение графа, примеры и сравнение результатов | Запланирован |

В текущей версии доступны чтение и проверка настроек и их вывод.
Сетевые запросы, получение зависимостей, обход графа и визуализация
пока не выполняются. Используется исключительно стандартная библиотека.
 
```

## Запуск и тесты

Из корня проекта:

```sh
sh run.sh --help
sh run.sh --config examples/maven.xml
sh run.sh --config examples/test.xml
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Прямой запуск модуля:

```sh
PYTHONPATH=src python3 -m dependency_visualizer --config examples/maven.xml
```

В PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m dependency_visualizer --config examples/maven.xml
python -m unittest discover -s tests -v
```

## Конфигурация

Единственный источник четырех пользовательских параметров — XML-файл.
Аргумент `--config` обязателен и выбирает этот файл; переопределения
параметров через CLI или переменные окружения нет.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <package>org.apache.commons:commons-lang3</package>
    <repository>https://repo.maven.apache.org/maven2</repository>
    <test_mode>false</test_mode>
    <version>3.14.0</version>
</configuration>
```

| Параметр | Правила |
| --- | --- |
| `package` | В обычном режиме `groupId:artifactId`; в тестовом — буквы A–Z. |
| `repository` | При `false` — HTTP(S) URL; при `true` — читаемый обычный файл. |
| `test_mode` | Только `true` или `false`, с учетом регистра. |
| `version` | Явная версия: латинские буквы, цифры, `.`, `_`, `+`, `-`. |

## Примеры использования

### Проверка конфигурации обычного репозитория

```sh
sh run.sh --config examples/maven.xml
```

Текущий результат этапа 1:

```text
package=org.apache.commons:commons-lang3
repository=https://repo.maven.apache.org/maven2
test_mode=false
version=3.14.0
```

### Проверка конфигурации тестового репозитория

```sh
sh run.sh --config examples/test.xml
```

Выводятся `package=A`, `test_mode=true`, `version=1.0`
и полный путь к `examples/repository.txt`.

Вывод настроек в формате ключ-значение предусмотрен заданием только
для этапа 1. В следующих версиях этот раздел будет описывать актуальный
результат запуска.

## Демонстрация ошибок всех параметров

Каждую команду следует выполнять отдельно: ожидается код завершения `1`.

```sh
sh run.sh --config examples/invalid_package.xml
sh run.sh --config examples/invalid_repository.xml
sh run.sh --config examples/invalid_test_mode.xml
sh run.sh --config examples/invalid_version.xml
```

| Файл | Причина и фрагмент сообщения |
| --- | --- |
| `invalid_package.xml` | `package: ожидается groupId:artifactId.` |
| `invalid_repository.xml` | `repository: нужен HTTP(S) URL…` |
| `invalid_test_mode.xml` | `test_mode: допустимы только true и false.` |
| `invalid_version.xml` | `version: ожидается версия…` |

Полное сообщение начинается с `Ошибка конфигурации:` и идет в stderr.
При ошибке настройки в stdout не выводятся; показывается первая ошибка.
Коды: `0` — успех или справка, `1` — ошибка конфигурации, `2` — ошибка
аргументов командной строки (стандартное поведение argparse).



