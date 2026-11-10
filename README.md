# Визуализатор зависимостей Maven — вариант №25

## Общее описание

Инструмент командной строки на Python для анализа и визуализации графа
зависимостей Java-пакетов Maven. Вариант практической работы — №25.
Настройки задаются XML-файлом. Используется только стандартная библиотека:
менеджеры пакетов и сторонние средства получения зависимостей не нужны.

## Состояние реализации

| Этап | Содержание | Статус |
| --- | --- | --- |
| 1 | CLI, XML-конфигурация, проверка параметров, вывод ключ-значение | Реализован |
| 2 | Получение и вывод прямых зависимостей заданной версии Maven-пакета | Реализован |
| 3 | Граф транзитивных зависимостей, итеративный DFS, циклы, тестовый режим | Реализован |
| 4 | Вывод обратных зависимостей | Запланирован |
| 5 | Graphviz, изображение графа, примеры и сравнение результатов | Запланирован |

На этапе 3 строится ориентированный граф всех достижимых зависимостей.
DFS использует стек без рекурсии: сначала полностью обходится одна ветвь,
затем следующая. Каждая вершина раскрывается один раз; общие зависимости
сохраняют все входящие ребра. Корень и листья включаются в граф.
Ребро к вершине текущего пути означает цикл: программа сохраняет его,
показывает замкнутый путь и продолжает обход остальных ветвей.
Выводятся циклы по обратным ребрам DFS, а не все возможные простые циклы.

В Maven-режиме вершина — `groupId:artifactId:version`.
Учитываются свойства `${...}`, родительские POM, dependencyManagement
и импортированные BOM; зависимости плагинов не включаются.
Обходятся объявления всех scope, включая test и optional.
Это граф объявлений POM: фильтрация scope, exclusions и разрешение
конфликтов версий как в Maven не выполняются. Разные версии — разные вершины.
Визуализация изображения относится к этапу 5.

## Запуск и тесты

Необходим Python 3.10 или новее. Установка зависимостей и сборка не нужны.
Команды выполняются из корня проекта.

На Linux или macOS:

```sh
sh run.sh --help
sh run.sh --config examples/test.xml
sh run.sh --config examples/junit.xml
python3 run_tests.py
```

В PowerShell, в том числе в терминале PyCharm:

```powershell
python -m src.dependency_visualizer --help
python -m src.dependency_visualizer --config examples/test.xml
python -m src.dependency_visualizer --config examples/junit.xml
python run_tests.py
```

`run_tests.py` самостоятельно добавляет src в пути импорта.
Успешный результат: `Ran 54 tests` и `OK`.
Проверяются транзитивность, порядок DFS, общие вершины, циклы,
самозависимость, недостижимые вершины и цепочка из 1501 вершины.
Maven-тесты используют локальный HTTP-сервер и не требуют интернета.

Альтернативный запуск тестов в PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

На Linux или macOS:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Для обычного Maven-репозитория необходим доступ к интернету.
Тестовый режим работает полностью локально.

## Конфигурация

Единственный источник четырех пользовательских параметров — XML-файл.
Обязательный аргумент `--config` выбирает файл настроек.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <package>A</package>
    <repository>repository.txt</repository>
    <test_mode>true</test_mode>
    <version>1.0</version>
