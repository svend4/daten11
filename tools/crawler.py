#!/usr/bin/env python3
"""
Краулер для сканирования файловой системы
Автоматическое обнаружение и индексация файлов
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse
from datetime import datetime


class FileCrawler:
    """Краулер для сканирования файловой системы"""

    def __init__(self, base_path: str = ".", exclude_patterns: Optional[List[str]] = None):
        self.base_path = Path(base_path).resolve()
        self.exclude_patterns = exclude_patterns or [
            '.git', '.svn', 'node_modules', '__pycache__',
            '.DS_Store', 'Thumbs.db', '.venv', 'venv'
        ]
        self.results = {
            "scannedAt": datetime.now().isoformat(),
            "basePath": str(self.base_path),
            "folders": [],
            "files": [],
            "statistics": {
                "totalFolders": 0,
                "totalFiles": 0,
                "totalSize": 0,
                "filesByType": {},
                "filesWithMetadata": 0,
                "filesWithoutMetadata": 0
            }
        }

    def should_exclude(self, path: Path) -> bool:
        """Проверить, нужно ли исключить путь"""

        for pattern in self.exclude_patterns:
            if pattern in path.parts:
                return True

        # Исключить скрытые файлы и папки (начинающиеся с .)
        if path.name.startswith('.') and not path.name.endswith('.json'):
            return True

        return False

    def scan(self, recursive: bool = True, max_depth: Optional[int] = None) -> Dict[str, Any]:
        """Сканировать файловую систему"""

        print(f"🔍 Сканирование: {self.base_path}")

        if recursive:
            self._scan_recursive(self.base_path, depth=0, max_depth=max_depth)
        else:
            self._scan_directory(self.base_path)

        print(f"✓ Сканирование завершено")
        print(f"  Папок: {self.results['statistics']['totalFolders']}")
        print(f"  Файлов: {self.results['statistics']['totalFiles']}")
        print(f"  Общий размер: {self._format_size(self.results['statistics']['totalSize'])}")

        return self.results

    def _scan_recursive(self, path: Path, depth: int = 0, max_depth: Optional[int] = None):
        """Рекурсивное сканирование"""

        if max_depth is not None and depth > max_depth:
            return

        try:
            for item in sorted(path.iterdir()):
                if self.should_exclude(item):
                    continue

                if item.is_dir():
                    self._process_folder(item)
                    self._scan_recursive(item, depth + 1, max_depth)

                elif item.is_file():
                    self._process_file(item)

        except PermissionError as e:
            print(f"⚠ Нет доступа: {path}")

    def _scan_directory(self, path: Path):
        """Сканировать одну директорию"""

        try:
            for item in sorted(path.iterdir()):
                if self.should_exclude(item):
                    continue

                if item.is_dir():
                    self._process_folder(item)
                elif item.is_file():
                    self._process_file(item)

        except PermissionError:
            print(f"⚠ Нет доступа: {path}")

    def _process_folder(self, folder: Path):
        """Обработать папку"""

        meta_file = folder / ".folder-meta.json"
        has_metadata = meta_file.exists()

        folder_info = {
            "path": str(folder.relative_to(self.base_path)),
            "name": folder.name,
            "hasMetadata": has_metadata,
            "metadataFile": str(meta_file.relative_to(self.base_path)) if has_metadata else None
        }

        if has_metadata:
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    folder_info["metadata"] = {
                        "description": metadata.get("description", ""),
                        "category": metadata.get("category", ""),
                        "tags": metadata.get("tags", [])
                    }
            except:
                pass

        self.results["folders"].append(folder_info)
        self.results["statistics"]["totalFolders"] += 1

    def _process_file(self, file: Path):
        """Обработать файл"""

        # Пропустить метаданные и служебные файлы
        if file.name.startswith('.folder-') or file.suffix == '.meta.json' or file.name.endswith('.summary.md') or file.name.endswith('.toc.md'):
            return

        meta_file = file.parent / f"{file.stem}.meta.json"
        summary_file = file.parent / f"{file.stem}.summary.md"
        toc_file = file.parent / f"{file.stem}.toc.md"

        has_metadata = meta_file.exists()

        stat = file.stat()

        file_info = {
            "path": str(file.relative_to(self.base_path)),
            "name": file.name,
            "extension": file.suffix,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "hasMetadata": has_metadata,
            "hasSummary": summary_file.exists(),
            "hasToc": toc_file.exists(),
            "metadataFile": str(meta_file.relative_to(self.base_path)) if has_metadata else None
        }

        if has_metadata:
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    file_info["metadata"] = {
                        "title": metadata.get("title", ""),
                        "description": metadata.get("description", ""),
                        "fileType": metadata.get("fileType", ""),
                        "tags": metadata.get("tags", [])
                    }
                self.results["statistics"]["filesWithMetadata"] += 1
            except:
                pass
        else:
            self.results["statistics"]["filesWithoutMetadata"] += 1

        self.results["files"].append(file_info)
        self.results["statistics"]["totalFiles"] += 1
        self.results["statistics"]["totalSize"] += stat.st_size

        # Статистика по типам
        ext = file.suffix.lower()
        self.results["statistics"]["filesByType"][ext] = \
            self.results["statistics"]["filesByType"].get(ext, 0) + 1

    def find_files_without_metadata(self) -> List[Dict[str, Any]]:
        """Найти все файлы без метаданных"""

        return [f for f in self.results["files"] if not f["hasMetadata"]]

    def generate_report(self, output_file: str = "scan_report.json"):
        """Сгенерировать отчет о сканировании"""

        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"✓ Отчет сохранен: {output_path}")

    def generate_html_report(self, output_file: str = "scan_report.html"):
        """Сгенерировать HTML отчет"""

        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет сканирования - {self.base_path.name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #0066cc;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h2 {{
            margin-top: 0;
            color: #333;
        }}
        .file-list {{
            list-style: none;
            padding: 0;
        }}
        .file-item {{
            padding: 10px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .file-item:hover {{
            background: #f9f9f9;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            margin-left: 5px;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .file-path {{
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Отчет сканирования</h1>
        <p><strong>Путь:</strong> {self.base_path}</p>
        <p><strong>Дата:</strong> {self.results['scannedAt']}</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{self.results['statistics']['totalFolders']}</div>
            <div class="stat-label">Папок</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.results['statistics']['totalFiles']}</div>
            <div class="stat-label">Файлов</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self._format_size(self.results['statistics']['totalSize'])}</div>
            <div class="stat-label">Общий размер</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.results['statistics']['filesWithMetadata']}</div>
            <div class="stat-label">С метаданными</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{self.results['statistics']['filesWithoutMetadata']}</div>
            <div class="stat-label">Без метаданных</div>
        </div>
    </div>

    <div class="section">
        <h2>📁 Файлы без метаданных</h2>
        <ul class="file-list">
"""

        files_without_meta = self.find_files_without_metadata()
        if files_without_meta:
            for file in files_without_meta[:50]:  # Показать первые 50
                html += f"""
            <li class="file-item">
                <div>
                    <strong>{file['name']}</strong>
                    <div class="file-path">{file['path']}</div>
                </div>
                <span class="badge badge-warning">Нет метаданных</span>
            </li>
"""
        else:
            html += "            <li class='file-item'>Все файлы имеют метаданные!</li>"

        html += """
        </ul>
    </div>

    <div class="section">
        <h2>📈 Распределение по типам файлов</h2>
        <ul class="file-list">
"""

        for ext, count in sorted(self.results['statistics']['filesByType'].items(), key=lambda x: x[1], reverse=True):
            html += f"            <li class='file-item'><strong>{ext or 'без расширения'}</strong> <span>{count} файлов</span></li>\n"

        html += """
        </ul>
    </div>
</body>
</html>
"""

        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✓ HTML отчет сохранен: {output_path}")

    def _format_size(self, size: int) -> str:
        """Форматировать размер в читаемый вид"""

        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ПБ"


