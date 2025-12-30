# Руководство по миграции существующих коллекций

## Введение

Это руководство поможет вам применить систему метаданных к вашим существующим коллекциям документов.

## Этап 1: Подготовка и анализ

### 1.1 Инвентаризация

Первым делом проанализируйте вашу коллекцию:

```bash
# Перейдите в директорию с документами
cd /path/to/your/documents

# Сканируйте текущее состояние
python3 /path/to/tools/crawler.py . \
  --recursive \
  --report initial_scan.json \
  --html initial_scan.html

# Посмотрите отчет
firefox initial_scan.html  # или ваш браузер
```

Отчет покажет:
- Сколько у вас папок и файлов
- Распределение по типам файлов
- Общий размер коллекции

### 1.2 Оценка объема работы

```bash
# Подсчитайте количество файлов
find . -type f ! -path '*/\.*' | wc -l

# Подсчитайте по типам
find . -name "*.pdf" | wc -l
find . -name "*.txt" | wc -l
find . -name "*.docx" | wc -l

# Посмотрите структуру папок
tree -d -L 3  # первые 3 уровня
```

### 1.3 Резервное копирование

**ВАЖНО:** Сделайте резервную копию перед началом!

```bash
# Создайте архив
tar -czf ~/documents_backup_$(date +%Y%m%d).tar.gz /path/to/your/documents

# Или используйте rsync
rsync -av /path/to/your/documents/ /backup/location/
```

## Этап 2: Пошаговая миграция

### 2.1 Начните с малого - пилотный проект

Выберите одну небольшую папку для тестирования:

```bash
# Выберите папку с 10-20 файлами
cd /path/to/documents/test_folder

# Создайте метаданные для папки
python3 /path/to/tools/metadata_manager.py init-folder . \
  --name "Тестовая папка" \
  --description "Пилотный проект для проверки системы метаданных" \
  --category "test" \
  --tags "тест" "миграция"

# Проверьте результат
cat .folder-meta.json
```

### 2.2 Автоматическая генерация для простых файлов

```bash
# Автоматически создайте базовые метаданные
/path/to/scripts/auto_metadata.sh . --files-only

# Проверьте созданные файлы
ls -la *.meta.json
```

### 2.3 Ручное улучшение метаданных

Откройте созданные `.meta.json` файлы и улучшите их:

```bash
# Для каждого важного файла
nano document.meta.json

# Добавьте/измените:
# - Более точное описание (description)
# - Релевантные теги (tags)
# - Ключевые слова (keywords)
# - Категорию (category)
```

Пример улучшенных метаданных:

```json
{
  "filename": "project_proposal.pdf",
  "title": "Предложение по проекту модернизации",
  "description": "Детальное предложение по модернизации информационной системы компании с оценкой стоимости и сроков",
  "fileType": "pdf",
  "author": "Иванов И.И.",
  "category": "work",
  "tags": ["проект", "предложение", "модернизация", "ИТ"],
  "keywords": ["информационная система", "бюджет", "сроки", "этапы"],
  "importance": "high",
  "status": "final"
}
```

### 2.4 Создание кратких содержаний

Для важных документов создайте summary:

```bash
# Создайте файл summary
python3 /path/to/tools/metadata_manager.py create-summary document.pdf

# Или вручную
cat > document.summary.md << 'EOF'
# Краткое содержание: Предложение по проекту

## Суть

Предложение описывает модернизацию ИС компании в 3 этапа:
1. Анализ текущего состояния (2 месяца)
2. Разработка и внедрение (6 месяцев)
3. Обучение и поддержка (1 месяц)

## Бюджет

Общий бюджет: 5 млн руб.

## Ключевые риски

- Сопротивление персонала
- Технические ограничения legacy-систем
EOF
```

## Этап 3: Масштабирование на всю коллекцию

### 3.1 Разделение по категориям

Сначала организуйте документы по категориям:

```bash
cd /path/to/documents

# Создайте основные категории
mkdir -p {work,personal,education,archive,projects}

# Переместите документы в соответствующие папки
# (делайте это аккуратно!)
```

### 3.2 Создание метаданных для всех папок

```bash
# Для каждой основной категории
for dir in work personal education archive projects; do
  python3 /path/to/tools/metadata_manager.py init-folder "$dir" \
    --name "$(echo $dir | tr '[:lower:]' '[:upper:]')" \
    --description "Категория: $dir" \
    --category "$dir"
done
```

### 3.3 Пакетная обработка файлов

Используйте скрипт для автоматизации:

