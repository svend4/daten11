# Интеграция с поисковыми системами

## Введение

Это руководство описывает интеграцию системы метаданных с мощными поисковыми системами Elasticsearch и Meilisearch для быстрого и точного поиска по большим коллекциям документов.

## Сравнение поисковых систем

| Характеристика | Elasticsearch | Meilisearch |
|---------------|--------------|-------------|
| Сложность настройки | Средняя | Низкая |
| Скорость | Очень быстрая | Очень быстрая |
| Размер индекса | Большой | Компактный |
| Поиск с опечатками | Да | Да (лучше) |
| Фасетный поиск | Да | Да |
| Русский язык | Требует настройки | Отлично из коробки |
| Ресурсы | Много (Java) | Мало (Rust) |
| Рекомендация | Для больших систем | Для малых/средних |

## Часть 1: Интеграция с Elasticsearch

### 1.1 Установка Elasticsearch

#### Docker способ (рекомендуется)

```bash
# Создайте docker-compose.yml
cat > docker-compose-elasticsearch.yml << 'EOF'
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: metadata-elasticsearch
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data

volumes:
  elasticsearch-data:
EOF

# Запустите
docker-compose -f docker-compose-elasticsearch.yml up -d

# Проверьте статус
curl http://localhost:9200
```

#### Локальная установка

```bash
# Для Ubuntu/Debian
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install elasticsearch

# Запустите
sudo systemctl start elasticsearch
sudo systemctl enable elasticsearch
```

### 1.2 Python клиент

```bash
pip install elasticsearch
```

### 1.3 Создание индексатора для Elasticsearch

