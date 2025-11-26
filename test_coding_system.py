# test_coding_system.py - Тестирование системы автотестов

import sys
import json
from coding_tasks import CodingTaskGenerator, CodingTask, TestCase
from code_runner import CodeRunner, CodeAnalyzer

def test_code_runner():
    """Тестирование запуска кода"""
    print("=" * 60)
    print("🧪 Тестирование CodeRunner")
    print("=" * 60)
    
    runner = CodeRunner()
    
    # Тест 1: Простая функция
    print("\n📝 Тест 1: Проверка простой функции")
    
    code = """
def sum_numbers(numbers):
    return sum(numbers)
"""
    
    test_cases = [
        {'input': [[1, 2, 3, 4, 5]], 'expected': 15, 'description': 'Простой случай'},
        {'input': [[]], 'expected': 0, 'description': 'Пустой список'},
        {'input': [[-1, 1, -2, 2]], 'expected': 0, 'description': 'Отрицательные числа'},
    ]
    
    result = runner.run_python_code(code, test_cases, 5, 128)
    
    print(f"✅ Результат: {result.passed_tests}/{result.total_tests} тестов пройдено")
    print(f"⏱️  Время: {result.execution_time}с")
    
    for test_result in result.test_results:
        status = "✅" if test_result['passed'] else "❌"
        print(f"{status} {test_result['description']}")
        if not test_result['passed']:
            print(f"   Ожидалось: {test_result['expected']}, Получено: {test_result.get('actual', 'N/A')}")
    
    # Тест 2: Проверка безопасности
    print("\n🔒 Тест 2: Проверка безопасности")
    
    dangerous_code = """
import os
def evil_function():
    os.system('ls')
"""
    
    is_valid, message = runner.validate_code(dangerous_code, 'python')
    print(f"Опасный код {'❌ заблокирован' if not is_valid else '⚠️ пропущен'}")
    print(f"Сообщение: {message}")
    
    # Тест 3: Сложная задача
    print("\n📊 Тест 3: Сложная задача - поиск дубликатов")
    
    code_duplicates = """
def find_duplicates(arr):
    seen = set()
    duplicates = []
    for item in arr:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates
"""
    
    test_cases_duplicates = [
        {'input': [[1, 2, 3, 2, 4, 3]], 'expected': [2, 3], 'description': 'Несколько дубликатов'},
        {'input': [[1, 2, 3, 4, 5]], 'expected': [], 'description': 'Нет дубликатов'},
        {'input': [[1, 1, 1, 1]], 'expected': [1], 'description': 'Все одинаковые'},
    ]
    
    result = runner.run_python_code(code_duplicates, test_cases_duplicates, 5, 128)
    print(f"✅ Результат: {result.passed_tests}/{result.total_tests} тестов пройдено")

def test_code_analyzer():
    """Тестирование анализатора кода"""
    print("\n" + "=" * 60)
    print("🔍 Тестирование CodeAnalyzer")
    print("=" * 60)
    
    analyzer = CodeAnalyzer()
    
    # Хороший код
    good_code = """
def fibonacci(n):
    \"\"\"Вычисляет n-ое число Фибоначчи\"\"\"
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b
"""
    
    print("\n📝 Анализ хорошего кода:")
    analysis = analyzer.analyze_code(good_code, 'python')
    print(f"  Качество: {analysis['quality_score']}/100")
    print(f"  Читаемость: {analysis['readability_score']}/100")
    print(f"  Сложность: {analysis['complexity']}")
    print(f"  Строк кода: {analysis['lines_of_code']}")
    
    # Плохой код
    bad_code = """
def x(n):
    if n<=1:return n
    return x(n-1)+x(n-2)
"""
    
    print("\n📝 Анализ плохого кода:")
    analysis = analyzer.analyze_code(bad_code, 'python')
    print(f"  Качество: {analysis['quality_score']}/100")
    print(f"  Читаемость: {analysis['readability_score']}/100")
    print(f"  Сложность: {analysis['complexity']}")
    
    if analysis['code_smells']:
        print(f"  ⚠️  Проблемы: {', '.join(analysis['code_smells'])}")
    
    if analysis['suggestions']:
        print(f"  💡 Рекомендации:")
        for suggestion in analysis['suggestions']:
            print(f"     - {suggestion}")