</configuration>
```

| Параметр | Правила |
| --- | --- |
| `package` | В обычном режиме `groupId:artifactId`; в тестовом — буквы A–Z. |
| `repository` | При false — HTTP(S) URL; при true — путь к UTF-8 файлу графа. |
| `test_mode` | Только `true` или `false`, с учетом регистра. |
| `version` | Явная версия: латинские буквы, цифры, `.`, `_`, `+`, `-`. |

Относительный путь repository отсчитывается от каталога XML.
В тестовом режиме version проверяется, но граф не содержит версий:
каждое заглавное имя обозначает одну вершину.

Формат тестового репозитория — одна вершина на строку:

```text
A: B C
B: C
C:
```

Здесь A зависит от B и C, а B — от C. Лист описывается строкой `C:`.
Все упомянутые пакеты должны иметь собственную строку; повтор определения
пакета запрещен. Пустые строки разрешены, повтор одного ребра удаляется.
Корень package должен присутствовать в файле. Недостижимые вершины
проверяются при чтении, но в результирующий граф не включаются.

При test_mode=false задаются Maven-координаты, URL и точная версия,
как в готовых examples/maven.xml и examples/junit.xml.
Диапазоны версий, активация profiles и поиск timestamped SNAPSHOT
через maven-metadata.xml пока не поддерживаются.

## Примеры использования

### Проверка конфигурации обычного репозитория

В stage-1 выводятся настройки, в stage-2 — прямые зависимости,
а в stage-3 — список смежности полного достижимого графа и циклы.
Для Maven выполните:

```powershell
python -m src.dependency_visualizer --config examples/junit.xml
```

Программа начинает с POM junit:junit версии 4.13.2, затем получает
POM его зависимостей и продолжает обход до листьев или уже посещенных
вершин. Ошибка загрузки любой вершины завершает операцию без вывода
частичного графа.

### Проверка конфигурации тестового репозитория

```powershell
python -m src.dependency_visualizer --config examples/test.xml
```

Результат:

```text
Корень: A
A -> B, C
B -> C
C -> нет
Циклы не обнаружены.
```

Различные случаи запускаются отдельными командами:

```powershell
python -m src.dependency_visualizer --config examples/test_chain.xml
python -m src.dependency_visualizer --config examples/test_diamond.xml
python -m src.dependency_visualizer --config examples/test_cycle.xml
python -m src.dependency_visualizer --config examples/test_self.xml
python -m src.dependency_visualizer --config examples/test_isolated.xml
```

| Файл | Результат |
| --- | --- |
| test_chain.xml | A → B → C, циклов нет |
| test_diamond.xml | A → B/C → D; D общая, циклов нет |
| test_cycle.xml | Цикл A → B → C → A; лист D также обходится |
| test_self.xml | Цикл A → A |
| test_isolated.xml | Только A; недостижимая Z с петлей не включается |

Для Linux/macOS используйте `sh run.sh --config examples/ИМЯ.xml`.
Цикл является допустимым содержимым графа и дает код завершения 0.

## Демонстрация ошибок всех параметров

Каждую команду выполняйте отдельно; ожидается код завершения 1:

```powershell
python -m src.dependency_visualizer --config examples/invalid_package.xml
python -m src.dependency_visualizer --config examples/invalid_repository.xml
python -m src.dependency_visualizer --config examples/invalid_test_mode.xml
python -m src.dependency_visualizer --config examples/invalid_version.xml
```

| Файл | Причина |
| --- | --- |
| invalid_package.xml | Некорректные координаты пакета |
| invalid_repository.xml | Некорректный URL репозитория |
| invalid_test_mode.xml | Значение отличается от true/false |
| invalid_version.xml | Недопустимый формат версии |

Ошибка неполного графа, код 3:

```powershell
python -m src.dependency_visualizer --config examples/test_invalid.xml
```

```text
Ошибка графа: Не описаны пакеты: B. Добавьте строки NAME:.
```

Обрабатываются ошибки UTF-8 и формата графа, отсутствие корня, HTTP,
соединения, POM, неизвестные/циклические свойства и циклы parent/BOM.
Для проверки HTTP 404 укажите в копии Maven XML отсутствующую версию.
Ошибки идут в stderr; частичный граф не выводится.

| Код | Значение |
| --- | --- |
| 0 | Успех или справка, включая граф с циклом |
| 1 | Ошибка конфигурации |
| 2 | Ошибка аргументов командной строки |
| 3 | Ошибка получения или обработки Maven-данных либо тестового графа |

Код последней команды в PowerShell: `$LASTEXITCODE`.
