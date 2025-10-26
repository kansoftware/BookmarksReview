import re

import pytest

from src.diagram import DiagramGenerator
from src.models import Bookmark, BookmarkFolder


def make_folder(name: str, children=None, bookmarks=None) -> BookmarkFolder:
    return BookmarkFolder(name=name, children=children or [], bookmarks=bookmarks or [])


def make_bookmark(title: str) -> Bookmark:
    return Bookmark(title=title, url="https://example.com", date_added=None)


def test_header_and_root_node():
    """
    Проверяет:
    - первая строка строго "graph TD"
    - корневая папка отображается как прямоугольный узел
    """
    root = make_folder("Root")
    gen = DiagramGenerator()
    code = gen.generate_structure_diagram(root)
    lines = code.splitlines()

    assert lines[0] == "graph TD"
    assert "  folder_0[Root]" in code


def test_shapes_and_edges():
    """
    Проверяет формы узлов и рёбра:
    - папка как id[Label]
    - закладка как id("Label")
    - корректные связи parent --> child
    """
    sub = make_folder("Sub")
    link = make_bookmark("Link")
    root = make_folder("Root", children=[sub], bookmarks=[link])

    gen = DiagramGenerator()
    code = gen.generate_structure_diagram(root)

    # Папка Sub как прямоугольник
    assert re.search(r"  folder_\d+\[Sub\]", code) is not None
    # Закладка Link как скругленный узел
    assert re.search(r'  bookmark_\d+\("Link"\)', code) is not None
    # Рёбра от корня к дочерним узлам (идентификаторы зависят от порядка)
    # Корень всегда folder_0
    assert re.search(r"  folder_0 --> folder_\d+", code) is not None
    assert re.search(r"  folder_0 --> bookmark_\d+", code) is not None


def test_empty_folder_displayed():
    """
    Пустые папки должны отображаться как узлы и быть связаны с родителем.
    """
    empty = make_folder("Empty")
    root = make_folder("Root", children=[empty])

    gen = DiagramGenerator()
    code = gen.generate_structure_diagram(root)

    # Узел пустой папки присутствует
    assert re.search(r"  folder_\d+\[Empty\]", code) is not None
    # Есть ребро от родителя
    assert re.search(r"  folder_0 --> folder_\d+", code) is not None


def test_sanitization_and_truncation():
    """
    Санитизация и усечение:
    - двойные кавычки заменяются на одинарные
    - обратные апострофы удаляются
    - множественные пробелы/переносы сворачиваются
    - длина обрезается с суффиксом '...'
    """
    bad_title = '  Bad  "Title"  with  `backticks`  and   spaces  \n new line  '
    # Упростим проверку: уменьшим лимит, чтобы точно увидеть '...'
    gen = DiagramGenerator(label_max_len=10)
    root = make_folder("Root", bookmarks=[make_bookmark(bad_title)])
    code = gen.generate_structure_diagram(root)

    m = re.search(r'bookmark_\d+\("([^"]+)"\)', code)
    assert m is not None
    label = m.group(1)

    assert len(label) <= 10
    assert label.endswith("...")
    assert '"' not in label
    assert "`" not in label
    # Не должно быть двойных пробелов
    assert "  " not in label


def test_collapse_more_than_50_children():
    """
    При количестве детей > 50 у папки:
    - отображаются первые 50 детей
    - добавляется синтетический узел свертки с текстом '... и N еще'
    """
    big_children = [make_bookmark(f"Item {i}") for i in range(55)]
    big = make_folder("Big", bookmarks=big_children)
    root = make_folder("Root", children=[big])

    gen = DiagramGenerator()  # max_children_per_folder=50 по умолчанию
    code = gen.generate_structure_diagram(root)

    # Ровно 50 видимых закладок
    bookmarks_shown = re.findall(r'  bookmark_\d+\("Item \d+"\)', code)
    assert len(bookmarks_shown) == 50

    # Узел свертки с корректным числом пропущенных
    assert re.search(r"\[\.\.\. и 5 еще\]", code) is not None


def test_max_nodes_limit_emits_limit_node_and_stops():
    """
    При превышении лимита узлов:
    - добавляется узел limit_reached
    - присутствует соответствующая связь от текущего родителя
    - текст метки содержит заданный лимит
    """
    # Лимит намеренно очень малый для компактного теста
    gen = DiagramGenerator(max_nodes=5)

    # Один корень и много закладок у корня
    root = make_folder("Root", bookmarks=[make_bookmark(f"Link {i}") for i in range(10)])
    code = gen.generate_structure_diagram(root)

    assert "limit_reached" in code
    assert f"Диграмма обрезана: достигнут предел {gen.max_nodes} узлов" in code or \
           f"Диаграмма обрезана: достигнут предел {gen.max_nodes} узлов" in code
    # Есть ребро от родителя (folder_0) к узлу лимита
    assert re.search(r"  folder_0 --> limit_reached", code) is not None