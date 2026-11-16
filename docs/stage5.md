# Этап 5: визуализация и сравнение с Maven

## Установка Graphviz

Программа использует стандартную библиотеку Python для получения POM и
построения графа. Для отрисовки требуется отдельная программа Graphviz:
[официальная страница](https://graphviz.org/download/). Python-пакет graphviz устанавливать не нужно.

На Windows установите 64-битный Graphviz, добавьте его каталог bin в PATH
и перезапустите PyCharm. В новом терминале проверьте:

```powershell
dot -V
```

Если установлен стандартный каталог, временно добавить его в текущий PATH
можно так:

```powershell
$env:Path += ";C:\Program Files\Graphviz\bin"
dot -V
```

## Команды визуализации

Выполняйте из корня проекта:

```powershell
python -m src.dependency_visualizer --config examples/junit.xml --visualize --output output/junit
python -m src.dependency_visualizer --config examples/hamcrest.xml --visualize --output output/hamcrest
python -m src.dependency_visualizer --config examples/slf4j.xml --visualize --output output/slf4j
```

Каждая команда создает DOT и SVG и открывает SVG в браузере. Стрелка
направлена от пакета к его зависимости. Голубой цвет выделяет корень;
красный цвет показывает ребра циклов, обнаруженных DFS.

Например, output/junit.dot содержит описание, output/junit.svg — изображение.
Для сохранения без браузера добавьте --no-open. Пример с циклом:

```powershell
python -m src.dependency_visualizer --config examples/test_cycle.xml --visualize --output output/cycle
```

Без --visualize остаются прежний текстовый вывод и режим --reverse.
--visualize и --reverse нельзя объединять. --output задает префикс файлов,
к которому добавляются .dot и .svg; по умолчанию это output/dependencies.
Существующие результаты с тем же префиксом перезаписываются.

Для ручной отрисовки уже сохраненного DOT:

```powershell
dot -Tsvg output/junit.dot -o output/junit.svg
Start-Process output/junit.svg
```

Код 4 означает ошибку визуализации. При отсутствии dot текст DOT сохраняется,
а программа объясняет, как установить Graphviz. При отсутствии просмотрщика
SVG остается на диске и может быть открыт вручную. Коды 0–3 сохраняют смысл
предыдущих этапов. Каталог output исключен из Git.

## Как воспроизвести сравнение

Maven используется исключительно как независимый эталон для требования 4.
Основное приложение не вызывает Maven для получения зависимостей.

Нужны JDK и [Maven](https://maven.apache.org/install.html). Проверьте:

```powershell
java -version
mvn -version
```

В examples/comparison для каждого пакета есть минимальный pom.xml:
проект-потребитель с одной зависимостью на исследуемый пакет. Это позволяет
сравнить наше описание всех объявлений POM с деревом зависимостей,
которое Maven включает в проект-потребитель.

Из корня проекта выполните:

```powershell
mvn -B -f examples/comparison/junit/pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree "-DoutputType=dot" "-DoutputFile=maven.dot"
mvn -B -f examples/comparison/hamcrest/pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree "-DoutputType=dot" "-DoutputFile=maven.dot"
mvn -B -f examples/comparison/slf4j/pom.xml org.apache.maven.plugins:maven-dependency-plugin:3.8.1:tree "-DoutputType=dot" "-DoutputFile=maven.dot"
```

Путь maven.dot отсчитывается от каталога соответствующего pom.xml.
Изображение штатного результата, например для JUnit:

```powershell
dot -Tsvg examples/comparison/junit/maven.dot -o output/junit-maven.svg
Start-Process output/junit-maven.svg
```

Штатный DOT содержит также искусственный корень comparison-junit. При
сравнении ниже он и единственное ребро от него исключены: сравниваются
вершины исследуемого пакета и его зависимостей. Подписи Maven содержат type
и scope; для сопоставления берутся groupId:artifactId:version.

## Полученные результаты

Проверено 16.11.2026: Apache Maven 3.9.11, Maven Dependency Plugin 3.8.1,
JDK 21, Graphviz 2.42.4. Все три нативных запуска завершились BUILD SUCCESS.

| Пакет | Наша программа: вершины / ребра | Maven: вершины / ребра |
| --- | --- | --- |
| junit:junit:4.13.2 | 3 / 3 | 2 / 1 |
| org.hamcrest:hamcrest-library:1.3 | 2 / 1 | 2 / 1 |
| org.slf4j:slf4j-simple:1.7.36 | 5 / 6 | 2 / 1 |

Числа Maven указаны после удаления искусственного проекта-потребителя.
В обоих результатах учитывается сам исследуемый пакет.

**JUnit.** Наша программа включает hamcrest-library:1.3, объявленный в POM
JUnit со scope=test, и ребро этой библиотеки к hamcrest-core:1.3. Maven
не переносит test-зависимости JUnit в проект, использующий JUnit как
внешнюю библиотеку. Поэтому в штатном результате остаются только JUnit
и hamcrest-core. Это объясняет разницу и вершин, и ребер.

**Hamcrest Library.** В обоих случаях есть единственная зависимость на
hamcrest-core:1.3. Совпадают наборы вершин и ребер; разница подписи type/scope
и оформления диаграмм не является различием графов.

**SLF4J Simple.** Наша модель наследует из slf4j-parent тестовую зависимость
на junit:4.13; аналогичная зависимость есть у модели slf4j-api. Затем
обходятся POM JUnit и Hamcrest. Maven не переносит эти test-зависимости
в проект-потребитель, поэтому показывает только slf4j-simple и slf4j-api.

Полученная визуализация отражает прежнюю модель приложения: все объявления
зависимостей POM, включая test и optional. Maven dependency:tree отражает
разрешенное дерево для конкретного проекта: учитывает scope, optional,
exclusions и выбор версий. Наше приложение эти правила полностью не
воспроизводит. В выбранных примерах наблюдаемое расхождение связано со
scope=test; конфликтов версий и optional как причин здесь не заявляется.

Файлы воспроизводимости для каждого имени junit/hamcrest/slf4j:

- examples/comparison/ИМЯ/pom.xml — проект-потребитель;
- examples/comparison/ИМЯ/ours.dot — фактически полученный DOT приложения;
- examples/comparison/ИМЯ/maven.dot — вывод Maven с корнем-потребителем;
  удалены только концевые пробелы строк;
- examples/comparison/ИМЯ/maven-normalized.dot — те же связи Maven без этого
  корня, подписи приведены к groupId:artifactId:version для сопоставления;
- examples/comparison/ИМЯ/maven-result.txt — сокращенный журнал успешного
  запуска; абсолютный путь рабочего каталога заменен на <project>;
- docs/comparison-results.json — числа, различия вершин и ребер.

В архиве поставки папка previews содержит изображения трех графов программы
и соответствующих нормализованных результатов Maven. Их можно воспроизвести
из сохраненных DOT без доступа к сети.


## Источники

- [Graphviz: параметры запуска](https://graphviz.org/doc/info/command.html)
- [Graphviz: SVG](https://graphviz.org/docs/outputs/svg/)
- [Maven Dependency Plugin: tree](https://maven.apache.org/plugins/maven-dependency-plugin/tree-mojo.html)
- [Правила Maven: транзитивность и scope](https://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html)
