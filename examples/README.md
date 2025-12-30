# Примеры использования системы метаданных

Эта папка содержит демонстрационные примеры использования системы метаданных для файлов и папок.

## Структура примеров

```
examples/
└── sample_library/              # Демонстрационная научная библиотека
    ├── .folder-meta.json       # Метаданные библиотеки
    ├── .folder-readme.md       # Описание библиотеки
    └── physics/                # Раздел физики
        ├── .folder-meta.json   # Метаданные раздела
        ├── quantum_intro.txt   # Пример документа
        ├── quantum_intro.meta.json     # Метаданные файла
        ├── quantum_intro.summary.md    # Краткое содержание
        └── quantum_intro.toc.md        # Расширенное оглавление
```

## Тестирование утилит

### 1. Чтение метаданных

```bash
# Прочитать метаданные папки
python3 ../tools/metadata_manager.py read sample_library/

# Прочитать метаданные файла
python3 ../tools/metadata_manager.py read sample_library/physics/quantum_intro.txt
```

### 2. Сканирование библиотеки

```bash
cd examples/

# Сканировать библиотеку рекурсивно
python3 ../tools/crawler.py sample_library/ \
  --recursive \
  --report library_scan.json \
  --html library_scan.html

# Показать файлы без метаданных
python3 ../tools/crawler.py sample_library/ \
  --recursive \
  --list-missing
```

### 3. Поиск по метаданным

```bash
cd examples/

# Текстовый поиск
python3 ../tools/search.py "квантовая" --path sample_library/

# Поиск по тегам
python3 ../tools/search.py --tags "физика" --path sample_library/

# Поиск файлов определенного типа
python3 ../tools/search.py --type txt --path sample_library/

# Показать фасеты (статистику по категориям)
python3 ../tools/search.py --facets --path sample_library/
```

### 4. Добавление нового материала

```bash
cd examples/sample_library/

# Создать новый файл
echo "Содержимое документа" > mathematics/algebra.txt

# Создать метаданные для файла
python3 ../../tools/metadata_manager.py init-file mathematics/algebra.txt \
  --title "Введение в алгебру" \
  --description "Основы алгебры для начинающих" \
  --category "education" \
  --tags "математика" "алгебра" \
  --language "ru"

# Инициализировать метаданные для всей папки mathematics
python3 ../../tools/metadata_manager.py init-folder mathematics/ \
  --name "Математика" \
  --description "Материалы по математике" \
  --category "science" \
  --tags "математика" "наука"
```

### 5. Автоматическая генерация метаданных

```bash
cd examples/

# Автоматически создать метаданные для всех файлов без них
../scripts/auto_metadata.sh sample_library/ --recursive
```

### 6. Обновление метаданных

```bash
# Добавить теги к существующему файлу
python3 ../tools/metadata_manager.py update \
  sample_library/physics/quantum_intro.txt \
  --tags "физика" "квантовая механика" "обучение" "популярная наука"

# Изменить статус
python3 ../tools/metadata_manager.py update \
  sample_library/physics/quantum_intro.txt \
  --status "published"
```

## Создание собственной структуры

### Шаг 1: Создать папку проекта

```bash
mkdir my_library
cd my_library
```

### Шаг 2: Инициализировать метаданные

```bash
# Создать метаданные для главной папки
python3 ../tools/metadata_manager.py init-folder . \
  --name "Моя библиотека" \
  --description "Личная коллекция документов" \
  --category "personal" \
  --tags "библиотека" "документы"

# Создать README
cat > .folder-readme.md << 'EOF'
# Моя библиотека

Описание библиотеки и её содержимого.

## Структура

Здесь будет описание структуры...
EOF
```

### Шаг 3: Добавить документы

```bash
# Создать подпапки
mkdir -p books articles notes

# Добавить файлы и создать метаданные
# ... (используйте команды из раздела 4)
```

### Шаг 4: Индексировать

```bash
# Сканировать и создать индекс
python3 ../tools/crawler.py . \
  --recursive \
  --report index.json \
  --html index.html
```

## Полезные команды

### Вывод в JSON для дальнейшей обработки

```bash
# Экспорт результатов поиска в JSON
python3 ../tools/search.py "физика" --path sample_library/ --json > results.json

# Обработка через jq (если установлен)
python3 ../tools/search.py "физика" --path sample_library/ --json | jq '.files[].title'
```

### Интеграция с Git

```bash
# Добавить метаданные в Git
git add .folder-meta.json *.meta.json *.summary.md *.toc.md

# Коммит
git commit -m "Добавлены метаданные для библиотеки"
```

### Резервное копирование метаданных

```bash
# Собрать все метаданные в архив
find . -name "*.meta.json" -o -name ".folder-meta.json" | \
  tar -czf metadata_backup.tar.gz -T -
```

## Советы

1. **Регулярно обновляйте метаданные** - актуальность информации важна
2. **Используйте теги** - они облегчают поиск
3. **Создавайте summary.md** - краткое содержание экономит время
4. **Сканируйте периодически** - находите файлы без метаданных
5. **Версионируйте через Git** - отслеживайте изменения метаданных

## Расширенные сценарии

### Генерация HTML-каталога

```bash
# Сканировать и создать HTML-отчет
python3 ../tools/crawler.py sample_library/ \
  --recursive \
  --html catalog.html

# Открыть в браузере
xdg-open catalog.html  # Linux
open catalog.html      # macOS
```

### Экспорт метаданных для обработки

```bash
# Собрать все метаданные файлов
find sample_library/ -name "*.meta.json" \
  -exec cat {} \; | jq -s '.' > all_metadata.json
```

### Статистика библиотеки

```bash
# Показать статистику по категориям
python3 ../tools/search.py --facets --path sample_library/ | \
  jq '.categories'
```

## Дополнительная информация

- Полная методология: [../docs/METHODOLOGY.md](../docs/METHODOLOGY.md)
- JSON схемы: [../schemas/](../schemas/)
- Инструменты: [../tools/](../tools/)
- Скрипты: [../scripts/](../scripts/)
