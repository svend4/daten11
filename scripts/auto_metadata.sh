#!/bin/bash
# Автоматическая генерация метаданных для файлов и папок

set -e

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Автоматическая генерация метаданных${NC}"
echo ""

# Проверка аргументов
if [ $# -lt 1 ]; then
    echo "Использование: $0 <путь> [опции]"
    echo ""
    echo "Опции:"
    echo "  --folders-only    Создать метаданные только для папок"
    echo "  --files-only      Создать метаданные только для файлов"
    echo "  --recursive       Рекурсивная обработка"
    echo ""
    exit 1
fi

TARGET_PATH="$1"
shift

# Опции по умолчанию
PROCESS_FOLDERS=true
PROCESS_FILES=true
RECURSIVE=false

# Разбор опций
while [[ $# -gt 0 ]]; do
    case $1 in
        --folders-only)
            PROCESS_FILES=false
            shift
            ;;
        --files-only)
            PROCESS_FOLDERS=false
            shift
            ;;
        --recursive)
            RECURSIVE=true
            shift
            ;;
        *)
            echo -e "${RED}Неизвестная опция: $1${NC}"
            exit 1
            ;;
    esac
done

# Функция для создания метаданных папки
create_folder_metadata() {
    local folder_path="$1"
    local meta_file="$folder_path/.folder-meta.json"

    # Пропустить если метаданные уже существуют
    if [ -f "$meta_file" ]; then
        echo -e "${YELLOW}⏭  Метаданные уже существуют: $folder_path${NC}"
        return
    fi

    # Получить название папки
    local folder_name=$(basename "$folder_path")

    # Создать метаданные
    echo -e "${GREEN}📁 Создание метаданных для папки: $folder_name${NC}"

    python3 ../tools/metadata_manager.py init-folder "$folder_path" \
        --name "$folder_name" \
        --description "Автоматически созданное описание для $folder_name" \
        --category "other" \
        --language "ru"
}

# Функция для создания метаданных файла
create_file_metadata() {
    local file_path="$1"
    local meta_file="${file_path%.*}.meta.json"

    # Пропустить если метаданные уже существуют
    if [ -f "$meta_file" ]; then
        return
    fi

    # Пропустить служебные файлы
    local filename=$(basename "$file_path")
    if [[ "$filename" == .* ]] || [[ "$filename" == *.meta.json ]] || [[ "$filename" == *.summary.md ]] || [[ "$filename" == *.toc.md ]]; then
        return
    fi

    # Создать метаданные
    echo -e "${GREEN}📄 Создание метаданных для файла: $filename${NC}"

    python3 ../tools/metadata_manager.py init-file "$file_path" \
        --title "$filename" \
        --description "Автоматически созданное описание" \
        --language "ru"
}

# Функция для обработки директории
process_directory() {
    local dir_path="$1"

    # Создать метаданные для папки
    if [ "$PROCESS_FOLDERS" = true ]; then
        create_folder_metadata "$dir_path"
    fi

    # Обработать файлы
    if [ "$PROCESS_FILES" = true ]; then
        for file in "$dir_path"/*; do
            if [ -f "$file" ]; then
                create_file_metadata "$file"
            fi
        done
    fi

    # Рекурсивная обработка
    if [ "$RECURSIVE" = true ]; then
        for subdir in "$dir_path"/*; do
            if [ -d "$subdir" ]; then
                # Пропустить скрытые папки и служебные
                local dirname=$(basename "$subdir")
                if [[ ! "$dirname" =~ ^\. ]] && [ "$dirname" != "node_modules" ] && [ "$dirname" != "__pycache__" ]; then
                    process_directory "$subdir"
                fi
            fi
        done
    fi
}

# Проверить что путь существует
if [ ! -e "$TARGET_PATH" ]; then
    echo -e "${RED}❌ Путь не найден: $TARGET_PATH${NC}"
    exit 1
fi

# Обработать путь
if [ -d "$TARGET_PATH" ]; then
    process_directory "$TARGET_PATH"
elif [ -f "$TARGET_PATH" ]; then
    if [ "$PROCESS_FILES" = true ]; then
        create_file_metadata "$TARGET_PATH"
    fi
else
    echo -e "${RED}❌ Неподдерживаемый тип пути: $TARGET_PATH${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Генерация метаданных завершена${NC}"
