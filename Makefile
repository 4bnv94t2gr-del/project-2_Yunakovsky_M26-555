.PHONY: install run lint build

install:
	poetry install

run:
	poetry run database

lint:
	poetry run ruff check .

build:
	poetry build
