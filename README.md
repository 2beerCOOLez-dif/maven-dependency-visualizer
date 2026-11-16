# Визуализатор зависимостей Maven — вариант №25

## Общее описание

CLI на Python для построения и визуализации графа зависимостей Maven.
Настройки задаются XML-файлом. POM загружаются стандартной библиотекой
Python, без менеджеров пакетов и сторонних библиотек сбора зависимостей.
Для отрисовки используется отдельная программа Graphviz.

## Состояние реализации

| Этап | Содержание | Статус |
| --- | --- | --- |
| 1 | CLI и XML-конфигурация, проверка настроек | Реализован |
| 2 | Получение прямых зависимостей заданной версии | Реализован |
| 3 | Транзитивный граф, итеративный DFS, циклы, тестовый режим | Реализован |
| 4 | Прямые и косвенные обратные зависимости | Реализован |
| 5 | Graphviz DOT, изображение, три пакета и сравнение с Maven | Реализован |

Прежний DFS без рекурсии строит граф. Визуализация сохраняет DOT и SVG,
затем открывает изображение в браузере. Корень выделен голубым, ребра
обнаруженных DFS циклов — красным. Общие зависимости не дублируются.

Учитываются свойства, parent, dependencyManagement и BOM. Обходятся все
объявления, включая test и optional. Exclusions, profiles и разрешение
конфликтов версий как в Maven не реализованы; версии — разные вершины.

## Запуск и тесты

