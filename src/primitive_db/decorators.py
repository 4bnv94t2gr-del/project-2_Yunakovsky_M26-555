import time
from functools import wraps


def handle_db_errors(func):
    """Обрабатывает ошибки БД и возвращает None при сбое."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print(
                "Ошибка: Файл данных не найден. "
                "Возможно, база данных не инициализирована."
            )
        except KeyError as error:
            print(f"Ошибка: Таблица или столбец {error} не найден.")
        except ValueError as error:
            print(f"Ошибка валидации: {error}")
        except OSError as error:
            print(f"Ошибка работы с файлами: {error}")

        return None

    return wrapper


def confirm_action(action_name):
    """Создаёт декоратор подтверждения опасной операции."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                answer = input(
                    "Вы уверены, что хотите выполнить "
                    f'"{action_name}"? [y/n]: '
                )
            except (EOFError, KeyboardInterrupt):
                print("\nОперация отменена.")
                return None

            if answer.strip().lower() != "y":
                print("Операция отменена.")
                return None

            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_time(func):
    """Выводит время выполнения функции."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        started_at = time.monotonic()

        try:
            return func(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - started_at
            print(
                f"Функция {func.__name__} выполнилась "
                f"за {elapsed:.3f} секунд."
            )

    return wrapper


def create_cacher():
    """Создаёт кэш до 128 результатов в замыкании."""
    cache = {}
    max_size = 128

    def cache_result(key, value_func):
        if key not in cache:
            value = value_func()

            if len(cache) >= max_size:
                oldest_key = next(iter(cache))
                del cache[oldest_key]

            cache[key] = value

        return cache[key]

    return cache_result