def main():
    """Главная функция CLI"""

    parser = argparse.ArgumentParser(
        description="Краулер для сканирования файловой системы"
    )

    parser.add_argument('path', nargs='?', default='.', help='Путь для сканирования')
    parser.add_argument('-r', '--recursive', action='store_true', help='Рекурсивное сканирование')
    parser.add_argument('--max-depth', type=int, help='Максимальная глубина сканирования')
    parser.add_argument('--exclude', nargs='*', help='Паттерны для исключения')
    parser.add_argument('--report', default='scan_report.json', help='Файл отчета (JSON)')
    parser.add_argument('--html', help='Создать HTML отчет')
    parser.add_argument('--list-missing', action='store_true', help='Показать файлы без метаданных')

    args = parser.parse_args()

    crawler = FileCrawler(args.path, args.exclude)
    results = crawler.scan(recursive=args.recursive, max_depth=args.max_depth)

    # Сохранить JSON отчет
    crawler.generate_report(args.report)

    # Сохранить HTML отчет
    if args.html:
        crawler.generate_html_report(args.html)

    # Показать файлы без метаданных
    if args.list_missing:
        files_without_meta = crawler.find_files_without_metadata()
        if files_without_meta:
            print(f"\n📋 Файлы без метаданных ({len(files_without_meta)}):")
            for file in files_without_meta:
                print(f"  - {file['path']}")
        else:
            print("\n✓ Все файлы имеют метаданные!")

    return 0


if __name__ == "__main__":
    exit(main())
