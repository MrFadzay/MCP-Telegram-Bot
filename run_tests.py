#!/usr/bin/env python3
"""
Скрипт для запуска тестов MCP Telegram Bot.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Запустить команду и показать результат."""
    print(f"\n🔄 {description}...")
    print(f"Команда: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - успешно")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - ошибка")
        if result.stderr:
            print("STDERR:", result.stderr)
        if result.stdout:
            print("STDOUT:", result.stdout)
    
    return result.returncode == 0


def main():
    """Основная функция."""
    print("🧪 Запуск тестов MCP Telegram Bot")
    
    # Проверяем, что мы в правильной директории
    if not Path("bot").exists():
        print("❌ Ошибка: Запустите скрипт из корневой директории проекта")
        sys.exit(1)
    
    # Проверяем наличие виртуального окружения
    if not os.environ.get('VIRTUAL_ENV'):
        print("⚠️  Предупреждение: Виртуальное окружение не активировано")
    
    success = True
    
    # Устанавливаем зависимости для разработки
    if not run_command([
        sys.executable, "-m", "pip", "install", "-r", "requirements-dev.txt"
    ], "Установка зависимостей для разработки"):
        success = False
    
    # Запускаем линтер
    if not run_command([
        sys.executable, "-m", "flake8", "bot", "tests", "--max-line-length=88", 
        "--ignore=E203,W503"
    ], "Проверка кода с flake8"):
        print("⚠️  Найдены проблемы со стилем кода")
    
    # Запускаем проверку типов
    if not run_command([
        sys.executable, "-m", "mypy", "bot", "--ignore-missing-imports"
    ], "Проверка типов с mypy"):
        print("⚠️  Найдены проблемы с типами")
    
    # Запускаем тесты
    if not run_command([
        sys.executable, "-m", "pytest", "-v", "--tb=short"
    ], "Запуск тестов"):
        success = False
    
    # Запускаем тесты с покрытием
    if not run_command([
        sys.executable, "-m", "pytest", "--cov=bot", "--cov-report=term-missing"
    ], "Запуск тестов с покрытием"):
        success = False
    
    if success:
        print("\n✅ Все тесты прошли успешно!")
        print("📊 Отчет о покрытии сохранен в htmlcov/index.html")
    else:
        print("\n❌ Некоторые тесты не прошли")
        sys.exit(1)


if __name__ == "__main__":
    main()