```python
# tools/elasticsearch_indexer.py
#!/usr/bin/env python3
"""
Индексатор метаданных в Elasticsearch
"""

from elasticsearch import Elasticsearch
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any


class ElasticsearchIndexer:
    """Индексатор для Elasticsearch"""

    def __init__(self, host="localhost", port=9200):
        self.es = Elasticsearch([f"http://{host}:{port}"])
        self.index_name = "documents_metadata"

    def create_index(self):
        """Создать индекс с маппингом"""

        mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "russian": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "russian_stop",
                                "russian_stemmer"
                            ]
                        }
                    },
                    "filter": {
                        "russian_stop": {
                            "type": "stop",
                            "stopwords": "_russian_"
                        },
                        "russian_stemmer": {
                            "type": "stemmer",
                            "language": "russian"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "filename": {
                        "type": "keyword"
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "russian",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "russian"
                    },
                    "abstract": {
                        "type": "text",
                        "analyzer": "russian"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "russian"
                    },
                    "fileType": {
                        "type": "keyword"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "tags": {
                        "type": "keyword"
                    },
                    "keywords": {
                        "type": "keyword"
                    },
                    "author": {
                        "type": "keyword"
                    },
                    "language": {
                        "type": "keyword"
                    },
                    "created": {
                        "type": "date"
                    },
                    "updated": {
                        "type": "date"
                    },
                    "size": {
                        "type": "long"
                    },
                    "importance": {
                        "type": "keyword"
                    },
                    "status": {
                        "type": "keyword"
                    },
                    "file_path": {
                        "type": "keyword"
                    },
                    "folder_path": {
                        "type": "keyword"
                    }
                }
            }
        }

        # Удалить старый индекс если существует
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)

        # Создать новый индекс
        self.es.indices.create(index=self.index_name, body=mapping)
        print(f"✓ Индекс '{self.index_name}' создан")

    def index_document(self, file_path: Path, metadata: Dict[str, Any]):
        """Индексировать документ"""

        # Подготовить документ для индексации
        doc = {
            "filename": metadata.get("filename", file_path.name),
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "abstract": metadata.get("abstract", ""),
            "fileType": metadata.get("fileType", ""),
            "category": metadata.get("category", ""),
            "tags": metadata.get("tags", []),
            "keywords": metadata.get("keywords", []),
            "author": metadata.get("author", ""),
            "language": metadata.get("language", "ru"),
            "created": metadata.get("created", datetime.now().isoformat()),
            "updated": metadata.get("updated", datetime.now().isoformat()),
            "size": metadata.get("size", 0),
            "importance": metadata.get("importance", "medium"),
            "status": metadata.get("status", "final"),
            "file_path": str(file_path),
            "folder_path": str(file_path.parent)
        }

        # Добавить содержимое если есть
        summary_file = file_path.parent / f"{file_path.stem}.summary.md"
        if summary_file.exists():
            doc["content"] = summary_file.read_text(encoding='utf-8')

        # Индексировать
        doc_id = str(file_path).replace("/", "_")

        self.es.index(
            index=self.index_name,
            id=doc_id,
            document=doc
        )

    def index_collection(self, base_path: Path):
        """Индексировать всю коллекцию"""

        count = 0

        print(f"🔨 Индексация коллекции: {base_path}")

        for meta_file in base_path.rglob("*.meta.json"):
            if meta_file.name.startswith('.folder-'):
                continue

            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                file_path = meta_file.parent / metadata['filename']

                self.index_document(file_path, metadata)
                count += 1

                if count % 100 == 0:
                    print(f"  Проиндексировано: {count} документов")

            except Exception as e:
                print(f"  ⚠ Ошибка {meta_file}: {e}")

        print(f"✓ Проиндексировано: {count} документов")

        # Обновить индекс
        self.es.indices.refresh(index=self.index_name)

    def search(self, query: str, filters: Dict[str, Any] = None, size: int = 10):
        """Поиск документов"""

        # Построить запрос
        must_clauses = []

        # Текстовый поиск по всем полям
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",
                        "description^2",
                        "abstract^2",
                        "keywords^2",
                        "content",
                        "tags"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })

        # Фильтры
        filter_clauses = []

        if filters:
            if filters.get("category"):
                filter_clauses.append({
                    "term": {"category": filters["category"]}
                })

            if filters.get("fileType"):
                filter_clauses.append({
                    "term": {"fileType": filters["fileType"]}
                })

            if filters.get("tags"):
                filter_clauses.append({
                    "terms": {"tags": filters["tags"]}
                })

            if filters.get("author"):
                filter_clauses.append({
                    "term": {"author": filters["author"]}
                })

        # Составить полный запрос
        body = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            },
            "size": size,
            "highlight": {
                "fields": {
                    "title": {},
                    "description": {},
                    "content": {}
                }
            }
        }

        # Выполнить поиск
        response = self.es.search(index=self.index_name, body=body)

        return response

    def get_aggregations(self):
        """Получить агрегации (фасеты)"""

        body = {
            "size": 0,
            "aggs": {
                "by_category": {
                    "terms": {"field": "category", "size": 20}
                },
                "by_type": {
                    "terms": {"field": "fileType", "size": 20}
                },
                "by_tags": {
                    "terms": {"field": "tags", "size": 50}
                },
                "by_author": {
                    "terms": {"field": "author", "size": 20}
                }
            }
        }

        response = self.es.search(index=self.index_name, body=body)

        return response["aggregations"]


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Индексатор Elasticsearch"
    )

    parser.add_argument('--create-index', action='store_true',
                        help='Создать индекс')
    parser.add_argument('--index-collection', type=str,
                        help='Проиндексировать коллекцию')
    parser.add_argument('--search', type=str,
                        help='Поисковый запрос')
    parser.add_argument('--category', type=str,
                        help='Фильтр по категории')
    parser.add_argument('--type', type=str,
                        help='Фильтр по типу')

    args = parser.parse_args()

    indexer = ElasticsearchIndexer()

    if args.create_index:
        indexer.create_index()

    if args.index_collection:
        indexer.index_collection(Path(args.index_collection))

    if args.search:
        filters = {}
        if args.category:
            filters['category'] = args.category
        if args.type:
            filters['fileType'] = args.type

        results = indexer.search(args.search, filters=filters)

        print(f"\n🔍 Найдено: {results['hits']['total']['value']} документов\n")

        for hit in results['hits']['hits']:
            source = hit['_source']
            score = hit['_score']

            print(f"📄 {source['title']} (score: {score:.2f})")
            print(f"   {source['description'][:100]}...")
            print(f"   Путь: {source['file_path']}")

            if 'highlight' in hit:
                for field, highlights in hit['highlight'].items():
                    print(f"   💡 {field}: {highlights[0]}")

            print()


if __name__ == "__main__":
    main()
```

