# Расширение автоматизации с помощью AI

## Введение

Это руководство описывает, как использовать AI для автоматической генерации метаданных, описаний и анализа содержимого документов.

## Обзор возможностей

С помощью AI можно автоматизировать:
- Генерацию описаний и аннотаций
- Извлечение ключевых слов и тем
- Создание кратких содержаний
- Категоризацию документов
- Извлечение сущностей (имена, даты, места)
- Определение языка документа
- Генерацию тегов
- Создание связей между документами

## Архитектура AI-расширения

```
┌─────────────────┐
│   Документ      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Извлечение     │
│  текста         │
│  (PDF, DOCX)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Предобработка  │
│  • Очистка      │
│  • Разбиение    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI обработка   │
│  • LLM          │
│  • NLP          │
│  • Embeddings   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Метаданные     │
│  .meta.json     │
└─────────────────┘
```

## Часть 1: Использование OpenAI / Anthropic API

### 1.1 Установка зависимостей

```bash
# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установите библиотеки
pip install openai anthropic tiktoken python-dotenv pypdf2 python-docx
```

### 1.2 Настройка API ключей

```bash
# Создайте .env файл
cat > .env << 'EOF'
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
EOF

# Не добавляйте .env в git!
echo ".env" >> .gitignore
```

### 1.3 Создание AI обработчика

```python
# tools/ai_metadata_generator.py
#!/usr/bin/env python3
"""
AI-генератор метаданных для документов
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import anthropic
from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv()


class AIMetadataGenerator:
    """Генератор метаданных с использованием AI"""

    def __init__(self, provider="anthropic"):
        self.provider = provider

        if provider == "anthropic":
            self.client = anthropic.Anthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        elif provider == "openai":
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")
            self.client = openai

    def extract_text(self, file_path: Path) -> str:
        """Извлечь текст из файла"""

        if file_path.suffix == '.pdf':
            return self._extract_from_pdf(file_path)
        elif file_path.suffix in ['.txt', '.md']:
            return file_path.read_text(encoding='utf-8')
        elif file_path.suffix in ['.docx']:
            return self._extract_from_docx(file_path)
        else:
            return ""

    def _extract_from_pdf(self, file_path: Path) -> str:
        """Извлечь текст из PDF"""
        try:
            import PyPDF2
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                # Извлечь первые 10 страниц
                for page in reader.pages[:10]:
                    text += page.extract_text()
                return text
        except Exception as e:
            print(f"Ошибка извлечения из PDF: {e}")
            return ""

    def _extract_from_docx(self, file_path: Path) -> str:
        """Извлечь текст из DOCX"""
        try:
            import docx
            doc = docx.Document(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            print(f"Ошибка извлечения из DOCX: {e}")
            return ""

    def generate_metadata(self, file_path: Path, text: str) -> Dict[str, Any]:
        """Сгенерировать метаданные с помощью AI"""

        # Ограничить текст для экономии токенов
        text_sample = text[:5000]

        prompt = f"""Проанализируй следующий документ и создай метаданные в JSON формате.

Документ: {file_path.name}

Содержимое (первые 5000 символов):
{text_sample}

Создай метаданные со следующими полями:
- title: краткое название документа (20-50 слов)
- description: описание содержимого (2-3 предложения)
- abstract: аннотация (50-100 слов)
- keywords: массив из 5-10 ключевых слов
- tags: массив из 3-5 тегов для категоризации
- category: основная категория (education, work, science, personal, etc.)
- subject: основная тема документа
- language: язык документа (ru, en, de, etc.)
- importance: важность (critical, high, medium, low)

Верни только JSON, без дополнительных объяснений."""

        if self.provider == "anthropic":
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = message.content[0].text

        elif self.provider == "openai":
            response = self.client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Ты эксперт по анализу документов."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices[0].message.content

        # Парсинг JSON ответа
        try:
            # Извлечь JSON из ответа (может быть в markdown блоке)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            metadata = json.loads(response_text.strip())
            return metadata

        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"Ответ AI: {response_text}")
            return {}

    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Сгенерировать краткое содержание"""

        text_sample = text[:8000]

        prompt = f"""Создай краткое содержание (summary) следующего документа.

Требования:
- Длина: {max_length} слов
- Формат: связный текст, 2-3 абзаца
- Включи основные идеи и выводы
- Пиши на том же языке, что и документ

Документ:
{text_sample}

Краткое содержание:"""

        if self.provider == "anthropic":
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text

        elif self.provider == "openai":
            response = self.client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content

    def generate_toc(self, text: str) -> list:
        """Сгенерировать оглавление"""

        text_sample = text[:10000]

        prompt = f"""Проанализируй структуру документа и создай оглавление.

Документ:
{text_sample}

Создай оглавление в JSON формате:
[
  {{"title": "Раздел 1", "level": 1, "summary": "краткое описание"}},
  {{"title": "Подраздел 1.1", "level": 2, "summary": "описание"}},
  ...
]

Верни только JSON массив."""

        if self.provider == "anthropic":
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = message.content[0].text
        else:
            response = self.client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices[0].message.content

        try:
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            return json.loads(response_text.strip())
        except:
            return []

    def process_document(self, file_path: Path, output_dir: Optional[Path] = None):
        """Полная обработка документа"""

        print(f"📄 Обработка: {file_path.name}")

        # Извлечь текст
        print("  Извлечение текста...")
        text = self.extract_text(file_path)

        if not text:
            print("  ⚠ Не удалось извлечь текст")
            return

        # Генерация метаданных
        print("  Генерация метаданных...")
        ai_metadata = self.generate_metadata(file_path, text)

        # Загрузить существующие метаданные или создать новые
        meta_file = file_path.parent / f"{file_path.stem}.meta.json"

        if meta_file.exists():
            with open(meta_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            from datetime import datetime
            metadata = {
                "filename": file_path.name,
                "created": datetime.now().isoformat(),
            }

        # Объединить с AI метаданными
        metadata.update(ai_metadata)
        metadata["updated"] = datetime.now().isoformat()
        metadata["ai_generated"] = True

        # Сохранить метаданные
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Метаданные: {meta_file.name}")

        # Генерация краткого содержания
        print("  Генерация summary...")
        summary = self.generate_summary(text)
        summary_file = file_path.parent / f"{file_path.stem}.summary.md"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# Краткое содержание: {file_path.name}\n\n")
            f.write(summary)
        print(f"  ✓ Summary: {summary_file.name}")

        # Генерация оглавления
        print("  Генерация оглавления...")
        toc = self.generate_toc(text)

        if toc:
            toc_file = file_path.parent / f"{file_path.stem}.toc.md"
            with open(toc_file, 'w', encoding='utf-8') as f:
                f.write(f"# Оглавление: {file_path.name}\n\n")
                for item in toc:
                    indent = "  " * (item.get("level", 1) - 1)
                    f.write(f"{indent}- {item['title']}\n")
                    if item.get("summary"):
                        f.write(f"{indent}  {item['summary']}\n")
            print(f"  ✓ TOC: {toc_file.name}")

        print(f"✓ Обработка завершена: {file_path.name}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="AI генератор метаданных"
    )
    parser.add_argument('file', help='Путь к файлу')
    parser.add_argument('--provider', choices=['anthropic', 'openai'],
                        default='anthropic', help='AI провайдер')

    args = parser.parse_args()

    generator = AIMetadataGenerator(provider=args.provider)
    generator.process_document(Path(args.file))


if __name__ == "__main__":
    main()
```

