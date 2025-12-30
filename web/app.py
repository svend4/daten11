#!/usr/bin/env python3
"""
Flask приложение для просмотра метаданных - production версия
"""

from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import json
import sys
import os

# Добавить путь к tools
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

app = Flask(__name__,
            static_folder='static',
            static_url_path='/static')

# Конфигурация
# В production путь к документам будет в переменной окружения
DOCUMENTS_PATH = os.getenv('DOCUMENTS_PATH', str(Path(__file__).parent / 'examples' / 'sample_library'))
app.config['DOCUMENTS_PATH'] = Path(DOCUMENTS_PATH)

# Импорт search модуля
try:
    from search import MetadataSearch
except ImportError:
    print("Warning: search module not found, creating dummy")
    class MetadataSearch:
        def __init__(self, path):
            self.base_path = path
            self.results = {"folders": [], "files": []}

        def build_index(self):
            pass

        def search(self, **kwargs):
            return self.results

        def faceted_search(self):
            return {"categories": {}, "tags": {}, "fileTypes": {}}


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/api/search')
def api_search():
    """API для поиска"""
    query = request.args.get('q', '')
    tags = request.args.getlist('tags')
    category = request.args.get('category')
    file_type = request.args.get('type')

    # Инициализировать поиск
    search = MetadataSearch(app.config['DOCUMENTS_PATH'])
    search.build_index()

    # Выполнить поиск
    results = search.search(
        query=query if query else None,
        tags=tags if tags else None,
        category=category if category else None,
        file_type=file_type if file_type else None
    )

    return jsonify(results)


@app.route('/api/facets')
def api_facets():
    """API для получения фасетов"""
    search = MetadataSearch(app.config['DOCUMENTS_PATH'])
    search.build_index()

    facets = search.faceted_search()

    return jsonify(facets)


@app.route('/api/folders')
def api_folders():
    """API для получения списка папок"""
    folders = []

    for folder_meta in app.config['DOCUMENTS_PATH'].rglob('.folder-meta.json'):
        try:
            with open(folder_meta, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                metadata['path'] = str(folder_meta.parent.relative_to(app.config['DOCUMENTS_PATH']))
                folders.append(metadata)
        except Exception as e:
            print(f"Error reading {folder_meta}: {e}")

    return jsonify({'folders': folders})


@app.route('/api/folder/<path:folder_path>')
def api_folder(folder_path):
    """API для получения содержимого папки"""
    folder = app.config['DOCUMENTS_PATH'] / folder_path

    # Метаданные папки
    folder_meta_file = folder / '.folder-meta.json'
    folder_metadata = {}

    if folder_meta_file.exists():
        with open(folder_meta_file, 'r', encoding='utf-8') as f:
            folder_metadata = json.load(f)

    # README
    readme_file = folder / '.folder-readme.md'
    readme = ""

    if readme_file.exists():
        readme = readme_file.read_text(encoding='utf-8')

    # Файлы в папке
    files = []

    for file in folder.iterdir():
        if file.is_file() and not file.name.startswith('.') and not file.name.endswith('.meta.json'):
            meta_file = file.parent / f"{file.stem}.meta.json"

            file_info = {
                'name': file.name,
                'path': str(file.relative_to(app.config['DOCUMENTS_PATH'])),
                'size': file.stat().st_size,
            }

            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        file_info['metadata'] = json.load(f)
                except Exception as e:
                    print(f"Error reading metadata for {file}: {e}")

            files.append(file_info)

    # Подпапки
    subfolders = []

    for subfolder in folder.iterdir():
        if subfolder.is_dir() and not subfolder.name.startswith('.'):
            meta_file = subfolder / '.folder-meta.json'

            subfolder_info = {
                'name': subfolder.name,
                'path': str(subfolder.relative_to(app.config['DOCUMENTS_PATH']))
            }

            if meta_file.exists():
                try:
                    with open(meta_file, 'r', encoding='utf-8') as f:
                        subfolder_info['metadata'] = json.load(f)
                except Exception as e:
                    print(f"Error reading metadata for {subfolder}: {e}")

            subfolders.append(subfolder_info)

    return jsonify({
        'folder': folder_metadata,
        'readme': readme,
        'files': files,
        'subfolders': subfolders
    })


@app.route('/api/file/<path:file_path>')
def api_file(file_path):
    """API для получения информации о файле"""
    file = app.config['DOCUMENTS_PATH'] / file_path

    # Метаданные
    meta_file = file.parent / f"{file.stem}.meta.json"
    metadata = {}

    if meta_file.exists():
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception as e:
            print(f"Error reading metadata: {e}")

    # Summary
    summary_file = file.parent / f"{file.stem}.summary.md"
    summary = ""

    if summary_file.exists():
        summary = summary_file.read_text(encoding='utf-8')

    # TOC
    toc_file = file.parent / f"{file.stem}.toc.md"
    toc = ""

    if toc_file.exists():
        toc = toc_file.read_text(encoding='utf-8')

    return jsonify({
        'file': str(file.name),
        'path': str(file.relative_to(app.config['DOCUMENTS_PATH'])),
        'metadata': metadata,
        'summary': summary,
        'toc': toc
    })


@app.route('/download/<path:file_path>')
def download_file(file_path):
    """Скачать файл"""
    file = app.config['DOCUMENTS_PATH'] / file_path

    if file.exists() and file.is_file():
        return send_file(file, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404


@app.route('/api/stats')
def api_stats():
    """API для статистики"""
    total_files = 0
    total_folders = 0
    total_size = 0

    for file in app.config['DOCUMENTS_PATH'].rglob('*'):
        if file.is_file() and not file.name.startswith('.'):
            total_files += 1
            try:
                total_size += file.stat().st_size
            except:
                pass

    for folder in app.config['DOCUMENTS_PATH'].rglob('*'):
        if folder.is_dir() and not folder.name.startswith('.'):
            total_folders += 1

    return jsonify({
        'total_files': total_files,
        'total_folders': total_folders,
        'total_size': total_size
    })


@app.route('/health')
def health():
    """Health check для Render"""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    # Для локальной разработки
    port = int(os.getenv('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
