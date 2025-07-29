# Makefile для MCP Telegram Bot

.PHONY: help install install-dev test lint format clean reset-db run

help:  ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Установить зависимости
	pip install -r requirements.txt

install-dev:  ## Установить зависимости для разработки
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

test:  ## Запустить тесты
	python run_tests.py

test-quick:  ## Запустить только юнит-тесты
	pytest tests/ -v --tb=short -m "not slow"

test-coverage:  ## Запустить тесты с покрытием
	pytest --cov=bot --cov-report=html --cov-report=term-missing

lint:  ## Проверить код линтерами
	flake8 bot tests --max-line-length=88 --ignore=E203,W503
	mypy bot --ignore-missing-imports

format:  ## Отформатировать код
	black bot tests
	isort bot tests

clean:  ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

reset-db:  ## Сбросить базу данных (УДАЛЯЕТ ВСЕ ДАННЫЕ!)
	python reset_db.py

run:  ## Запустить бота
	python main.py

setup:  ## Первоначальная настройка проекта
	python -m venv venv
	@echo "Активируйте виртуальное окружение:"
	@echo "Windows: .\\venv\\Scripts\\activate"
	@echo "Linux/Mac: source venv/bin/activate"
	@echo "Затем выполните: make install-dev"