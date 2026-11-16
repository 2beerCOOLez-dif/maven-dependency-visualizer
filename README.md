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
| 4 | Вывод обратных зависимостей | Реализован |
| 5 | Graphviz, изображение графа, примеры и сравнение результатов | Запланирован |

Граф строится итеративным DFS без рекурсии. Общие вершины раскрываются
один раз; циклы сохраняются, обход остальных ветвей продолжается.
На этапе 4 добавлен режим `--reverse PACKAGE`: ребра разворачиваются,
а прежний DFS находит прямых и косвенных потребителей выбранного пакета.
Ответ отсортирован, повторов нет; сам пакет исключается даже в цикле.

В тестовом режиме обратный поиск охватывает весь файл репозитория,
включая компоненты вне пути от корня XML. В Maven-режиме область поиска —
граф, достижимый от package/version из XML. POM описывает исходящие связи,
поэтому поиск всех потребителей во всем Maven Central не выполняется.
Цель в Maven задается точно: `groupId:artifactId:version`.

Учитываются свойства, parent, dependencyManagement и BOM. Обходятся
объявления всех scope, включая test и optional. Exclusions и разрешение
конфликтов версий как в Maven не выполняются; разные версии — разные вершины.
Визуализация изображения относится к этапу 5.

## Запуск и тесты

Необходим Python 3.10 или новее. Установка зависимостей и сборка не нужны.
Команды выполняются из корня проекта.

На Linux или macOS:

```sh
sh run.sh --config examples/test_reverse.xml --reverse D
python3 run_tests.py
```

В PowerShell / PyCharm:

```powershell
python -m src.dependency_visualizer --config examples/test_reverse.xml --reverse D
python run_tests.py
```

`run_tests.py` самостоятельно добавляет src в пути импорта.
Успешный результат: `Ran 69 tests` и `OK`.
Maven-тесты используют локальный HTTP-сервер и не требуют интернета.

Для Maven необходим интернет; тестовый режим полностью локальный.
Проверка оформления в PowerShell (утилиты нужны только разработчику):

```powershell
python -m pip install pycodestyle radon
python -m pycodestyle --max-line-length=80 src tests run_tests.py check_style.py
$env:RADONFILESENCODING = "UTF-8"
python -m radon cc -s --min C src tests run_tests.py check_style.py
python check_style.py
```

Первые две проверки кода при отсутствии замечаний ничего не выводят.
Radon показывает C–F при сложности выше 10. check_style.py проверяет
80 символов в строке, 1000 строк в файле, 40 строк в функции, 7 параметров,
docstring, отсутствие комментариев и числовых литералов в сравнениях.
Код 0 означает успех дополнительных проверок, 1 — нарушения.

## Конфигурация

Единственный источник четырех пользовательских параметров — XML-файл.
Аргумент `--config` выбирает настройки. Опция `--reverse PACKAGE` выбирает
операцию и ее цель, не переопределяя четыре параметра XML.

Пример XML: `examples/test_reverse.xml`.

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

Каждый упомянутый пакет должен иметь собственную строку; лист — `C:`.
Повтор определения запрещен. Пустые строки разрешены, повторы ребер удаляются.
При обычном обходе включаются только достижимые от package вершины.
При обратном поиске анализируется весь тестовый файл; цель должна
присутствовать в нем. Некорректное описание отклоняется целиком.

Maven-настройки показаны в examples/maven.xml и examples/junit.xml.
Диапазоны версий, активация profiles и поиск timestamped SNAPSHOT
через maven-metadata.xml пока не поддерживаются.

## Примеры использования

### Проверка конфигурации обычного репозитория

Обычный вывод графа сохраняется. Пример обратного поиска в PowerShell:

```powershell
python -m src.dependency_visualizer --config examples/junit.xml --reverse org.hamcrest:hamcrest-core:1.3
```

Сначала строится граф junit:junit:4.13.2, затем в нем ищутся потребители
указанной версии hamcrest-core. В ответ включаются прямые и косвенные
потребители. Ошибка загрузки любого POM завершает операцию без части ответа.

### Проверка конфигурации тестового репозитория

Обычный граф: `python -m src.dependency_visualizer --config examples/test.xml`.

Демонстрация обратных зависимостей:

```powershell
python -m src.dependency_visualizer --config examples/test_chain.xml --reverse C
python -m src.dependency_visualizer --config examples/test_diamond.xml --reverse D
python -m src.dependency_visualizer --config examples/test_cycle.xml --reverse A
python -m src.dependency_visualizer --config examples/test_self.xml --reverse A
python -m src.dependency_visualizer --config examples/test_reverse.xml --reverse D
python -m src.dependency_visualizer --config examples/test_reverse.xml --reverse A
```

| Файл и цель | Обратные зависимости |
| --- | --- |
| test_chain.xml, C | A, B — косвенный и прямой потребители |
| test_diamond.xml, D | A, B, C — без повторов общей вершины |
| test_cycle.xml, A | B, C — цикл завершается |
| test_self.xml, A | Нет — сам целевой пакет исключается |
| test_reverse.xml, D | A, B, C, E — E находится вне прямого графа корня A |
| test_reverse.xml, A | Нет — от корня никто не зависит |

В graph_reverse.txt описаны A → B/C → D, E → D, G → F.
Для цели D вывод будет таким:

```text
Обратные зависимости для D:
A
B
C
E
```

Для Linux/macOS используйте `sh run.sh --config examples/ИМЯ.xml --reverse D`.
Без --reverse выводится прежний граф. Пустой ответ и циклы дают код 0.

## Демонстрация ошибок всех параметров

Примеры неверных настроек, ожидается код 1:

```powershell
python -m src.dependency_visualizer --config examples/invalid_package.xml
python -m src.dependency_visualizer --config examples/invalid_repository.xml
python -m src.dependency_visualizer --config examples/invalid_test_mode.xml
python -m src.dependency_visualizer --config examples/invalid_version.xml
```

Файлы проверяют соответственно координаты, URL, true/false и формат версии.
Ошибка неполного графа и неизвестная цель дают код 3:

```powershell
python -m src.dependency_visualizer --config examples/test_invalid.xml
python -m src.dependency_visualizer --config examples/test_reverse.xml --reverse Z
```

Ошибки конфигурации, графа, UTF-8, HTTP, POM и parent/BOM идут в stderr.
Частичный результат не выводится. Отсутствие потребителей — успешный ответ.

| Код | Значение |
| --- | --- |
| 0 | Успех или справка, включая циклы и пустой ответ |
| 1 | Ошибка конфигурации |
| 2 | Ошибка аргументов CLI |
| 3 | Ошибка получения данных, графа или неизвестная цель |

Код последней команды в PowerShell: `$LASTEXITCODE`.
