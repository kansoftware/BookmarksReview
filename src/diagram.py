"""
Модуль diagram.py
Генерирует Mermaid-диаграммы для визуализации структуры закладок.
Профиль A: TD; без URL в метках; обрезка меток до 60; пустые папки отображаются;
лимиты: максимум 1000 узлов; >50 детей в папке — свертка.
"""

import time
from pathlib import Path
from typing import Optional

from .logger import (
    get_logger,
    log_error_with_context,
    log_function_call,
    log_performance,
)
from .models import Bookmark, BookmarkFolder

logger = get_logger(__name__)


class DiagramGenerator:
    """
    Генератор Mermaid-диаграмм структуры закладок.

    Атрибуты:
        label_max_len: Максимальная длина метки узла (по умолчанию 60)
        max_nodes: Глобальный лимит количества узлов (по умолчанию 1000)
        max_children_per_folder: Максимум дочерних элементов, отображаемых для одной папки (по умолчанию 50)
    """

    def __init__(
        self,
        label_max_len: int = 60,
        max_nodes: int = 1000,
        max_children_per_folder: int = 50,
    ) -> None:
        """
        Инициализация генератора диаграмм.

        Аргументы:
            label_max_len: Максимальная длина меток узлов
            max_nodes: Максимальное количество узлов в диаграмме
            max_children_per_folder: Сколько детей (папок+закладок) показывать у одной папки до свертки
        """
        log_function_call(
            "DiagramGenerator.__init__",
            (),
            {
                "label_max_len": label_max_len,
                "max_nodes": max_nodes,
                "max_children_per_folder": max_children_per_folder,
            },
        )

        self.label_max_len = label_max_len
        self.max_nodes = max_nodes
        self.max_children_per_folder = max_children_per_folder
        self._counter = 0
        self._nodes_count = 0
        self._limit_emitted = False

        logger.info(
            f"DiagramGenerator инициализирован: label_max_len={label_max_len}, "
            f"max_nodes={max_nodes}, max_children_per_folder={max_children_per_folder}"
        )

    def generate_structure_diagram(self, root: BookmarkFolder) -> str:
        """
        Генерирует код Mermaid-диаграммы структуры закладок.

        Аргументы:
            root: Корневой объект папки закладок

        Возвращает:
            str: Строка Mermaid с заголовком 'graph TD' и последующими узлами/ребрами
        """
        start_time = time.time()
        log_function_call("generate_structure_diagram", (root.name,))

        # Сброс счетчиков на случай повторного использования инстанса
        self._counter = 0
        self._nodes_count = 0
        self._limit_emitted = False

        logger.debug(f"Начало генерации диаграммы для корневой папки: {root.name}")

        lines: list[str] = ["graph TD"]
        self._traverse_folder(root, None, lines)

        diagram_code = "\n".join(lines)

        duration = time.time() - start_time
        log_performance(
            "generate_structure_diagram", duration, f"nodes={self._nodes_count}"
        )
        logger.info(
            f"Диаграмма сгенерирована: {self._nodes_count} узлов за {duration:.2f}с"
        )

        return diagram_code

    def save_diagram(self, diagram_code: str, output_path: str) -> None:
        """
        Сохраняет диаграмму в Markdown-файл с оградой ```mermaid.

        Аргументы:
            diagram_code: Код Mermaid-диаграммы
            output_path: Путь для сохранения результата
        """
        start_time = time.time()
        log_function_call(
            "save_diagram", (output_path,), {"diagram_length": len(diagram_code)}
        )

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            with path.open("w", encoding="utf-8") as f:
                f.write("```mermaid\n")
                f.write(diagram_code)
                f.write("\n```")

            duration = time.time() - start_time
            log_performance("save_diagram", duration, f"path={output_path}")
            logger.info(f"Диаграмма сохранена: {output_path} за {duration:.2f}с")

        except Exception as e:
            duration = time.time() - start_time
            log_performance(
                "save_diagram", duration, f"path={output_path}, success=False"
            )
            log_error_with_context(
                e, {"output_path": output_path, "operation": "save_diagram"}
            )
            raise

    def _traverse_folder(
        self, folder: BookmarkFolder, parent_id: Optional[str], lines: list[str]
    ) -> Optional[str]:
        """
        Рекурсивно обходит папку, добавляет узел папки, её детей и связи.

        Аргументы:
            folder: Текущая папка
            parent_id: Идентификатор родительского узла (если есть)
            lines: Аккумулируемый список строк Mermaid

        Возвращает:
            Optional[str]: Идентификатор узла папки или None, если достигнут лимит
        """
        log_function_call(
            "_traverse_folder",
            (folder.name,),
            {
                "parent_id": parent_id,
                "children_count": len(folder.children),
                "bookmarks_count": len(folder.bookmarks),
            },
        )

        if self._would_exceed_limit(1):
            logger.debug(f"Достигнут лимит узлов, пропуск папки: {folder.name}")
            self._emit_limit(lines, parent_id)
            return None

        folder_id = self._next_id("folder")
        label = self._sanitize_label(folder.name)
        self._add_folder_node(lines, folder_id, label)
        if parent_id:
            self._add_edge(lines, parent_id, folder_id)

        logger.debug(f"Добавлен узел папки: {folder.name} (ID: {folder_id})")

        # Подготовка упорядоченного списка детей: сначала папки, затем закладки
        total_children = len(folder.children) + len(folder.bookmarks)
        processed = 0

        for child_folder in folder.children:
            if processed >= self.max_children_per_folder or self._limit_emitted:
                logger.debug(
                    f"Достигнут лимит детей для папки {folder.name}, пропуск подпапок"
                )
                break
            self._traverse_folder(child_folder, folder_id, lines)
            processed += 1

        for bookmark in folder.bookmarks:
            if processed >= self.max_children_per_folder or self._limit_emitted:
                logger.debug(
                    f"Достигнут лимит детей для папки {folder.name}, пропуск закладок"
                )
                break
            self._add_bookmark(bookmark, folder_id, lines)
            processed += 1

        omitted = total_children - processed
        if omitted > 0 and not self._limit_emitted:
            # Добавляем синтетический узел свертки
            if self._would_exceed_limit(1):
                self._emit_limit(lines, folder_id)
            else:
                collapsed_id = self._next_id("collapsed")
                collapsed_label = f"... и {omitted} еще"
                self._add_folder_node(lines, collapsed_id, collapsed_label)
                self._add_edge(lines, folder_id, collapsed_id)
                logger.debug(
                    f"Добавлен узел свертки для {folder.name}: {omitted} пропущенных элементов"
                )

        return folder_id

    def _add_bookmark(
        self, bookmark: Bookmark, parent_id: str, lines: list[str]
    ) -> Optional[str]:
        """
        Добавляет узел закладки и связь с родителем.

        Аргументы:
            bookmark: Объект закладки
            parent_id: Идентификатор родительского узла папки
            lines: Аккумулируемый список строк Mermaid

        Возвращает:
            Optional[str]: Идентификатор узла закладки или None, если достигнут лимит
        """
        log_function_call("_add_bookmark", (bookmark.title,), {"parent_id": parent_id})

        if self._would_exceed_limit(1):
            logger.debug(f"Достигнут лимит узлов, пропуск закладки: {bookmark.title}")
            self._emit_limit(lines, parent_id)
            return None

        node_id = self._next_id("bookmark")
        label = self._sanitize_label(bookmark.title)
        lines.append(f'  {node_id}("{label}")')
        self._nodes_count += 1
        self._add_edge(lines, parent_id, node_id)

        logger.debug(f"Добавлен узел закладки: {bookmark.title} (ID: {node_id})")
        return node_id

    def _add_folder_node(self, lines: list[str], node_id: str, label: str) -> None:
        """
        Добавляет узел папки с прямоугольной формой.

        Аргументы:
            lines: Аккумулируемый список строк Mermaid
            node_id: Идентификатор узла
            label: Метка узла (после санитизации/усечения)
        """
        log_function_call("_add_folder_node", (node_id, label))

        lines.append(f"  {node_id}[{label}]")
        self._nodes_count += 1

        logger.debug(f"Добавлен узел папки: {label} (ID: {node_id})")

    def _add_edge(self, lines: list[str], parent_id: str, child_id: str) -> None:
        """
        Добавляет ребро между двумя узлами.

        Аргументы:
            lines: Аккумулируемый список строк Mermaid
            parent_id: Идентификатор родительского узла
            child_id: Идентификатор дочернего узла
        """
        log_function_call("_add_edge", (parent_id, child_id))

        lines.append(f"  {parent_id} --> {child_id}")
        logger.debug(f"Добавлено ребро: {parent_id} --> {child_id}")

    def _sanitize_label(self, text: str) -> str:
        """
        Санитизирует и нормализует метку: замена кавычек, удаление обратных апостров,
        свертка повторных пробелов/переносов и усечение до максимальной длины.

        Аргументы:
            text: Исходная строка метки

        Возвращает:
            str: Санитизированная и, при необходимости, усеченная метка
        """
        log_function_call("_sanitize_label", (text,))

        original_length = len(text)
        s = text.replace('"', "'").replace("`", "")
        s = " ".join(s.split())  # свертка пробелов и переносов
        s = s.strip()

        if len(s) > self.label_max_len:
            s = s[: self.label_max_len - 3] + "..."
            logger.debug(f"Метка усечена с {original_length} до {len(s)} символов")

        logger.debug(f"Метка санитизирована: '{text}' -> '{s}'")
        return s

    def _next_id(self, kind: str) -> str:
        """
        Возвращает следующий идентификатор узла указанного типа и увеличивает счетчик.

        Аргументы:
            kind: Тип узла ('folder', 'bookmark', 'collapsed')

        Возвращает:
            str: Уникальный идентификатор узла
        """
        node_id = f"{kind}_{self._counter}"
        self._counter += 1

        logger.debug(f"Сгенерирован ID узла: {node_id} (тип: {kind})")
        return node_id

    def _would_exceed_limit(self, additional: int) -> bool:
        """
        Проверяет, превысит ли добавление указанного количества узлов глобальный лимит.

        Аргументы:
            additional: Количество узлов, планируемых к добавлению

        Возвращает:
            bool: True, если лимит будет превышен, иначе False
        """
        would_exceed = (self._nodes_count + additional) > self.max_nodes

        if would_exceed:
            logger.debug(
                f"Превышение лимита узлов: текущих={self._nodes_count}, "
                f"добавляемых={additional}, лимит={self.max_nodes}"
            )

        return would_exceed

    def _emit_limit(self, lines: list[str], parent_id: Optional[str]) -> None:
        """
        Добавляет специальный узел, указывающий на достижение лимита узлов, один раз за генерацию.

        Аргументы:
            lines: Аккумулируемый список строк Mermaid
            parent_id: Идентификатор родительского узла, к которому будет присоединен узел лимита (если есть)
        """
        if self._limit_emitted:
            logger.debug("Узел лимита уже был добавлен ранее")
            return

        limit_label = f"Диаграмма обрезана: достигнут предел {self.max_nodes} узлов"
        limit_id = "limit_reached"
        lines.append(f"  {limit_id}[{limit_label}]")
        self._nodes_count += 1
        self._limit_emitted = True

        logger.warning(f"Добавлен узел ограничения: {limit_label}")

        if parent_id:
            self._add_edge(lines, parent_id, limit_id)
