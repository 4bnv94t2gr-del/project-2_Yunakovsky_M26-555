import re
import shlex

import prompt
from prettytable import PrettyTable

from primitive_db.core import (
    create_table,
    delete,
    drop_table,
    insert,
    select,
    update,
    validate_values,
)
from primitive_db.decorators import handle_db_errors
from primitive_db.parser import parse_set, parse_values, parse_where
from primitive_db.utils import (
    delete_table_data,
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)

METADATA_FILE = "db_meta.json"

def print_help():
    """Выводит справку по доступным командам."""
    print("\n***База данных***")

    print("\nУправление таблицами:")
    print(
        "create_table <имя_таблицы> "
        "<столбец1:тип> ... - создать таблицу"
    )
    print("list_tables - показать список таблиц")
    print("drop_table <имя_таблицы> - удалить таблицу")

    print("\nОперации с данными:")
    print(
        "insert into <имя_таблицы> values "
        "(<значение1>, <значение2>, ...) - добавить запись"
    )
    print("select from <имя_таблицы> - показать все записи")
    print(
        "select from <имя_таблицы> where "
        "<столбец> = <значение> - выбрать записи"
    )
    print(
        "update <имя_таблицы> set <столбец> = <значение> "
        "where <столбец> = <значение> - обновить записи"
    )
    print(
        "delete from <имя_таблицы> where "
        "<столбец> = <значение> - удалить записи"
    )
    print("info <имя_таблицы> - информация о таблице")

    print("\nОбщие команды:")
    print("exit - выход из программы")
    print("help - справочная информация")
    print('\nСтроковые значения вводите в двойных кавычках.\n')


def split_where(text):
    """Отделяет where, игнорируя его внутри строк."""
    in_quotes = False
    escaped = False

    for index, character in enumerate(text):
        if escaped:
            escaped = False
            continue

        if in_quotes and character == "\\":
            escaped = True
            continue

        if character == '"':
            in_quotes = not in_quotes
            continue

        if not in_quotes:
            match = re.match(
                r"\s+where\s+",
                text[index:],
                flags=re.IGNORECASE,
            )
            if match:
                left = text[:index].strip()
                right = text[index + match.end():].strip()
                return left, right

    raise ValueError(
        "Не указано условие where. "
        "Пример: where ID = 1."
    )


def show_records(metadata, table_name, records):
    """Выводит записи в виде таблицы."""
    columns = [
        column.split(":")[0]
        for column in metadata[table_name]
    ]

    table = PrettyTable()
    table.field_names = columns

    for record in records:
        if any(column not in record for column in columns):
            raise ValueError(
                f'Некорректные данные таблицы "{table_name}": '
                "в записи отсутствуют обязательные поля."
            )
        table.add_row([record[column] for column in columns])

    print(table)

    if not records:
        print("Подходящих записей нет.")


@handle_db_errors
def handle_data_command(user_input, metadata):
    """Обрабатывает CRUD и info; возвращает признак обработки."""
    parts = user_input.split(maxsplit=1)

    if not parts:
        return False

    command = parts[0].lower()

    if command not in {"insert", "select", "update", "delete", "info"}:
        return False

    patterns = {
        "insert": r"insert\s+into\s+(\w+)\s+values\s*(\(.*\))",
        "select": r"select\s+from\s+(\w+)(?:\s+where\s+(.+))?",
        "update": r"update\s+(\w+)\s+set\s+(.+)",
        "delete": r"delete\s+from\s+(\w+)\s+where\s+(.+)",
        "info": r"info\s+(\w+)",
    }

    match = re.fullmatch(
        patterns[command],
        user_input,
        flags=re.IGNORECASE,
    )

    if match is None:
        raise ValueError(
            "Некорректный синтаксис команды. Введите help."
        )

    table_name = match.group(1)

    if not table_name.isidentifier():
        raise ValueError(f"Некорректное имя таблицы: {table_name}")

    if table_name not in metadata:
        raise ValueError(f'Таблица "{table_name}" не существует.')

    if command == "insert":
        values = parse_values(match.group(2))
        result = insert(metadata, table_name, values)

        if result is None:
            return True

        save_table_data(table_name, result)
        print(
            f'Запись с ID={result[-1]["ID"]} успешно добавлена '
            f'в таблицу "{table_name}".'
        )
        return True

    table_data = load_table_data(table_name)

    if command == "info":
        print(f"Таблица: {table_name}")
        print(f"Столбцы: {', '.join(metadata[table_name])}")
        print(f"Количество записей: {len(table_data)}")
        return True

    if command == "select":
        condition_text = match.group(2)
        where_clause = None

        if condition_text is not None:
            where_clause = parse_where(condition_text)
            validate_values(metadata, table_name, where_clause)

        result = select(table_data, where_clause)

        if result is None:
            return True

        show_records(metadata, table_name, result)
        return True

    if command == "update":
        set_text, where_text = split_where(match.group(2))
        set_clause = parse_set(set_text)
        where_clause = parse_where(where_text)

        validate_values(metadata, table_name, set_clause)
        validate_values(metadata, table_name, where_clause)

        affected = select(table_data, where_clause)

        if affected is None:
            return True

        result = update(table_data, set_clause, where_clause)
    else:
        where_clause = parse_where(match.group(2))
        validate_values(metadata, table_name, where_clause)

        affected = select(table_data, where_clause)

        if affected is None:
            return True

        result = delete(table_data, where_clause)

    if result is None:
        return True

    if not affected:
        print("Подходящих записей нет.")
        return True

    save_table_data(table_name, result)


    for record in affected:
        record_id = record.get("ID")

        if command == "update":
            print(
                f'Запись с ID={record_id} в таблице '
                f'"{table_name}" успешно обновлена.'
            )
        else:
            print(
                f'Запись с ID={record_id} успешно удалена '
                f'из таблицы "{table_name}".'
            )

    return True