Сохраните это как `/path/to/tools/ai_metadata_generator.py` и сделайте исполняемым.

### 1.4 Использование AI генератора

```bash
# Для одного файла
python3 tools/ai_metadata_generator.py document.pdf

# С OpenAI вместо Anthropic
python3 tools/ai_metadata_generator.py document.pdf --provider openai

# Пакетная обработка
find /path/to/documents -name "*.pdf" | while read file; do
    python3 tools/ai_metadata_generator.py "$file"
done
```

## Часть 2: Использование локальных NLP моделей

Для работы без интернета и API ключей используйте локальные модели.

### 2.1 Установка spaCy

```bash
pip install spacy

# Скачайте русскую модель
python3 -m spacy download ru_core_news_lg

# Для английского
python3 -m spacy download en_core_web_lg
```

### 2.2 NLP процессор

```python
# tools/nlp_metadata_generator.py
#!/usr/bin/env python3
"""
Локальный NLP генератор метаданных
"""

import spacy
from pathlib import Path
from collections import Counter
import json


class NLPMetadataGenerator:
    """Генератор метаданных с локальными NLP моделями"""

    def __init__(self, language="ru"):
        if language == "ru":
            self.nlp = spacy.load("ru_core_news_lg")
        else:
            self.nlp = spacy.load("en_core_web_lg")

    def extract_keywords(self, text: str, top_n: int = 10) -> list:
        """Извлечь ключевые слова"""

        doc = self.nlp(text)

        # Собрать существительные и имена собственные
        keywords = []
        for token in doc:
            if token.pos_ in ['NOUN', 'PROPN'] and not token.is_stop:
                keywords.append(token.lemma_.lower())

        # Подсчитать частоту
        counter = Counter(keywords)
        return [word for word, count in counter.most_common(top_n)]

    def extract_entities(self, text: str) -> dict:
        """Извлечь именованные сущности"""

        doc = self.nlp(text)

        entities = {
            "persons": [],
            "organizations": [],
            "locations": [],
            "dates": []
        }

        for ent in doc.ents:
            if ent.label_ == "PER":
                entities["persons"].append(ent.text)
            elif ent.label_ == "ORG":
                entities["organizations"].append(ent.text)
            elif ent.label_ == "LOC":
                entities["locations"].append(ent.text)
            elif ent.label_ == "DATE":
                entities["dates"].append(ent.text)

        # Убрать дубликаты
        for key in entities:
            entities[key] = list(set(entities[key]))

        return entities

    def generate_summary(self, text: str, num_sentences: int = 3) -> str:
        """Простое извлечение первых предложений"""

        doc = self.nlp(text)
        sentences = [sent.text for sent in doc.sents]

        return " ".join(sentences[:num_sentences])

    def detect_language(self, text: str) -> str:
        """Определить язык текста"""

        from langdetect import detect
        try:
            return detect(text)
        except:
            return "unknown"

    def process_document(self, file_path: Path):
        """Обработать документ"""

        # Извлечь текст (используйте тот же метод, что и в AI генераторе)
        # ...

        text = file_path.read_text(encoding='utf-8')[:10000]

        # Анализ
        keywords = self.extract_keywords(text)
        entities = self.extract_entities(text)
        summary = self.generate_summary(text)
        language = self.detect_language(text)

        # Создать метаданные
        metadata = {
            "filename": file_path.name,
            "keywords": keywords,
            "entities": entities,
            "abstract": summary,
            "language": language,
            "nlp_generated": True
        }

        # Сохранить
        meta_file = file_path.parent / f"{file_path.stem}.meta.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"✓ Обработан: {file_path.name}")
```

