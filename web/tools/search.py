#!/usr/bin/env python3
"""
Поисковая система по метаданным
Быстрый поиск файлов и папок по метаданным
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime


class MetadataSearch:
    """Поиск по метаданным файлов и папок"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.index = {
            "folders": [],
            "files": []
        }

    def build_index(self):
        """Построить индекс метаданных"""

        print(f"🔨 Построение индекса: {self.base_path}")

        for root, dirs, files in os.walk(self.base_path):
            root_path = Path(root)

            # Индексировать папку
            folder_meta = root_path / ".folder-meta.json"
            if folder_meta.exists():
                try:
                    with open(folder_meta, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        metadata['_path'] = str(root_path.relative_to(self.base_path))
                        self.index["folders"].append(metadata)
                except:
                    pass

            # Индексировать файлы
            for file in files:
                if file.endswith('.meta.json') and not file.startswith('.folder-'):
                    meta_path = root_path / file
                    try:
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            metadata['_path'] = str(root_path.relative_to(self.base_path))
                            self.index["files"].append(metadata)
                    except:
                        pass

        print(f"✓ Индекс построен: {len(self.index['folders'])} папок, {len(self.index['files'])} файлов")

    def search(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        file_type: Optional[str] = None,
        author: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        search_folders: bool = True,
        search_files: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Поиск по различным критериям"""

        results = {
            "folders": [],
            "files": []
        }

        # Поиск в папках
        if search_folders:
            for folder in self.index["folders"]:
                if self._matches(folder, query, tags, category, None, author, date_from, date_to):
                    results["folders"].append(folder)

        # Поиск в файлах
        if search_files:
            for file in self.index["files"]:
                if self._matches(file, query, tags, category, file_type, author, date_from, date_to):
                    results["files"].append(file)

        return results

    def _matches(
        self,
        item: Dict[str, Any],
        query: Optional[str],
        tags: Optional[List[str]],
        category: Optional[str],
        file_type: Optional[str],
        author: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str]
    ) -> bool:
        """Проверить соответствие критериям поиска"""

        # Текстовый поиск
        if query:
            query_lower = query.lower()
            searchable_text = " ".join([
                item.get("name", ""),
                item.get("title", ""),
                item.get("description", ""),
                item.get("subject", ""),
                " ".join(item.get("keywords", [])),
                " ".join(item.get("tags", []))
            ]).lower()

            if query_lower not in searchable_text:
                return False

        # Поиск по тегам
        if tags:
            item_tags = set(item.get("tags", []))
            if not any(tag in item_tags for tag in tags):
                return False

        # Поиск по категории
        if category and item.get("category") != category:
            return False

        # Поиск по типу файла
        if file_type and item.get("fileType") != file_type:
            return False

        # Поиск по автору
        if author and author.lower() not in item.get("author", "").lower():
            return False

        # Поиск по дате
        if date_from or date_to:
            item_date = item.get("updated") or item.get("created")
            if item_date:
                if date_from and item_date < date_from:
                    return False
                if date_to and item_date > date_to:
                    return False

        return True

    def faceted_search(self) -> Dict[str, Any]:
        """Фасетный поиск - группировка по категориям"""

        facets = {
            "categories": {},
            "tags": {},
            "fileTypes": {},
            "authors": {}
        }

        for file in self.index["files"]:
            # Категории
            category = file.get("category", "unknown")
            facets["categories"][category] = facets["categories"].get(category, 0) + 1

            # Теги
            for tag in file.get("tags", []):
                facets["tags"][tag] = facets["tags"].get(tag, 0) + 1

            # Типы файлов
            file_type = file.get("fileType", "unknown")
            facets["fileTypes"][file_type] = facets["fileTypes"].get(file_type, 0) + 1

            # Авторы
            author = file.get("author", "unknown")
            facets["authors"][author] = facets["authors"].get(author, 0) + 1

        return facets


def print_results(results: Dict[str, List[Dict[str, Any]]]):
    """Вывести результаты поиска"""

    total = len(results["folders"]) + len(results["files"])

    if total == 0:
        print("\n❌ Ничего не найдено")
        return

    print(f"\n✓ Найдено: {total} результатов")

    if results["folders"]:
        print(f"\n📁 Папки ({len(results['folders'])}):")
        for folder in results["folders"]:
            print(f"\n  {folder.get('name', 'Без названия')}")
            print(f"  📍 {folder.get('_path', '')}")
            print(f"  📝 {folder.get('description', '')[:100]}")
            if folder.get("tags"):
                print(f"  🏷  {', '.join(folder['tags'])}")

    if results["files"]:
        print(f"\n📄 Файлы ({len(results['files'])}):")
        for file in results["files"]:
            print(f"\n  {file.get('title', file.get('filename', 'Без названия'))}")
            print(f"  📍 {folder.get('_path', '')}/{file.get('filename', '')}")
            print(f"  📝 {file.get('description', '')[:100]}")
            if file.get("tags"):
                print(f"  🏷  {', '.join(file['tags'])}")
            if file.get("fileType"):
                print(f"  📋 Тип: {file['fileType']}")


def main():
    """Главная функция CLI"""

    import os

    parser = argparse.ArgumentParser(
        description="Поиск файлов и папок по метаданным"
    )

    parser.add_argument('query', nargs='?', help='Поисковый запрос')
    parser.add_argument('--path', default='.', help='Путь для поиска')
    parser.add_argument('--tags', nargs='*', help='Поиск по тегам')
    parser.add_argument('--category', help='Поиск по категории')
    parser.add_argument('--type', help='Тип файла')
    parser.add_argument('--author', help='Автор')
    parser.add_argument('--from', dest='date_from', help='Дата от (ISO формат)')
    parser.add_argument('--to', dest='date_to', help='Дата до (ISO формат)')
    parser.add_argument('--folders-only', action='store_true', help='Искать только папки')
    parser.add_argument('--files-only', action='store_true', help='Искать только файлы')
    parser.add_argument('--facets', action='store_true', help='Показать фасеты')
    parser.add_argument('--json', action='store_true', help='Вывод в JSON формате')

    args = parser.parse_args()

    search = MetadataSearch(args.path)
    search.build_index()

    if args.facets:
        facets = search.faceted_search()
        print("\n📊 Фасеты:")
        print(json.dumps(facets, ensure_ascii=False, indent=2))
        return 0

    results = search.search(
        query=args.query,
        tags=args.tags,
        category=args.category,
        file_type=args.type,
        author=args.author,
        date_from=args.date_from,
        date_to=args.date_to,
        search_folders=not args.files_only,
        search_files=not args.folders_only
    )

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print_results(results)

    return 0


if __name__ == "__main__":
    import os
    exit(main())