def run():
    print_help()

    while True:
        try:
            metadata = load_metadata(METADATA_FILE)
        except (OSError, ValueError) as error:
            print(f"Ошибка загрузки метаданных: {error}")
            return

        if (
            not isinstance(metadata, dict)
            or not all(
                isinstance(name, str)
                and isinstance(columns, list)
                and all(isinstance(column, str) for column in columns)
                for name, columns in metadata.items()
            )
        ):
            print("Ошибка: некорректная структура файла метаданных.")
            return

        try:
            user_input = prompt.string("\n>>>Введите команду: ")
        except (EOFError, KeyboardInterrupt):
            print()
            return

        user_input = user_input.strip()

        if not user_input:
            continue

        if handle_data_command(user_input, metadata) is not False:
            continue

        try:
            args = shlex.split(user_input)

        except ValueError:
            print(f"Некорректное значение: {user_input}. Попробуйте снова.")
            continue

        if not args:
            continue

        command, *arguments = args

        if command in {"help", "exit", "list_tables"}:
            if arguments:
                value = " ".join(arguments)
                print(f"Некорректное значение: {value}. Попробуйте снова.")
                continue

            if command == "exit":
                return

            if command == "help":
                print_help()
            elif metadata:
                for table_name in metadata:
                    print(f"- {table_name}")
            else:
                print("Таблиц пока нет.")

        elif command in {"create_table", "drop_table"}:
            if not arguments:
                print(
                    "Некорректное значение: не указано имя таблицы. "
                    "Попробуйте снова."
                )
                continue

            if command == "drop_table" and len(arguments) != 1:
                value = " ".join(arguments)
                print(f"Некорректное значение: {value}. Попробуйте снова.")
                continue

            table_name = arguments[0]
            previous_metadata = metadata.copy()


            if command == "create_table":
                result = create_table(
                    metadata, table_name, arguments[1:]
                )
            else:
                result = drop_table(metadata, table_name)

            if result is None:
                continue

            metadata = result

            if metadata == previous_metadata:
                continue


            try:
                if command == "create_table":
                    save_table_data(table_name, [])

                save_metadata(METADATA_FILE, metadata)
            except (OSError, ValueError) as error:
                print(f"Ошибка сохранения таблицы: {error}")
                continue

            if command == "create_table":
                columns = ", ".join(metadata[table_name])
                print(
                    f'Таблица "{table_name}" успешно создана '
                    f"со столбцами: {columns}"
                )
            else:
                try:
                    delete_table_data(table_name)
                except (OSError, ValueError) as error:
                    print(
                        f'Таблица "{table_name}" удалена из метаданных, '
                        f"но файл данных удалить не удалось: {error}"
                    )
                else:
                    print(f'Таблица "{table_name}" успешно удалена.')
        else:
            print(f"Функции {command} нет. Попробуйте снова.")