### 1.4 Использование Elasticsearch

```bash
# Создать индекс
python3 tools/elasticsearch_indexer.py --create-index

# Проиндексировать коллекцию
python3 tools/elasticsearch_indexer.py --index-collection /path/to/documents

# Поиск
python3 tools/elasticsearch_indexer.py --search "квантовая механика"

# Поиск с фильтрами
python3 tools/elasticsearch_indexer.py --search "физика" --category "science" --type "pdf"
```

## Часть 2: Интеграция с Meilisearch

### 2.1 Установка Meilisearch

#### Docker способ

```bash
# Запустите Meilisearch
docker run -d \
  --name meilisearch \
  -p 7700:7700 \
  -v $(pwd)/meili_data:/meili_data \
  getmeili/meilisearch:v1.5

# Проверьте статус
curl http://localhost:7700/health
```

#### Локальная установка

```bash
# Скачайте и установите
curl -L https://install.meilisearch.com | sh

# Запустите
./meilisearch

# Или как сервис
sudo systemctl start meilisearch
```

### 2.2 Python клиент

```bash
pip install meilisearch
```

### 2.3 Создание индексатора для Meilisearch

```python
# tools/meilisearch_indexer.py
#!/usr/bin/env python3
"""
Индексатор метаданных в Meilisearch
"""

import meilisearch
from pathlib import Path
import json
from typing import Dict, Any, List


class MeilisearchIndexer:
    """Индексатор для Meilisearch"""

    def __init__(self, host="http://localhost:7700", api_key=None):
        self.client = meilisearch.Client(host, api_key)
        self.index_name = "documents"

    def create_index(self):
        """Создать индекс с настройками"""

        try:
            # Создать индекс
            index = self.client.create_index(
                self.index_name,
                {'primaryKey': 'id'}
            )

            # Настроить searchable attributes
            self.client.index(self.index_name).update_searchable_attributes([
                'title',
                'description',
                'abstract',
                'keywords',
                'tags',
                'content',
                'author'
            ])

            # Настроить filterable attributes
            self.client.index(self.index_name).update_filterable_attributes([
                'category',
                'fileType',
                'tags',
                'author',
                'language',
                'importance',
                'status'
            ])

            # Настроить sortable attributes
            self.client.index(self.index_name).update_sortable_attributes([
                'created',
                'updated',
                'size',
                'title'
            ])

            # Настроить ranking rules
            self.client.index(self.index_name).update_ranking_rules([
                'words',
                'typo',
                'proximity',
                'attribute',
                'sort',
                'exactness'
            ])

            print(f"✓ Индекс '{self.index_name}' создан")

        except Exception as e:
            print(f"Индекс уже существует: {e}")

    def index_document(self, file_path: Path, metadata: Dict[str, Any]):
        """Индексировать документ"""

        # Создать уникальный ID
        doc_id = str(file_path).replace("/", "_")

        # Подготовить документ
        doc = {
            "id": doc_id,
            "filename": metadata.get("filename", file_path.name),
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "abstract": metadata.get("abstract", ""),
            "fileType": metadata.get("fileType", ""),
            "category": metadata.get("category", ""),
            "tags": metadata.get("tags", []),
            "keywords": metadata.get("keywords", []),
            "author": metadata.get("author", ""),
            "language": metadata.get("language", "ru"),
            "created": metadata.get("created", ""),
            "updated": metadata.get("updated", ""),
            "size": metadata.get("size", 0),
            "importance": metadata.get("importance", "medium"),
            "status": metadata.get("status", "final"),
            "file_path": str(file_path),
            "folder_path": str(file_path.parent)
        }

        # Добавить содержимое
        summary_file = file_path.parent / f"{file_path.stem}.summary.md"
        if summary_file.exists():
            doc["content"] = summary_file.read_text(encoding='utf-8')[:5000]

        return doc

    def index_collection(self, base_path: Path):
        """Проиндексировать всю коллекцию"""

        documents = []
        count = 0

        print(f"🔨 Индексация коллекции: {base_path}")

        for meta_file in base_path.rglob("*.meta.json"):
            if meta_file.name.startswith('.folder-'):
                continue

            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                file_path = meta_file.parent / metadata['filename']

                doc = self.index_document(file_path, metadata)
                documents.append(doc)
                count += 1

                # Индексировать пачками по 100
                if len(documents) >= 100:
                    self.client.index(self.index_name).add_documents(documents)
                    documents = []
                    print(f"  Проиндексировано: {count} документов")

            except Exception as e:
                print(f"  ⚠ Ошибка {meta_file}: {e}")

        # Индексировать оставшиеся
        if documents:
            self.client.index(self.index_name).add_documents(documents)

        print(f"✓ Проиндексировано: {count} документов")

    def search(self, query: str, filters: Dict[str, Any] = None, limit: int = 20):
        """Поиск документов"""

        # Подготовить фильтры
        filter_str = None

        if filters:
            filter_parts = []

            if filters.get("category"):
                filter_parts.append(f'category = "{filters["category"]}"')

            if filters.get("fileType"):
                filter_parts.append(f'fileType = "{filters["fileType"]}"')

            if filters.get("tags"):
                tags_filter = " OR ".join([f'tags = "{tag}"' for tag in filters["tags"]])
                filter_parts.append(f"({tags_filter})")

            if filter_parts:
                filter_str = " AND ".join(filter_parts)

        # Выполнить поиск
        results = self.client.index(self.index_name).search(
            query,
            {
                'limit': limit,
                'filter': filter_str,
                'attributesToHighlight': ['title', 'description', 'content'],
                'highlightPreTag': '<mark>',
                'highlightPostTag': '</mark>'
            }
        )

        return results

    def get_facets(self):
        """Получить фасеты"""

        # Meilisearch требует запрос для фасетов
        results = self.client.index(self.index_name).search(
            "",
            {
                'facets': ['category', 'fileType', 'tags', 'author']
            }
        )

        return results.get('facetDistribution', {})


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Индексатор Meilisearch"
    )

    parser.add_argument('--create-index', action='store_true',
                        help='Создать индекс')
    parser.add_argument('--index-collection', type=str,
                        help='Проиндексировать коллекцию')
    parser.add_argument('--search', type=str,
                        help='Поисковый запрос')
    parser.add_argument('--category', type=str,
                        help='Фильтр по категории')
    parser.add_argument('--type', type=str,
                        help='Фильтр по типу')

    args = parser.parse_args()

    indexer = MeilisearchIndexer()

    if args.create_index:
        indexer.create_index()

    if args.index_collection:
        indexer.index_collection(Path(args.index_collection))

    if args.search:
        filters = {}
        if args.category:
            filters['category'] = args.category
        if args.type:
            filters['fileType'] = args.type

        results = indexer.search(args.search, filters=filters)

        print(f"\n🔍 Найдено: {results['estimatedTotalHits']} документов")
        print(f"⏱ Время поиска: {results['processingTimeMs']} мс\n")

        for hit in results['hits']:
            print(f"📄 {hit['title']}")
            print(f"   {hit['description'][:100]}...")
            print(f"   Путь: {hit['file_path']}")

            if '_formatted' in hit:
                if hit['_formatted'].get('title') != hit['title']:
                    print(f"   💡 {hit['_formatted']['title']}")

            print()


if __name__ == "__main__":
    main()
```

