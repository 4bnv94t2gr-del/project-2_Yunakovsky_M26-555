import json

from primitive_db.constants import SUPPORTED_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data

_select_cache = create_cacher()

@handle_db_errors
def create_table(metadata, table_name, columns):
    """Проверяет схему и добавляет таблицу в метаданные."""
    if table_name in metadata:
        raise ValueError(f'Таблица "{table_name}" уже существует.')

    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}")

    if not columns:
        raise ValueError("Не указаны столбцы.")

    column_names = {"ID"}

    for column in columns:
        parts = column.split(":")

        if len(parts) != 2:
            raise ValueError(
                f"Некорректное определение столбца: {column}"
            )

        column_name, column_type = parts

        if not column_name.isidentifier():
            raise ValueError(
                f"Некорректное имя столбца: {column_name}"
            )

        if column_name in column_names:
            raise ValueError(
                f'Столбец "{column_name}" указан повторно '
                "или зарезервирован."
            )

        if column_type not in SUPPORTED_TYPES:
            raise ValueError(
                f"Неподдерживаемый тип столбца: {column_type}"
            )

        column_names.add(column_name)

    metadata[table_name] = ["ID:int", *columns]
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удаляет таблицу из метаданных после подтверждения."""
    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    del metadata[table_name]
    return metadata


def validate_values(metadata, table_name, values):
    """Проверяет названия столбцов и типы значений."""
    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    schema = dict(
        column.split(":") for column in metadata[table_name]
    )
    python_types = {"int": int, "str": str, "bool": bool}

    for column_name, value in values.items():
        if column_name not in schema:
            raise ValueError(
                f'Столбец "{column_name}" не существует '
                f'в таблице "{table_name}".'
            )

        column_type = schema[column_name]

        if column_type not in python_types:
            raise ValueError(
                f'Неизвестный тип столбца "{column_name}": {column_type}.'
            )

        if type(value) is not python_types[column_type]:
            raise ValueError(
                f'Столбец "{column_name}" должен иметь тип '
                f"{column_type}, получено: {value!r}."
            )


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Добавляет запись и возвращает данные без сохранения в файл."""
    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    columns = [
        column.split(":")[0]
        for column in metadata[table_name]
        if column.split(":")[0] != "ID"
    ]

    if len(values) != len(columns):
        raise ValueError(
            f"Ожидается значений: {len(columns)}, "
            f"получено: {len(values)}. ID указывать не нужно."
        )

    record = dict(zip(columns, values))
    validate_values(metadata, table_name, record)

    table_data = load_table_data(table_name)

    if any(
        type(row.get("ID")) is not int or row["ID"] < 1
        for row in table_data
    ):
        raise ValueError(
            f'Некорректные ID в данных таблицы "{table_name}".'
        )

    new_id = max(
        (row["ID"] for row in table_data),
        default=0,
    ) + 1

    new_record = {"ID": new_id, **record}
    return [*table_data, new_record]


def matches_where(record, where_clause):
    """Проверяет соответствие записи всем условиям."""
    return all(
        column_name in record
        and type(record[column_name]) is type(value)
        and record[column_name] == value
        for column_name, value in where_clause.items()
    )


@handle_db_errors
@log_time
def select(table_data, where_clause=None):
    """Возвращает копии записей с кэшированием фильтрации."""
    cache_key = json.dumps(
        [table_data, where_clause],
        ensure_ascii=False,
        sort_keys=True,
    )

    def get_records():
        return [
            record.copy()
            for record in table_data
            if where_clause is None
            or matches_where(record, where_clause)
        ]

    cached_records = _select_cache(cache_key, get_records)

    return [record.copy() for record in cached_records]


@handle_db_errors
def update(table_data, set_clause, where_clause):
    """Возвращает данные с обновлёнными записями."""
    if not set_clause:
        raise ValueError("Не указаны новые значения.")

    if "ID" in set_clause:
        raise ValueError("Изменять ID записи нельзя.")

    if not where_clause:
        raise ValueError("Для обновления необходимо условие where.")

    return [
        {**record, **set_clause}
        if matches_where(record, where_clause)
        else record.copy()
        for record in table_data
    ]


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause):
    """Возвращает данные без записей, подходящих под условие."""
    if not where_clause:
        raise ValueError("Для удаления необходимо условие where.")

    return [
        record.copy()
        for record in table_data
        if not matches_where(record, where_clause)
    ]
