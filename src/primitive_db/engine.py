import shlex

import prompt

from primitive_db.core import create_table, drop_table
from primitive_db.utils import load_metadata, save_metadata

METADATA_FILE = "db_meta.json"

HELP_TEXT = """***База данных***

Функции:
<command> create_table <имя_таблицы> <столбец1:тип> ... - создать таблицу
<command> list_tables - показать список всех таблиц
<command> drop_table <имя_таблицы> - удалить таблицу
<command> exit - выход из программы
<command> help - справочная информация"""

def run():
    print(HELP_TEXT)

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
                print(HELP_TEXT)
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
                metadata = create_table(
                    metadata, table_name, arguments[1:]
                )
            else:
                metadata = drop_table(metadata, table_name)

            if metadata == previous_metadata:
                continue

            try:
                save_metadata(METADATA_FILE, metadata)
            except OSError as error:
                print(f"Ошибка сохранения метаданных: {error}")
                continue

            if command == "create_table":
                columns = ", ".join(metadata[table_name])
                print(
                    f'Таблица "{table_name}" успешно создана '
                    f"со столбцами: {columns}"
                )
            else:
                print(f'Таблица "{table_name}" успешно удалена.')

        else:
            print(f"Функции {command} нет. Попробуйте снова.")
