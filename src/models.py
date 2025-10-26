"""
Модуль models.py
Содержит модели данных для работы с закладками браузера.
Используется dataclass для удобного представления структур.
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
from typing_extensions import Literal


@dataclass
class Bookmark:
    """
    Класс для представления одной закладки.

    Атрибуты:
        title: Заголовок закладки
        url: URL-адрес страницы
        date_added: Дата добавления закладки
    """
    title: str
    url: str
    date_added: Optional[datetime]


@dataclass
class BookmarkFolder:
    """
    Класс для представления папки с закладками.
    Поддерживает вложенную структуру папок.

    Атрибуты:
        name: Название папки
        children: Список вложенных папок
        bookmarks: Список закладок в папке
    """
    name: str
    children: List['BookmarkFolder']
    bookmarks: List[Bookmark]


@dataclass
class ProcessedPage:
    """
    Класс для представления обработанной страницы.

    Атрибуты:
        url: URL-адрес страницы
        title: Заголовок страницы
        summary: Сгенерированное описание
        fetch_date: Дата обработки
        status: Статус обработки ('success', 'failed', 'skipped')
    """
    url: str
    title: str
    summary: str
    fetch_date: datetime
    status: Literal['success', 'failed', 'skipped']