### 2.4 Использование Meilisearch

```bash
# Создать индекс
python3 tools/meilisearch_indexer.py --create-index

# Проиндексировать коллекцию
python3 tools/meilisearch_indexer.py --index-collection /path/to/documents

# Поиск (с исправлением опечаток!)
python3 tools/meilisearch_indexer.py --search "кванто вая механка"

# Поиск с фильтрами
python3 tools/meilisearch_indexer.py --search "физика" --category "science"
```

## Часть 3: Автоматическое обновление индексов

### 3.1 Watchdog для отслеживания изменений

```python
# tools/index_watcher.py
#!/usr/bin/env python3
"""
Отслеживание изменений и автообновление индексов
"""

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import json
import time


class MetadataHandler(FileSystemEventHandler):
    """Обработчик изменений метаданных"""

    def __init__(self, indexer):
        self.indexer = indexer

    def on_created(self, event):
        if event.src_path.endswith('.meta.json'):
            self.update_index(event.src_path)

    def on_modified(self, event):
        if event.src_path.endswith('.meta.json'):
            self.update_index(event.src_path)

    def update_index(self, meta_path):
        """Обновить индекс для файла"""

        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            file_path = Path(meta_path).parent / metadata['filename']

            self.indexer.index_document(file_path, metadata)
            print(f"✓ Обновлен индекс для: {file_path.name}")

        except Exception as e:
            print(f"⚠ Ошибка обновления индекса: {e}")


def watch_directory(documents_path, indexer_type="meilisearch"):
    """Отслеживать директорию"""

    if indexer_type == "meilisearch":
        from meilisearch_indexer import MeilisearchIndexer
        indexer = MeilisearchIndexer()
    else:
        from elasticsearch_indexer import ElasticsearchIndexer
        indexer = ElasticsearchIndexer()

    event_handler = MetadataHandler(indexer)
    observer = Observer()
    observer.schedule(event_handler, documents_path, recursive=True)
    observer.start()

    print(f"👀 Отслеживание изменений в: {documents_path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python3 index_watcher.py /path/to/documents [meilisearch|elasticsearch]")
        sys.exit(1)

    docs_path = sys.argv[1]
    indexer_type = sys.argv[2] if len(sys.argv) > 2 else "meilisearch"

    watch_directory(docs_path, indexer_type)
```