Необходим Python 3.10+. Сборка и установка Python-зависимостей не нужны.
Для изображения установите [Graphviz](https://graphviz.org/download/),
добавьте его bin в PATH и перезапустите PyCharm. Проверьте `dot -V`.
Команды выполняются из корня проекта.

PowerShell / PyCharm:

```powershell
python -m src.dependency_visualizer --config examples/test_cycle.xml --visualize --output output/cycle
python run_tests.py
```

Linux/macOS:

```sh
sh run.sh --config examples/test_cycle.xml --visualize --output output/cycle
python3 run_tests.py
```

Ожидается `Ran 83 tests` и `OK`. Проверки POM используют локальный HTTP,
внешний интернет не требуется. При отсутствии dot две проверки настоящего
рендера пропускаются; для полного прогона установите Graphviz.

Оформление кода (утилиты нужны только разработчику):

```powershell
python -m pip install pycodestyle radon
python -m pycodestyle --max-line-length=80 src tests run_tests.py
$env:RADONFILESENCODING = "UTF-8"
python -m radon cc -s --min C src tests run_tests.py
git diff --check
```

При отсутствии нарушений эти проверки кода ничего не выводят.
Ограничения задания: строка до 80 символов, файл до 1000 строк,
функция до 40 строк, до 7 параметров, сложность до 10, PEP8 и docstring.

## Конфигурация

Четыре параметра задаются только XML, --config выбирает файл.
Опции операции не переопределяют эти настройки.

| Параметр | Правила |
| --- | --- |
| package | Maven: groupId:artifactId; тест: заглавные буквы A–Z |
| repository | HTTP(S) URL либо путь к UTF-8 файлу тестового графа |
| test_mode | true или false |
| version | Точная версия: латиница, цифры, `.`, `_`, `+`, `-` |

Примеры: examples/junit.xml, hamcrest.xml, slf4j.xml, test.xml.
В тестовом режиме version проверяется, но вершины обозначаются именами.
Путь тестового репозитория считается от каталога XML. Формат:

```text
A: B C
B: C
C:
```

Каждый упомянутый пакет должен иметь собственную строку; лист — `C:`.
Повтор определения запрещен. Пустые строки разрешены, повторы ребер удаляются.
Обычный обход включает только достижимые от package вершины.

| Опция | Назначение |
| --- | --- |
| --visualize | Сохранить DOT, отрисовать SVG и открыть его в браузере |
| --output PREFIX | Имена PREFIX.dot и PREFIX.svg; по умолчанию output/dependencies |
| --no-open | Сохранить изображение без браузера; требует --visualize |
| --reverse PACKAGE | Вывести прямых и косвенных потребителей выбранного пакета |

--output требует --visualize; --visualize и --reverse взаимоисключаются.
Без обеих операций выводится прежний текстовый список смежности.
Результаты output игнорируются Git; одинаковый префикс перезаписывает файлы.

Обратный поиск в тестовом режиме охватывает весь файл. Для Maven он
ограничен графом корня из XML; цель задается как groupId:artifactId:version.
Сам целевой пакет исключается даже в цикле; результат отсортирован.
Диапазоны версий и timestamped SNAPSHOT через maven-metadata.xml не реализованы.

## Примеры использования

### Проверка конфигурации обычного репозитория

Три различных Maven-пакета, каждая команда открывает изображение:

```powershell
python -m src.dependency_visualizer --config examples/junit.xml --visualize --output output/junit
python -m src.dependency_visualizer --config examples/hamcrest.xml --visualize --output output/hamcrest
python -m src.dependency_visualizer --config examples/slf4j.xml --visualize --output output/slf4j
```

Получаются файлы output/junit.dot и output/junit.svg и аналогичные пары
для остальных пакетов. Для работы без окна добавьте --no-open.
Содержимое DOT можно открыть в текстовом редакторе.

Сравнение реально выполнено с Maven 3.9.11 и Dependency Plugin 3.8.1:

| Пакет | Наш граф: вершины/ребра | Maven: вершины/ребра |
| --- | --- | --- |
| junit:junit:4.13.2 | 3/3 | 2/1 |
| org.hamcrest:hamcrest-library:1.3 | 2/1 | 2/1 |
| org.slf4j:slf4j-simple:1.7.36 | 5/6 | 2/1 |

Maven запускался для проектов-потребителей; их искусственные корни исключены
из чисел. Отличия JUnit и SLF4J вызваны test-зависимостями: наша программа
показывает их объявления, Maven не переносит их в проект-потребитель.
У Hamcrest совпадают вершины и ребра.

Исходные DOT, проекты Maven и журналы находятся в examples/comparison.
[Подробное сравнение, установка и команды Maven](docs/stage5.md).
Maven используется только для независимого сравнения, не основным приложением.

### Проверка конфигурации тестового репозитория

```powershell
python -m src.dependency_visualizer --config examples/test.xml
python -m src.dependency_visualizer --config examples/test_cycle.xml --visualize --output output/cycle
python -m src.dependency_visualizer --config examples/test_reverse.xml --reverse D
```

Обычный вывод: корень A, связи A → B/C, B → C и отсутствие циклов.
Визуализация test_cycle.xml выделяет цикл A → B → C → A; D — лист.
Обратный поиск D дает A, B, C, E, включая отдельного потребителя E.
Примеры chain, diamond, self и isolated из этапа 3 сохраняются.

## Демонстрация ошибок всех параметров

Примеры неверных настроек, ожидается код 1:

```powershell
python -m src.dependency_visualizer --config examples/invalid_package.xml
python -m src.dependency_visualizer --config examples/invalid_repository.xml
python -m src.dependency_visualizer --config examples/invalid_test_mode.xml
python -m src.dependency_visualizer --config examples/invalid_version.xml
```

Неполный граф и неизвестная цель дают код 3:

```powershell
python -m src.dependency_visualizer --config examples/test_invalid.xml
python -m src.dependency_visualizer --config examples/test_reverse.xml --reverse Z
```

При отсутствии Graphviz выводится инструкция установки; DOT уже сохранен.
Если браузер не открылся, откройте SVG вручную или используйте --no-open.

| Код | Значение |
| --- | --- |
| 0 | Успех или справка, включая циклы и отсутствие потребителей |
| 1 | Ошибка конфигурации |
| 2 | Ошибка аргументов CLI |
| 3 | Ошибка получения данных, графа или неизвестная цель |
| 4 | Ошибка сохранения, отрисовки или открытия изображения |

Ошибки идут в stderr. Код последней команды PowerShell: `$LASTEXITCODE`.