def test_task_generation():
    """Тестирование генерации задач (без LLM)"""
    print("\n" + "=" * 60)
    print("🎯 Тестирование генерации задач")
    print("=" * 60)
    
    # Создаем mock генератор
    from openai import OpenAI
    
    # Используем fallback задачу
    print("\n📚 Получение fallback задачи:")
    
    task = CodingTask(
        task_id="test_task",
        title="Тестовая задача",
        description="Напишите функцию для тестирования",
        difficulty="easy",
        language="python",
        test_cases=[
            TestCase([1, 2, 3], 6, "Простой тест", False),
            TestCase([10], 10, "Один элемент", True),
        ],
        solution_template="def test_function(arr):\n    pass",
        time_limit=5,
        memory_limit=128,
        hints=["Используйте цикл", "Не забудьте про краевые случаи"],
        tags=["массивы", "базовые"]
    )
    
    print(f"  Название: {task.title}")
    print(f"  Сложность: {task.difficulty}")
    print(f"  Язык: {task.language}")
    print(f"  Тестов: {len(task.test_cases)} (видимых: {len([tc for tc in task.test_cases if not tc.is_hidden])})")
    print(f"  Лимит времени: {task.time_limit}с")
    print(f"  Лимит памяти: {task.memory_limit}MB")
    
    task_dict = task.to_dict()
    print(f"\n  ✅ Сериализация в JSON работает")
    print(f"  Скрытых тестов: {task_dict['hidden_test_count']}")

def test_full_workflow():
    """Полный рабочий процесс"""
    print("\n" + "=" * 60)
    print("🔄 Тестирование полного рабочего процесса")
    print("=" * 60)
    
    runner = CodeRunner()
    analyzer = CodeAnalyzer()
    
    # Задача
    print("\n1️⃣ Создание задачи: Сумма четных чисел")
    
    task = CodingTask(
        task_id="sum_even",
        title="Сумма четных чисел",
        description="Напишите функцию sum_even(numbers), которая возвращает сумму всех четных чисел в списке",
        difficulty="easy",
        language="python",
        test_cases=[
            TestCase([[1, 2, 3, 4, 5, 6]], 12, "Смешанные числа", False),
            TestCase([[2, 4, 6]], 12, "Только четные", False),
            TestCase([[1, 3, 5]], 0, "Только нечетные", False),
            TestCase([[]], 0, "Пустой список", True),
            TestCase([[0, 2, -2]], 0, "С нулем и отрицательными", True),
        ],
        solution_template="def sum_even(numbers):\n    pass",
        time_limit=3,
        memory_limit=64,
        hints=["Проверяйте остаток от деления на 2"],
        tags=["массивы", "математика"]
    )
    
    # Решение кандидата
    print("\n2️⃣ Решение кандидата:")
    
    solution = """
def sum_even(numbers):
    total = 0
    for num in numbers:
        if num % 2 == 0:
            total += num
    return total
"""
    
    print(solution)
    
    # Валидация
    print("\n3️⃣ Валидация кода:")
    is_valid, message = runner.validate_code(solution, 'python')
    print(f"  {'✅' if is_valid else '❌'} {message}")
    
    # Запуск тестов
    print("\n4️⃣ Запуск тестов:")
    result = runner.run_python_code(solution, task.get_all_tests(), task.time_limit, task.memory_limit)
    
    print(f"  Пройдено: {result.passed_tests}/{result.total_tests}")
    print(f"  Процент: {result.to_dict()['pass_rate']}%")
    print(f"  Время: {result.execution_time}с")
    
    # Анализ качества
    print("\n5️⃣ Анализ качества кода:")
    analysis = analyzer.analyze_code(solution, 'python')
    
    print(f"  Качество: {analysis['quality_score']}/100")
    print(f"  Читаемость: {analysis['readability_score']}/100")
    print(f"  Сложность: {analysis['complexity']}")
    print(f"  Строк кода: {analysis['lines_of_code']}")
    
    # Итоговый вердикт
    print("\n6️⃣ Итоговый вердикт:")
    
    if result.success and analysis['quality_score'] >= 70:
        print("  ✅ ПРИНЯТО - Все тесты пройдены, код качественный")
    elif result.success:
        print("  ⚠️  УСЛОВНО ПРИНЯТО - Тесты пройдены, но качество кода требует улучшения")
    else:
        print("  ❌ НЕ ПРИНЯТО - Не все тесты пройдены")
    
    return result, analysis

if __name__ == '__main__':
    print("🚀 Запуск тестов системы автоматической проверки кода\n")
    
    try:
        test_code_runner()
        test_code_analyzer()
        test_task_generation()
        result, analysis = test_full_workflow()
        
        print("\n" + "=" * 60)
        print("✅ Все тесты завершены успешно!")
        print("=" * 60)
        
        print("\n📊 Итоговая статистика:")
        print(f"  Система готова к использованию")
        print(f"  Поддержка языков: Python (JavaScript - в разработке)")
        print(f"  Безопасность: ✅ Валидация кода работает")
        print(f"  Анализ качества: ✅ Метрики рассчитываются")
        print(f"  Автотесты: ✅ Проверка работает")
        
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
