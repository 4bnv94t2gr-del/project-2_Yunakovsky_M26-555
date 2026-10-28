import json
import re


def split_outside_quotes(text, separator):
    """Разделяет текст, не затрагивая разделители внутри строк."""
    parts = []
    start = 0
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

        if character == separator and not in_quotes:
            parts.append(text[start:index].strip())
            start = index + 1

    if in_quotes:
        raise ValueError("Не закрыты двойные кавычки.")

    parts.append(text[start:].strip())
    return parts


def parse_value(text):
    """Преобразует значение в str, int или bool."""
    text = text.strip()

    if not text:
        raise ValueError("Не указано значение.")

    if text.startswith('"'):
        try:
            value = json.loads(text)
        except ValueError as error:
            raise ValueError(
                "Некорректная строка. Используйте двойные кавычки "
                "и корректное экранирование."
            ) from error

        if not isinstance(value, str):
            raise ValueError("Ожидалась строка в двойных кавычках.")

        return value

    if text.lower() == "true":
        return True

    if text.lower() == "false":
        return False

    if re.fullmatch(r"[+-]?[0-9]+", text):
        try:
            return int(text)
        except ValueError as error:
            raise ValueError("Некорректное целое число.") from error

    raise ValueError(
        f"Некорректное значение: {text}. "
        "Допустимы целые числа, true, false "
        "и строки в двойных кавычках."
    )


def parse_values(text):
    """Разбирает список значений вместе с внешними скобками."""
    text = text.strip()

    if not (text.startswith("(") and text.endswith(")")):
        raise ValueError("Значения должны быть заключены в скобки.")

    content = text[1:-1].strip()

    if not content:
        raise ValueError("Не указаны значения для вставки.")

    return [
        parse_value(part)
        for part in split_outside_quotes(content, ",")
    ]


def parse_assignment(text):
    """Разбирает выражение вида имя_столбца = значение."""
    parts = split_outside_quotes(text, "=")

    if len(parts) != 2:
        raise ValueError(
            "Ожидается выражение: <столбец> = <значение>."
        )

    column_name, value_text = parts

    if not column_name.isidentifier():
        raise ValueError(
            f"Некорректное имя столбца: {column_name}."
        )

    return column_name, parse_value(value_text)


def parse_where(text):
    """Разбирает одно условие без ключевого слова where."""
    column_name, value = parse_assignment(text)
    return {column_name: value}


def parse_set(text):
    """Разбирает присваивания без ключевого слова set."""
    result = {}

    for part in split_outside_quotes(text, ","):
        column_name, value = parse_assignment(part)

        if column_name in result:
            raise ValueError(
                f'Столбец "{column_name}" указан несколько раз.'
            )

        result[column_name] = value

    return result