```bash
# Создайте скрипт миграции
cat > migrate_all.sh << 'EOF'
#!/bin/bash

BASE_DIR="/path/to/documents"
TOOLS_DIR="/path/to/tools"

# Функция обработки директории
process_dir() {
    local dir="$1"
    echo "Processing: $dir"

    # Создать метаданные папки если нет
    if [ ! -f "$dir/.folder-meta.json" ]; then
        python3 "$TOOLS_DIR/metadata_manager.py" init-folder "$dir" \
            --name "$(basename "$dir")" \
            --description "Auto-generated metadata" \
            --category "other"
    fi

    # Создать метаданные для файлов
    /path/to/scripts/auto_metadata.sh "$dir" --files-only
}

# Обработать все поддиректории
find "$BASE_DIR" -type d -not -path '*/\.*' | while read dir; do
    process_dir "$dir"
done

echo "Migration complete!"
EOF

chmod +x migrate_all.sh
./migrate_all.sh
```

### 3.4 Обработка по типам файлов

Разные типы файлов требуют разного подхода:

#### PDF файлы

```bash
# Извлечь метаданные из PDF
for pdf in $(find . -name "*.pdf"); do
    # Используйте pdfinfo для извлечения метаданных
    pdfinfo "$pdf" > "${pdf%.pdf}_info.txt"

    # Извлеките текст для анализа
    pdftotext "$pdf" "${pdf%.pdf}.txt"
done
```

#### Текстовые файлы

```bash
# Для txt, md файлов
for txt in $(find . -name "*.txt" -o -name "*.md"); do
    # Извлеките первые строки как описание
    head -n 5 "$txt" > "${txt}_preview.txt"
done
```

#### Office документы

```bash
# Используйте Apache Tika для извлечения метаданных
for doc in $(find . -name "*.docx" -o -name "*.doc"); do
    java -jar tika-app.jar --metadata "$doc" > "${doc}_metadata.txt"
done
```

## Этап 4: Постобработка и улучшение

### 4.1 Проверка качества метаданных

```bash
# Сканируйте после миграции
python3 /path/to/tools/crawler.py . \
  --recursive \
  --report post_migration_scan.json \
  --html post_migration_scan.html

# Найдите файлы без метаданных
python3 /path/to/tools/crawler.py . \
  --recursive \
  --list-missing
```

### 4.2 Улучшение с помощью AI (опционально)

Создайте скрипт для генерации описаний через AI:

```bash
cat > ai_enhance.py << 'EOF'
#!/usr/bin/env python3
import json
import openai  # или anthropic
from pathlib import Path

def enhance_metadata(meta_file):
    """Улучшить метаданные с помощью AI"""
    with open(meta_file, 'r') as f:
        metadata = json.load(f)

    # Прочитать содержимое файла
    content_file = Path(meta_file).stem + Path(meta_file).suffix.replace('.meta.json', '')

    if content_file.exists():
        content = content_file.read_text()[:5000]  # первые 5000 символов

        # Запрос к AI
        prompt = f"Создай краткое описание (2-3 предложения) и 5 ключевых слов для документа:\n\n{content}"

        # response = openai.ChatCompletion.create(...)
        # metadata['description'] = response['description']
        # metadata['keywords'] = response['keywords']

        # Сохранить обновленные метаданные
        with open(meta_file, 'w') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

# Обработать все метаданные
for meta_file in Path('.').rglob('*.meta.json'):
    enhance_metadata(meta_file)
EOF

chmod +x ai_enhance.py
./ai_enhance.py
```

### 4.3 Создание индекса

```bash
# Создайте главный индекс
python3 /path/to/tools/crawler.py . \
  --recursive \
  --report master_index.json \
  --html master_index.html

# Создайте README для коллекции
cat > README.md << 'EOF'
# Моя коллекция документов

Последнее обновление: $(date)

## Статистика

- Всего документов: $(find . -type f -name "*.meta.json" | wc -l)
- Категорий: $(find . -name ".folder-meta.json" | wc -l)

## Навигация

- [Рабочие документы](work/)
- [Личные документы](personal/)
- [Образование](education/)
- [Архив](archive/)
- [Проекты](projects/)

## Поиск

Используйте поиск по метаданным:

\`\`\`bash
python3 /path/to/tools/search.py "ваш запрос" --path .
\`\`\`
EOF
```

## Этап 5: Поддержка и обновление

### 5.1 Регулярное обновление

Создайте cron job для регулярного сканирования:

```bash
# Добавьте в crontab
crontab -e

# Сканировать раз в неделю
0 2 * * 0 cd /path/to/documents && python3 /path/to/tools/crawler.py . --recursive --report weekly_scan.json
```

### 5.2 Мониторинг новых файлов

```bash
# Скрипт для отслеживания новых файлов
cat > check_new_files.sh << 'EOF'
#!/bin/bash

NEW_FILES=$(find . -type f -mtime -7 -not -path '*/\.*' -not -name "*.meta.json")

if [ -n "$NEW_FILES" ]; then
    echo "Новые файлы обнаружены:"
    echo "$NEW_FILES"

    # Создать метаданные для новых файлов
    echo "$NEW_FILES" | while read file; do
        if [ ! -f "${file%.*}.meta.json" ]; then
            echo "Создание метаданных для: $file"
            /path/to/scripts/auto_metadata.sh "$file"
        fi
    done
fi
EOF

chmod +x check_new_files.sh
```