### 2.3 Использование

```bash
# Установите langdetect
pip install langdetect

# Обработайте документ
python3 tools/nlp_metadata_generator.py document.txt
```

## Часть 3: Векторные представления и семантический поиск

### 3.1 Генерация embeddings

```python
# tools/embeddings_generator.py
#!/usr/bin/env python3
"""
Генератор векторных представлений для семантического поиска
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import json
from pathlib import Path


class EmbeddingsGenerator:
    """Генератор embeddings для документов"""

    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2"):
        # Мультиязычная модель
        self.model = SentenceTransformer(model_name)

    def generate_embedding(self, text: str) -> np.ndarray:
        """Сгенерировать embedding для текста"""
        return self.model.encode(text)

    def process_document(self, file_path: Path):
        """Создать embedding для документа"""

        # Прочитать текст
        text = file_path.read_text(encoding='utf-8')[:5000]

        # Сгенерировать embedding
        embedding = self.generate_embedding(text)

        # Сохранить
        embedding_file = file_path.parent / f"{file_path.stem}.embedding.npy"
        np.save(embedding_file, embedding)

        # Добавить в метаданные
        meta_file = file_path.parent / f"{file_path.stem}.meta.json"
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                metadata = json.load(f)

            metadata["embedding_file"] = str(embedding_file.name)
            metadata["embedding_model"] = "paraphrase-multilingual-MiniLM-L12-v2"

            with open(meta_file, 'w') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"✓ Embedding создан: {file_path.name}")

    def find_similar(self, query: str, documents_dir: Path, top_k: int = 5):
        """Найти похожие документы"""

        query_embedding = self.generate_embedding(query)

        similarities = []

        for embedding_file in documents_dir.rglob("*.embedding.npy"):
            doc_embedding = np.load(embedding_file)

            # Косинусное сходство
            similarity = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )

            similarities.append({
                "file": embedding_file.stem,
                "similarity": float(similarity)
            })

        # Сортировать по сходству
        similarities.sort(key=lambda x: x["similarity"], reverse=True)

        return similarities[:top_k]


# Использование
if __name__ == "__main__":
    gen = EmbeddingsGenerator()

    # Создать embeddings
    gen.process_document(Path("document.txt"))

    # Поиск похожих
    results = gen.find_similar("квантовая физика", Path("."))
    for result in results:
        print(f"{result['file']}: {result['similarity']:.3f}")
```

### 3.2 Установка и использование

