import prompt


def welcome():
    print("Первая попытка запустить проект!")
    print()
    print("***")

    help_text = (
        "<command> exit - выйти из программы\n"
        "<command> help - справочная информация"
    )
    print(help_text)

    while True:
        command = prompt.string("Введите команду: ").strip()

        if command == "exit":
            break
        elif command == "help":
            print(help_text)
        else:
            print("Неизвестная команда. Введите help для справки.")