### 5.3 Git версионирование метаданных

```bash
# Инициализируйте git для метаданных
cd /path/to/documents
git init

# Добавьте только метаданные
cat > .gitignore << 'EOF'
# Игнорировать сами документы
*.pdf
*.docx
*.doc
*.txt
*.jpg
*.png

# Отслеживать только метаданные
!*.meta.json
!.folder-meta.json
!*.summary.md
!*.toc.md
!.folder-readme.md
EOF

git add -A
git commit -m "Initial metadata commit"
```

## Практические примеры

### Пример 1: Миграция библиотеки PDF книг

```bash
cd ~/Documents/Books

# Шаг 1: Структура по авторам
for pdf in *.pdf; do
    # Извлечь автора из метаданных PDF
    author=$(pdfinfo "$pdf" | grep "Author:" | cut -d: -f2 | xargs)

    if [ -n "$author" ]; then
        mkdir -p "$author"
        mv "$pdf" "$author/"
    fi
done

# Шаг 2: Создать метаданные для каждого автора
for dir in */; do
    python3 /path/to/tools/metadata_manager.py init-folder "$dir" \
        --name "Книги: $(basename "$dir")" \
        --description "Книги автора $(basename "$dir")" \
        --category "education"
done

# Шаг 3: Метаданные для книг
for pdf in */*.pdf; do
    title=$(pdfinfo "$pdf" | grep "Title:" | cut -d: -f2 | xargs)
    author=$(pdfinfo "$pdf" | grep "Author:" | cut -d: -f2 | xargs)

    python3 /path/to/tools/metadata_manager.py init-file "$pdf" \
        --title "$title" \
        --author "$author" \
        --category "education" \
        --tags "книга" "образование"
done
```

### Пример 2: Миграция рабочих документов

```bash
cd ~/Documents/Work

# Организация по годам и проектам
mkdir -p {2023,2024,2025}/{project_a,project_b,reports}

# Перемещение файлов по годам (по дате модификации)
for file in *.pdf *.docx; do
    year=$(date -r "$file" +%Y)

    # Определить тип документа
    if [[ "$file" == *"report"* ]]; then
        mv "$file" "$year/reports/"
    elif [[ "$file" == *"project_a"* ]]; then
        mv "$file" "$year/project_a/"
    fi
done

# Создать метаданные
find . -name "*.pdf" -o -name "*.docx" | while read file; do
    /path/to/scripts/auto_metadata.sh "$file"
done
```

### Пример 3: Миграция коллекции статей

```bash
cd ~/Documents/Articles

# Группировка по темам на основе имен файлов
for article in *.pdf; do
    # Извлечь тему из названия (предполагается формат "Topic_Title.pdf")
    topic=$(echo "$article" | cut -d_ -f1)

    mkdir -p "$topic"
    mv "$article" "$topic/"
done

# Создать детальные метаданные для статей
for pdf in */*.pdf; do
    # Извлечь текст
    text=$(pdftotext "$pdf" - | head -c 1000)

    # Создать метаданные
    python3 /path/to/tools/metadata_manager.py init-file "$pdf" \
        --title "$(basename "$pdf" .pdf)" \
        --category "science" \
        --tags "статья" "наука"

    # Создать краткое содержание (первый абзац)
    pdftotext "$pdf" - | head -n 5 > "${pdf%.pdf}.summary.md"
done
```

## Советы и лучшие практики

### 1. Инкрементальный подход
- Начинайте с малого
- Тестируйте на пилотных папках
- Постепенно расширяйте охват

### 2. Автоматизация
- Создавайте скрипты для повторяющихся задач
- Используйте AI для генерации описаний
- Настройте мониторинг новых файлов

### 3. Качество метаданных
- Ручная проверка важных документов
- Осмысленные теги и категории
- Регулярное обновление

### 4. Версионирование
- Используйте Git для метаданных
- Делайте резервные копии
- Отслеживайте изменения

### 5. Постепенное улучшение
- Не пытайтесь сделать все идеально сразу
- Улучшайте метаданные по мере использования
- Собирайте обратную связь

## Устранение проблем

### Проблема: Слишком много файлов

```bash
# Обрабатывайте порциями
find . -name "*.pdf" | head -n 100 | while read file; do
    /path/to/scripts/auto_metadata.sh "$file"
done
```

### Проблема: Дублирующиеся файлы

```bash
# Найдите дубликаты по контрольной сумме
find . -type f -exec md5sum {} \; | sort | uniq -w32 -D
```

### Проблема: Некорректные метаданные

```bash
# Удалите и пересоздайте
find . -name "*.meta.json" -delete
/path/to/scripts/auto_metadata.sh . --recursive
```

## Следующие шаги

После успешной миграции:
1. Настройте поисковую систему (см. SEARCH_INTEGRATION.md)
2. Добавьте веб-интерфейс (см. WEB_INTERFACE.md)
3. Расширьте автоматизацию с AI (см. AI_AUTOMATION.md)
