import json
import os

from primitive_db.constants import DATA_DIR


def load_metadata(filepath):
    """Загружает метаданные; возвращает пустой словарь без файла."""
    try:
        with open(filepath, encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_metadata(filepath, data):
    """Сохраняет метаданные в JSON-файл."""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")


def load_table_data(table_name):
    """Загружает записи таблицы из JSON-файла."""
    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}")

    filepath = os.path.join(DATA_DIR, f"{table_name}.json")

    try:
        with open(filepath, encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return []

    if not isinstance(data, list) or not all(
        isinstance(record, dict) for record in data
    ):
        raise ValueError(
            f'Некорректная структура данных таблицы "{table_name}".'
        )

    return data


def save_table_data(table_name, data):
    """Сохраняет записи таблицы в JSON-файл."""
    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}")

    if not isinstance(data, list) or not all(
        isinstance(record, dict) for record in data
    ):
        raise ValueError(
            f'Некорректная структура данных таблицы "{table_name}".'
        )

    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, f"{table_name}.json")

    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
        file.write("\n")


def delete_table_data(table_name):
    """Удаляет файл данных таблицы, если он существует."""
    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}")

    filepath = os.path.join(DATA_DIR, f"{table_name}.json")

    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass
