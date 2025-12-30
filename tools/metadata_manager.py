#!/usr/bin/env python3
"""
Менеджер метаданных для файлов и папок
Управление метаданными согласно методологии информационной операционной системы
"""

import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import argparse


class MetadataManager:
    """Класс для управления метаданными файлов и папок"""

    FOLDER_META_FILE = ".folder-meta.json"
    FOLDER_README_FILE = ".folder-readme.md"
    FOLDER_SCRIPTS_DIR = ".folder-scripts"

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()

    def create_folder_metadata(
        self,
        folder_path: str,
        name: str,
        description: str,
        category: str = "other",
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """Создать метаданные для папки"""

        folder = Path(folder_path).resolve()
        if not folder.exists():
            raise FileNotFoundError(f"Папка не найдена: {folder}")

        if not folder.is_dir():
            raise ValueError(f"Не является папкой: {folder}")

        # Собрать статистику
        stats = self._collect_folder_statistics(folder)

        metadata = {
            "name": name,
            "description": description,
            "category": category,
            "tags": tags or [],
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "author": author or os.getenv("USER", "unknown"),
            "language": language,
            "status": "active",
            "statistics": stats,
            "relatedFolders": [],
            "quickLinks": [],
            "keywords": []
        }

        # Сохранить метаданные
        meta_file = folder / self.FOLDER_META_FILE
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"✓ Метаданные папки созданы: {meta_file}")
        return metadata

    def create_file_metadata(
        self,
        file_path: str,
        title: str,
        description: str = "",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """Создать метаданные для файла"""

        file = Path(file_path).resolve()
        if not file.exists():
            raise FileNotFoundError(f"Файл не найден: {file}")

        if not file.is_file():
            raise ValueError(f"Не является файлом: {file}")

        # Определить тип файла
        file_type = self._detect_file_type(file)

        # Получить информацию о файле
        stat = file.stat()

        # Вычислить контрольные суммы
        checksums = self._calculate_checksums(file)

        metadata = {
            "filename": file.name,
            "title": title,
            "description": description,
            "fileType": file_type,
            "mimeType": self._get_mime_type(file),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "updated": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "author": author or os.getenv("USER", "unknown"),
            "language": language,
            "category": category,
            "tags": tags or [],
            "keywords": [],
            "status": "final",
            "checksum": checksums
        }

        # Сохранить метаданные
        meta_file = file.parent / f"{file.stem}.meta.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"✓ Метаданные файла созданы: {meta_file}")
        return metadata

    def read_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """Прочитать метаданные файла или папки"""

        path_obj = Path(path).resolve()

        if path_obj.is_dir():
            meta_file = path_obj / self.FOLDER_META_FILE
        else:
            meta_file = path_obj.parent / f"{path_obj.stem}.meta.json"

        if not meta_file.exists():
            return None

        with open(meta_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_metadata(self, path: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить метаданные"""

        metadata = self.read_metadata(path)
        if metadata is None:
            raise FileNotFoundError(f"Метаданные не найдены для: {path}")

        # Обновить поля
        metadata.update(updates)
        metadata["updated"] = datetime.now().isoformat()

        # Сохранить
        path_obj = Path(path).resolve()
        if path_obj.is_dir():
            meta_file = path_obj / self.FOLDER_META_FILE
        else:
            meta_file = path_obj.parent / f"{path_obj.stem}.meta.json"

        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"✓ Метаданные обновлены: {meta_file}")
        return metadata

    def create_folder_readme(self, folder_path: str, content: str) -> Path:
        """Создать README файл для папки"""

        folder = Path(folder_path).resolve()
        readme_file = folder / self.FOLDER_README_FILE

        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ README создан: {readme_file}")
        return readme_file

    def create_summary(self, file_path: str, summary: str) -> Path:
        """Создать краткое содержание для файла"""

        file = Path(file_path).resolve()
        summary_file = file.parent / f"{file.stem}.summary.md"

        content = f"# Краткое содержание: {file.name}\n\n{summary}\n"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ Краткое содержание создано: {summary_file}")
        return summary_file

    def create_toc(self, file_path: str, sections: List[Dict[str, Any]]) -> Path:
        """Создать расширенное оглавление для файла"""

        file = Path(file_path).resolve()
        toc_file = file.parent / f"{file.stem}.toc.md"

        content = f"# Оглавление: {file.name}\n\n"

        for section in sections:
            indent = "  " * (section.get("level", 1) - 1)
            title = section.get("title", "")
            page = section.get("page", "")
            summary = section.get("summary", "")

            if page:
                content += f"{indent}- {title} (стр. {page})\n"
            else:
                content += f"{indent}- {title}\n"

            if summary:
                content += f"{indent}  {summary}\n"

        with open(toc_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"✓ Оглавление создано: {toc_file}")
        return toc_file

    def _collect_folder_statistics(self, folder: Path) -> Dict[str, Any]:
        """Собрать статистику о содержимом папки"""

        total_files = 0
        total_subfolders = 0
        total_size = 0
        file_types = {}

        try:
            for item in folder.iterdir():
                if item.is_file():
                    total_files += 1
                    total_size += item.stat().st_size

                    # Подсчет по типам
                    ext = item.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1

                elif item.is_dir() and not item.name.startswith('.'):
                    total_subfolders += 1
        except PermissionError:
            pass

        return {
            "totalFiles": total_files,
            "totalSubfolders": total_subfolders,
            "totalSize": total_size,
            "fileTypes": file_types
        }

    def _detect_file_type(self, file: Path) -> str:
        """Определить тип файла по расширению"""

        ext = file.suffix.lower()

        type_map = {
            '.pdf': 'pdf',
            '.txt': 'txt',
            '.md': 'md',
            '.docx': 'docx',
            '.doc': 'docx',
            '.odt': 'odt',
            '.rtf': 'rtf',
            '.tex': 'tex',
            '.html': 'html',
            '.htm': 'html',
            '.epub': 'epub',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.svg': 'image',
            '.mp4': 'video',
            '.avi': 'video',
            '.mkv': 'video',
            '.mp3': 'audio',
            '.wav': 'audio',
            '.flac': 'audio',
            '.zip': 'archive',
            '.tar': 'archive',
            '.gz': 'archive',
            '.rar': 'archive',
            '.py': 'code',
            '.js': 'code',
            '.java': 'code',
            '.cpp': 'code',
            '.c': 'code',
            '.json': 'data',
            '.xml': 'data',
            '.csv': 'data',
        }

        return type_map.get(ext, 'other')

    def _get_mime_type(self, file: Path) -> str:
        """Получить MIME тип файла"""

        try:
            import mimetypes
            mime_type, _ = mimetypes.guess_type(str(file))
            return mime_type or "application/octet-stream"
        except:
            return "application/octet-stream"

    def _calculate_checksums(self, file: Path) -> Dict[str, str]:
        """Вычислить контрольные суммы файла"""

        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()

        try:
            with open(file, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    md5_hash.update(chunk)
                    sha256_hash.update(chunk)

            return {
                "md5": md5_hash.hexdigest(),
                "sha256": sha256_hash.hexdigest()
            }
        except:
            return {}


def main():
    """Главная функция CLI"""

    parser = argparse.ArgumentParser(
        description="Менеджер метаданных для файлов и папок"
    )

    subparsers = parser.add_subparsers(dest='command', help='Команды')

    # Команда: создать метаданные папки
    folder_parser = subparsers.add_parser('init-folder', help='Инициализировать метаданные папки')
    folder_parser.add_argument('path', help='Путь к папке')
    folder_parser.add_argument('--name', required=True, help='Название папки')
    folder_parser.add_argument('--description', required=True, help='Описание папки')
    folder_parser.add_argument('--category', default='other', help='Категория')
    folder_parser.add_argument('--tags', nargs='*', help='Теги')
    folder_parser.add_argument('--author', help='Автор')
    folder_parser.add_argument('--language', default='ru', help='Язык')

    # Команда: создать метаданные файла
    file_parser = subparsers.add_parser('init-file', help='Инициализировать метаданные файла')
    file_parser.add_argument('path', help='Путь к файлу')
    file_parser.add_argument('--title', required=True, help='Название')
    file_parser.add_argument('--description', default='', help='Описание')
    file_parser.add_argument('--category', help='Категория')
    file_parser.add_argument('--tags', nargs='*', help='Теги')
    file_parser.add_argument('--author', help='Автор')
    file_parser.add_argument('--language', default='ru', help='Язык')

    # Команда: прочитать метаданные
    read_parser = subparsers.add_parser('read', help='Прочитать метаданные')
    read_parser.add_argument('path', help='Путь к файлу или папке')

    # Команда: обновить метаданные
    update_parser = subparsers.add_parser('update', help='Обновить метаданные')
    update_parser.add_argument('path', help='Путь к файлу или папке')
    update_parser.add_argument('--tags', nargs='*', help='Обновить теги')
    update_parser.add_argument('--status', help='Обновить статус')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = MetadataManager()

    try:
        if args.command == 'init-folder':
            manager.create_folder_metadata(
                args.path,
                args.name,
                args.description,
                args.category,
                args.tags,
                args.author,
                args.language
            )

        elif args.command == 'init-file':
            manager.create_file_metadata(
                args.path,
                args.title,
                args.description,
                args.category,
                args.tags,
                args.author,
                args.language
            )

        elif args.command == 'read':
            metadata = manager.read_metadata(args.path)
            if metadata:
                print(json.dumps(metadata, ensure_ascii=False, indent=2))
            else:
                print(f"Метаданные не найдены для: {args.path}")

        elif args.command == 'update':
            updates = {}
            if args.tags:
                updates['tags'] = args.tags
            if args.status:
                updates['status'] = args.status

            if updates:
                manager.update_metadata(args.path, updates)
            else:
                print("Нет изменений для обновления")

    except Exception as e:
        print(f"Ошибка: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