### 3.2 Использование

```bash
# Установите watchdog
pip install watchdog

# Запустите отслеживание
python3 tools/index_watcher.py /path/to/documents meilisearch
```

## Часть 4: Интеграция с веб-интерфейсом

Обновите `web/app.py` для использования поисковых систем:

```python
# Добавьте в web/app.py

from meilisearch_indexer import MeilisearchIndexer

# Инициализировать при старте
meilisearch = MeilisearchIndexer()


@app.route('/api/search/meili')
def api_search_meili():
    """Поиск через Meilisearch"""

    query = request.args.get('q', '')
    category = request.args.get('category')
    file_type = request.args.get('type')

    filters = {}
    if category:
        filters['category'] = category
    if file_type:
        filters['fileType'] = file_type

    results = meilisearch.search(query, filters=filters)

    return jsonify(results)
```

## Заключение

Теперь у вас есть мощная поисковая система:

- **Elasticsearch** для больших коллекций и сложной аналитики
- **Meilisearch** для быстрого и простого поиска с отличной поддержкой опечаток
- Автоматическое обновление индексов
- Интеграция с веб-интерфейсом

Следующие шаги:
1. Добавьте семантический поиск (vector search)
2. Настройте релевантность
3. Добавьте рекомендации похожих документов
4. Создайте дашборды для аналитики
