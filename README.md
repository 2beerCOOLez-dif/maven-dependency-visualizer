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
| 2 | Получение и вывод прямых зависимостей заданной версии Maven-пакета | Реализован |
| 3 | Граф транзитивных зависимостей, итеративный DFS, циклы, тестовый режим | Запланирован |
| 4 | Вывод обратных зависимостей | Запланирован |
| 5 | Graphviz, изображение графа, примеры и сравнение результатов | Запланирован |

На этапе 1 реализованы чтение и проверка настроек и их вывод.
На этапе 2 добавлены загрузка POM заданной версии Maven-пакета
из указанного репозитория и вывод его прямых зависимостей.

При обработке POM учитываются свойства `${...}`, родительские POM,
dependencyManagement и импортированные BOM. Зависимости плагинов
не включаются в результат. POM самих зависимостей не загружаются:
транзитивный обход пока не выполняется.

Используется исключительно стандартная библиотека Python.
Построение графа и визуализация пока не реализованы.

## Запуск и тесты

Для работы необходим Python 3.10 или новее.
Установка сторонних библиотек и сборка проекта не требуются.
Команды выполняются из корня проекта.

На Linux или macOS:

```sh
sh run.sh --help
sh run.sh --config examples/maven.xml
sh run.sh --config examples/junit.xml
python3 run_tests.py
```

Прямой запуск модуля:

```sh
PYTHONPATH=src python3 -m dependency_visualizer --config examples/maven.xml
```

В PowerShell, в том числе в терминале PyCharm:

```powershell
python -m src.dependency_visualizer --help
python -m src.dependency_visualizer --config examples/maven.xml
python -m src.dependency_visualizer --config examples/junit.xml
python run_tests.py
```

Скрипт run_tests.py самостоятельно добавляет папку src в пути поиска
модулей. При успешном выполнении выводятся `Ran 37 tests` и `OK`.

Альтернативный запуск тестов в PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

На Linux или macOS:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Автоматические тесты не требуют внешнего интернета:
HTTP-запросы проверяются с помощью временного локального сервера.
Для получения данных из Maven Central необходим доступ к интернету.

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

На этапе 2 для получения зависимостей используется `test_mode=false`.
Программа формирует URL POM на основании имени пакета и версии,
затем загружает его из репозитория, указанного в `repository`.

При `test_mode=true` сохраняется проверка конфигурации и доступности
тестового файла. Обработка содержимого тестового графа относится
к этапу 3, поэтому на этапе 2 такой запуск завершается сообщением
об отсутствии этой возможности и кодом `3`.

Относительный путь к тестовому файлу отсчитывается от каталога XML.

Диапазоны версий, активация Maven profiles и поиск timestamped SNAPSHOT
через maven-metadata.xml пока не поддерживаются.

## Примеры использования

### Проверка конфигурации обычного репозитория

В ветке `stage-1`:

```sh
sh run.sh --config examples/maven.xml
```

Результат этапа 1:

```text
package=org.apache.commons:commons-lang3
repository=https://repo.maven.apache.org/maven2
test_mode=false
version=3.14.0
```

На этапе 2 вместо настроек выводятся прямые зависимости.

Например, в файле `examples/junit.xml` указан пакет `junit:junit`
версии `4.13.2`. Запуск в PowerShell:

```powershell
python -m src.dependency_visualizer --config examples/junit.xml
```

На Linux или macOS:

```sh
sh run.sh --config examples/junit.xml
```

Программа загружает POM по адресу:

```text
https://repo.maven.apache.org/maven2/junit/junit/4.13.2/junit-4.13.2.pom
```

Результат этапа 2:

```text
org.hamcrest:hamcrest-core:1.3 [scope=compile, type=jar]
org.hamcrest:hamcrest-library:1.3 [scope=test, type=jar]
```

Каждая строка содержит имя и версию прямой зависимости,
область использования `scope` и тип `type`.
При наличии дополнительно выводятся `classifier` и `optional=true`.

Если прямых зависимостей нет:

```text
Прямые зависимости не найдены.
```

### Проверка конфигурации тестового репозитория

В ветке `stage-1`:

```sh
sh run.sh --config examples/test.xml
```

Выводятся `package=A`, `test_mode=true`, `version=1.0`
и полный путь к `examples/repository.txt`.

На этапе 1 содержимое тестового файла не анализируется.
На этапе 2 эта команда сообщает, что сбор зависимостей
из тестового графа относится к этапу 3.

Вывод настроек в формате ключ-значение предусмотрен заданием только
для этапа 1. На этапе 2 вместо него выводятся прямые зависимости.

## Демонстрация ошибок всех параметров

Каждую команду следует выполнять отдельно:
ожидается код завершения `1`.

```sh
sh run.sh --config examples/invalid_package.xml
sh run.sh --config examples/invalid_repository.xml
sh run.sh --config examples/invalid_test_mode.xml
sh run.sh --config examples/invalid_version.xml
```

В PowerShell:

```powershell
python -m src.dependency_visualizer --config examples/invalid_package.xml
python -m src.dependency_visualizer --config examples/invalid_repository.xml
python -m src.dependency_visualizer --config examples/invalid_test_mode.xml
python -m src.dependency_visualizer --config examples/invalid_version.xml
```

| Файл | Причина и фрагмент сообщения |
| --- | --- |
| `invalid_package.xml` | `package: ожидается groupId:artifactId.` |
| `invalid_repository.xml` | `repository: нужен HTTP(S) URL…` |
| `invalid_test_mode.xml` | `test_mode: допустимы только true и false.` |
| `invalid_version.xml` | `version: ожидается версия…` |

Полное сообщение начинается с `Ошибка конфигурации:` и идет в stderr.
Показывается первая обнаруженная ошибка.

На этапе 2 дополнительно обрабатываются ошибки HTTP,
таймауты и ошибки соединения, некорректный POM, неизвестные
и циклические свойства, отсутствие версии зависимости и циклы parent/BOM.

Например, для проверки отсутствующей версии укажите в копии XML:

```xml
<version>0.0.0-does-not-exist</version>
```

При запуске с этой конфигурацией ожидается сообщение,
начинающееся с `Ошибка Maven: HTTP 404`, и код завершения `3`.

При ошибке получения данных частичный список зависимостей не выводится.

Коды завершения:

| Код | Значение |
| --- | --- |
| `0` | Успех или справка |
| `1` | Ошибка конфигурации |
| `2` | Ошибка аргументов командной строки |
| `3` | Ошибка получения или обработки Maven-данных |

Посмотреть код последней команды в PowerShell:

```powershell
$LASTEXITCODE
```