# Веб-интерфейс для навигации

## Введение

Этот документ описывает создание веб-интерфейса для просмотра, поиска и управления метаданными документов.

## Архитектура

```
┌──────────────┐
│   Frontend   │  React/Vue или простой HTML+JS
│  (Browser)   │
└──────┬───────┘
       │ HTTP/REST API
       ▼
┌──────────────┐
│   Backend    │  Flask/FastAPI
│   (Python)   │
└──────┬───────┘
       │
       ├──► Файловая система (метаданные)
       ├──► Поисковая система (опционально)
       └──► База данных (опционально)
```

## Вариант 1: Простой Flask интерфейс

### 1.1 Установка зависимостей

```bash
cd /path/to/project
python3 -m venv venv
source venv/bin/activate

pip install flask flask-cors jinja2
```

### 1.2 Backend (Flask приложение)

Создайте файл `web/app.py`:

```python
#!/usr/bin/env python3
"""
Flask приложение для просмотра метаданных
"""

from flask import Flask, render_template, jsonify, request, send_file
from pathlib import Path
import json
import sys

# Добавить путь к tools
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from search import MetadataSearch

app = Flask(__name__)
app.config['DOCUMENTS_PATH'] = Path('/path/to/documents')


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
        with open(folder_meta, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            metadata['path'] = str(folder_meta.parent.relative_to(app.config['DOCUMENTS_PATH']))
            folders.append(metadata)

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
                with open(meta_file, 'r', encoding='utf-8') as f:
                    file_info['metadata'] = json.load(f)

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
                with open(meta_file, 'r', encoding='utf-8') as f:
                    subfolder_info['metadata'] = json.load(f)

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
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

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
            total_size += file.stat().st_size

    for folder in app.config['DOCUMENTS_PATH'].rglob('*'):
        if folder.is_dir() and not folder.name.startswith('.'):
            total_folders += 1

    return jsonify({
        'total_files': total_files,
        'total_folders': total_folders,
        'total_size': total_size
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

### 1.3 Frontend (HTML шаблоны)

Создайте `web/templates/index.html`:

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Библиотека документов</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 24px;
            margin-bottom: 10px;
        }

        .search-container {
            background: white;
            padding: 20px;
            margin: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .search-box {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }

        .search-box input {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 16px;
        }

        .search-box button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
        }

        .search-box button:hover {
            background: #5568d3;
        }

        .filters {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .filters select {
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
        }

        .main-content {
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
            margin: 0 20px;
        }

        .sidebar {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: fit-content;
        }

        .sidebar h3 {
            margin-bottom: 15px;
            color: #333;
        }

        .facet-list {
            list-style: none;
        }

        .facet-list li {
            padding: 8px 0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #f0f0f0;
        }

        .facet-list li:hover {
            color: #667eea;
        }

        .content {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .file-card {
            background: #fafafa;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .file-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .file-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }

        .file-description {
            color: #666;
            margin-bottom: 10px;
        }

        .file-meta {
            display: flex;
            gap: 15px;
            font-size: 14px;
            color: #999;
        }

        .tag {
            display: inline-block;
            padding: 4px 8px;
            background: #e0e7ff;
            color: #667eea;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 5px;
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
        }

        .modal-content {
            background: white;
            max-width: 800px;
            margin: 50px auto;
            padding: 30px;
            border-radius: 8px;
            max-height: 80vh;
            overflow-y: auto;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .close-btn {
            cursor: pointer;
            font-size: 24px;
            color: #999;
        }

        .close-btn:hover {
            color: #333;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e0e0e0;
        }

        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
        }

        .tab.active {
            border-bottom-color: #667eea;
            color: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📚 Библиотека документов</h1>
        <p>Система управления метаданными</p>
    </div>

    <div class="search-container">
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="Поиск документов...">
            <button onclick="performSearch()">🔍 Поиск</button>
        </div>

        <div class="filters">
            <select id="categoryFilter">
                <option value="">Все категории</option>
            </select>
            <select id="typeFilter">
                <option value="">Все типы</option>
            </select>
        </div>
    </div>

    <div class="main-content">
        <div class="sidebar">
            <h3>Категории</h3>
            <ul class="facet-list" id="categoriesFacet"></ul>

            <h3 style="margin-top: 20px;">Теги</h3>
            <ul class="facet-list" id="tagsFacet"></ul>

            <h3 style="margin-top: 20px;">Типы файлов</h3>
            <ul class="facet-list" id="typesFacet"></ul>
        </div>

        <div class="content">
            <div class="results-header">
                <h2>Результаты поиска</h2>
                <span id="resultsCount"></span>
            </div>

            <div id="results"></div>
        </div>
    </div>

    <div class="modal" id="fileModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalTitle"></h2>
                <span class="close-btn" onclick="closeModal()">&times;</span>
            </div>

            <div class="tabs">
                <div class="tab active" onclick="switchTab('info')">Информация</div>
                <div class="tab" onclick="switchTab('summary')">Краткое содержание</div>
                <div class="tab" onclick="switchTab('toc')">Оглавление</div>
            </div>

            <div id="tab-info" class="tab-content active"></div>
            <div id="tab-summary" class="tab-content"></div>
            <div id="tab-toc" class="tab-content"></div>

            <div style="margin-top: 20px;">
                <button onclick="downloadFile()" style="padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer;">
                    📥 Скачать файл
                </button>
            </div>
        </div>
    </div>

    <script>
        let currentFilePath = null;

        // Загрузить фасеты при старте
        async function loadFacets() {
            const response = await fetch('/api/facets');
            const facets = await response.json();

            // Категории
            const categoriesEl = document.getElementById('categoriesFacet');
            Object.entries(facets.categories).forEach(([cat, count]) => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${cat}</span><span>${count}</span>`;
                li.onclick = () => filterByCategory(cat);
                categoriesEl.appendChild(li);
            });

            // Теги
            const tagsEl = document.getElementById('tagsFacet');
            Object.entries(facets.tags).slice(0, 10).forEach(([tag, count]) => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${tag}</span><span>${count}</span>`;
                li.onclick = () => filterByTag(tag);
                tagsEl.appendChild(li);
            });

            // Типы
            const typesEl = document.getElementById('typesFacet');
            Object.entries(facets.fileTypes).forEach(([type, count]) => {
                const li = document.createElement('li');
                li.innerHTML = `<span>${type}</span><span>${count}</span>`;
                li.onclick = () => filterByType(type);
                typesEl.appendChild(li);
            });
        }

        // Поиск
        async function performSearch() {
            const query = document.getElementById('searchInput').value;
            const category = document.getElementById('categoryFilter').value;
            const type = document.getElementById('typeFilter').value;

            let url = '/api/search?';
            if (query) url += `q=${encodeURIComponent(query)}&`;
            if (category) url += `category=${category}&`;
            if (type) url += `type=${type}&`;

            const response = await fetch(url);
            const results = await response.json();

            displayResults(results);
        }

        // Отобразить результаты
        function displayResults(results) {
            const resultsEl = document.getElementById('results');
            const total = results.files.length + results.folders.length;

            document.getElementById('resultsCount').textContent = `Найдено: ${total}`;

            resultsEl.innerHTML = '';

            // Файлы
            results.files.forEach(file => {
                const card = document.createElement('div');
                card.className = 'file-card';
                card.onclick = () => showFileDetails(file._path + '/' + file.filename);

                const tags = file.tags ? file.tags.map(tag =>
                    `<span class="tag">${tag}</span>`
                ).join('') : '';

                card.innerHTML = `
                    <div class="file-title">📄 ${file.title || file.filename}</div>
                    <div class="file-description">${file.description || 'Нет описания'}</div>
                    <div>${tags}</div>
                    <div class="file-meta">
                        <span>Тип: ${file.fileType}</span>
                        <span>Категория: ${file.category || 'N/A'}</span>
                    </div>
                `;

                resultsEl.appendChild(card);
            });

            // Папки
            results.folders.forEach(folder => {
                const card = document.createElement('div');
                card.className = 'file-card';
                card.style.borderLeftColor = '#10b981';

                const tags = folder.tags ? folder.tags.map(tag =>
                    `<span class="tag">${tag}</span>`
                ).join('') : '';

                card.innerHTML = `
                    <div class="file-title">📁 ${folder.name}</div>
                    <div class="file-description">${folder.description || 'Нет описания'}</div>
                    <div>${tags}</div>
                `;

                resultsEl.appendChild(card);
            });
        }

        // Показать детали файла
        async function showFileDetails(filePath) {
            currentFilePath = filePath;

            const response = await fetch(`/api/file/${filePath}`);
            const data = await response.json();

            document.getElementById('modalTitle').textContent = data.file;

            // Информация
            const infoEl = document.getElementById('tab-info');
            const metadata = data.metadata;

            let infoHTML = '<div style="line-height: 1.8;">';

            if (metadata.description) {
                infoHTML += `<p><strong>Описание:</strong> ${metadata.description}</p>`;
            }

            if (metadata.author) {
                infoHTML += `<p><strong>Автор:</strong> ${metadata.author}</p>`;
            }

            if (metadata.category) {
                infoHTML += `<p><strong>Категория:</strong> ${metadata.category}</p>`;
            }

            if (metadata.tags && metadata.tags.length > 0) {
                infoHTML += `<p><strong>Теги:</strong> ${metadata.tags.map(t => `<span class="tag">${t}</span>`).join('')}</p>`;
            }

            if (metadata.keywords && metadata.keywords.length > 0) {
                infoHTML += `<p><strong>Ключевые слова:</strong> ${metadata.keywords.join(', ')}</p>`;
            }

            if (metadata.created) {
                infoHTML += `<p><strong>Создан:</strong> ${new Date(metadata.created).toLocaleString('ru-RU')}</p>`;
            }

            infoHTML += '</div>';

            infoEl.innerHTML = infoHTML;

            // Summary
            document.getElementById('tab-summary').innerHTML = data.summary ?
                `<div style="white-space: pre-wrap;">${data.summary}</div>` :
                '<p>Краткое содержание отсутствует</p>';

            // TOC
            document.getElementById('tab-toc').innerHTML = data.toc ?
                `<div style="white-space: pre-wrap;">${data.toc}</div>` :
                '<p>Оглавление отсутствует</p>';

            document.getElementById('fileModal').style.display = 'block';
        }

        function closeModal() {
            document.getElementById('fileModal').style.display = 'none';
        }

        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(`tab-${tab}`).classList.add('active');
        }

        function downloadFile() {
            if (currentFilePath) {
                window.location.href = `/download/${currentFilePath}`;
            }
        }

        function filterByCategory(cat) {
            document.getElementById('categoryFilter').value = cat;
            performSearch();
        }

        function filterByTag(tag) {
            document.getElementById('searchInput').value = tag;
            performSearch();
        }

        function filterByType(type) {
            document.getElementById('typeFilter').value = type;
            performSearch();
        }

        // Поиск по Enter
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        // Загрузить данные при старте
        window.onload = () => {
            loadFacets();
            performSearch();
        };
    </script>
</body>
</html>
```

### 1.4 Запуск приложения

```bash
cd web

# Обновите путь к документам в app.py
# app.config['DOCUMENTS_PATH'] = Path('/path/to/your/documents')

python3 app.py

# Откройте в браузере
# http://localhost:5000
```

## Вариант 2: Современный Stack (React + FastAPI)

Для более мощного интерфейса см. файл `/docs/WEB_INTERFACE_ADVANCED.md` (создан отдельно).

## Следующие шаги

После создания веб-интерфейса:
1. Добавьте аутентификацию
2. Интегрируйте с Elasticsearch (см. SEARCH_INTEGRATION.md)
3. Добавьте редактирование метаданных
4. Создайте дашборды и аналитику