```bash
# Установить sentence-transformers
pip install sentence-transformers

# Генерация embeddings
python3 tools/embeddings_generator.py

# Семантический поиск
python3 tools/embeddings_generator.py --query "квантовая механика" --search
```

## Часть 4: Пакетная обработка и очереди

### 4.1 Создание системы очередей

```python
# tools/batch_processor.py
#!/usr/bin/env python3
"""
Пакетная обработка документов с очередями
"""

import asyncio
from pathlib import Path
from queue import Queue
from threading import Thread
from ai_metadata_generator import AIMetadataGenerator


class BatchProcessor:
    """Пакетный процессор документов"""

    def __init__(self, num_workers: int = 3):
        self.queue = Queue()
        self.num_workers = num_workers
        self.generator = AIMetadataGenerator()

    def add_documents(self, directory: Path, pattern: str = "*.pdf"):
        """Добавить документы в очередь"""

        for file_path in directory.rglob(pattern):
            # Проверить, нет ли уже метаданных
            meta_file = file_path.parent / f"{file_path.stem}.meta.json"

            if not meta_file.exists():
                self.queue.put(file_path)

        print(f"Добавлено в очередь: {self.queue.qsize()} документов")

    def worker(self):
        """Рабочий процесс"""

        while True:
            try:
                file_path = self.queue.get(timeout=1)

                try:
                    self.generator.process_document(file_path)
                except Exception as e:
                    print(f"Ошибка обработки {file_path}: {e}")

                self.queue.task_done()

            except:
                break

    def process_all(self):
        """Обработать все документы в очереди"""

        # Запустить workers
        threads = []
        for i in range(self.num_workers):
            t = Thread(target=self.worker)
            t.start()
            threads.append(t)

        # Дождаться завершения
        self.queue.join()

        # Остановить workers
        for t in threads:
            t.join(timeout=1)

        print("✓ Все документы обработаны")


# Использование
if __name__ == "__main__":
    processor = BatchProcessor(num_workers=3)
    processor.add_documents(Path("/path/to/documents"), "*.pdf")
    processor.process_all()
```

## Часть 5: Интеграция с существующими инструментами

### 5.1 Обновление crawler.py

Добавьте AI обработку в существующий crawler:

```python
# В crawler.py добавьте:

def process_with_ai(self, file_path: Path):
    """Обработать файл с AI если нет метаданных"""

    meta_file = file_path.parent / f"{file_path.stem}.meta.json"

    if not meta_file.exists():
        try:
            from ai_metadata_generator import AIMetadataGenerator
            generator = AIMetadataGenerator()
            generator.process_document(file_path)
        except Exception as e:
            print(f"AI обработка не удалась: {e}")
```

## Часть 6: Мониторинг и отчеты

### 6.1 Создание дашборда обработки

```python
# tools/processing_dashboard.py
#!/usr/bin/env python3
"""
Дашборд для мониторинга AI обработки
"""

import json
from pathlib import Path
from datetime import datetime


def generate_report(documents_dir: Path):
    """Создать отчет об обработке"""

    total_files = 0
    ai_generated = 0
    nlp_generated = 0
    manual = 0
    no_metadata = 0

    for file in documents_dir.rglob("*"):
        if file.is_file() and file.suffix in ['.pdf', '.txt', '.docx']:
            total_files += 1

            meta_file = file.parent / f"{file.stem}.meta.json"

            if meta_file.exists():
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)

                if metadata.get("ai_generated"):
                    ai_generated += 1
                elif metadata.get("nlp_generated"):
                    nlp_generated += 1
                else:
                    manual += 1
            else:
                no_metadata += 1

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_files": total_files,
        "ai_generated": ai_generated,
        "nlp_generated": nlp_generated,
        "manual": manual,
        "no_metadata": no_metadata,
        "completion_rate": (total_files - no_metadata) / total_files * 100 if total_files > 0 else 0
    }

    print(f"📊 Отчет обработки:")
    print(f"  Всего файлов: {total_files}")
    print(f"  AI генерация: {ai_generated}")
    print(f"  NLP генерация: {nlp_generated}")
    print(f"  Ручная обработка: {manual}")
    print(f"  Без метаданных: {no_metadata}")
    print(f"  Готовность: {report['completion_rate']:.1f}%")

    return report
```

## Заключение

С AI автоматизацией вы можете:
- Обработать тысячи документов автоматически
- Получить высококачественные метаданные
- Создать семантический поиск
- Сэкономить часы ручной работы

Следующий шаг: создайте веб-интерфейс (см. WEB_INTERFACE.md) и интегрируйте с поисковыми системами (см. SEARCH_INTEGRATION.md).
