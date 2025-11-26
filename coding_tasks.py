# coding_tasks.py - Модуль для генерации и проверки программных задач

import json
from openai import OpenAI
from dataclasses import dataclass
from typing import List, Dict, Any
import re

@dataclass
class TestCase:
    """Тест-кейс для проверки решения"""
    input_data: Any
    expected_output: Any
    description: str
    is_hidden: bool = False  # Скрытые тесты для защиты от читерства
    
    def to_dict(self):
        return {
            'input': self.input_data,
            'expected': self.expected_output,
            'description': self.description,
            'is_hidden': self.is_hidden
        }

@dataclass
class CodingTask:
    """Программная задача"""
    task_id: str
    title: str
    description: str
    difficulty: str  # easy, medium, hard
    language: str
    test_cases: List[TestCase]
    solution_template: str
    time_limit: int  # секунды
    memory_limit: int  # МБ
    hints: List[str]
    tags: List[str]
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'difficulty': self.difficulty,
            'language': self.language,
            'test_cases': [tc.to_dict() for tc in self.test_cases if not tc.is_hidden],
            'hidden_test_count': sum(1 for tc in self.test_cases if tc.is_hidden),
            'solution_template': self.solution_template,
            'time_limit': self.time_limit,
            'memory_limit': self.memory_limit,
            'hints': self.hints,
            'tags': self.tags
        }
    
    def get_all_tests(self):
        """Получить все тесты включая скрытые"""
        return [tc.to_dict() for tc in self.test_cases]

class CodingTaskGenerator:
    """Генератор программных задач через LLM"""
    
    def __init__(self, client: OpenAI):
        self.client = client
        self.position_topics = {
            'Frontend разработчик': [
                'работа с DOM элементами', 'обработка событий click/submit', 'валидация email/форм', 
                'фильтрация списков на странице', 'динамическое создание элементов', 'работа с localStorage',
                'асинхронные запросы fetch', 'обработка массивов данных', 'создание React компонентов',
                'работа с состоянием (state)', 'роутинг и навигация', 'оптимизация рендеринга'
            ],
            'Backend разработчик': [
                'обработка HTTP запросов', 'валидация входных данных', 'работа с базой данных', 
                'парсинг JSON/XML', 'алгоритмы поиска и сортировки', 'работа со словарями/хеш-таблицами',
                'обработка строк и регулярные выражения', 'создание REST API endpoints', 'аутентификация',
                'работа с файлами', 'обработка ошибок', 'кеширование данных'
            ],
            'Fullstack разработчик': [
                'интеграция frontend и backend', 'работа с API', 'преобразование данных между слоями',
                'валидация на клиенте и сервере', 'работа с JWT токенами', 'обработка форм',
                'real-time обновления (WebSocket)', 'оптимизация запросов', 'state management',
                'работа с базами данных', 'деплой и CI/CD', 'обработка файлов'
            ],
            'Data Scientist': [
                'статистический анализ данных', 'очистка и препроцессинг данных', 'работа с pandas DataFrame',
                'вычисление корреляций', 'группировка и агрегация', 'визуализация данных',
                'обработка временных рядов', 'работа с numpy массивами', 'нормализация данных',
                'обработка пропущенных значений', 'feature engineering', 'кросс-валидация'
            ],
            'QA Engineer': [
                'написание unit тестов', 'валидация граничных случаев', 'проверка входных данных',
                'тестирование API', 'автоматизация проверок', 'создание тест-кейсов',
                'проверка производительности', 'регрессионное тестирование', 'интеграционные тесты'
            ]
        }
        
    def get_difficulty_for_task_number(self, task_number: int, total_tasks: int, level: str) -> str:
        """Определяет сложность задачи на основе прогресса и уровня кандидата"""
        progress = task_number / total_tasks
        
        # Базовая сложность в зависимости от уровня кандидата
        if level == "Junior":
            # Junior: easy -> medium -> medium
            if progress <= 0.5:  # Первые 50% - легкие
                return 'easy'
            elif progress <= 0.8:  # 30% - средние
                return 'medium'
            else:  # Последние 20% - средние (не даем сложные джунам)
                return 'medium'
                
        elif level == "Middle":
            # Middle: easy -> medium -> hard
            if progress <= 0.3:  # Первые 30% - легкие
                return 'easy'
            elif progress <= 0.7:  # Средние 40% - средние
                return 'medium'
            else:  # Последние 30% - сложные
                return 'hard'
                
        elif level in ["Senior", "Team Lead"]:
            # Senior/Lead: medium -> hard -> hard
            if progress <= 0.3:  # Первые 30% - средние (не даем легкие сеньорам)
                return 'medium'
            elif progress <= 0.6:  # Средние 30% - сложные
                return 'hard'
            else:  # Последние 40% - очень сложные
                return 'hard'
        
        # Fallback: стандартная прогрессия
        if progress <= 0.3:
            return 'easy'
        elif progress <= 0.7:
            return 'medium'
        else:
            return 'hard'
    
    def get_topic_for_task(self, position: str, task_number: int) -> str:
        """Выбирает тематику для задачи по должности"""
        topics = self.position_topics.get(position, self.position_topics['Backend разработчик'])
        # Циклически перебираем темы, чтобы они не повторялись подряд
        return topics[task_number % len(topics)]
    
    def get_position_specific_context(self, position: str, language: str) -> dict:
        """Возвращает специфичный контекст для каждой должности"""
        contexts = {
            'Frontend разработчик': {
                'language': 'javascript',
                'focus': 'работа с DOM, браузерными API, React/Vue компонентами',
                'examples': 'манипуляция элементами страницы, обработка событий, валидация форм',
                'template': 'function solution() {\n    // Ваш код здесь\n}'
            },
            'Backend разработчик': {
                'language': 'python',
                'focus': 'обработка данных, работа с API, алгоритмы, базы данных',
                'examples': 'парсинг данных, фильтрация, агрегация, валидация',
                'template': 'def solution():\n    # Ваш код здесь\n    pass'
            },
            'Fullstack разработчик': {
                'language': language,
                'focus': 'работа с данными на фронте и бэке, интеграция API, обработка запросов',
                'examples': 'преобразование данных между frontend и backend, валидация',
                'template': 'def solution():\n    # Ваш код здесь\n    pass' if language == 'python' else 'function solution() {\n    // Ваш код\n}'
            },
            'Data Scientist': {
                'language': 'python',
                'focus': 'анализ данных, статистика, обработка массивов, математические вычисления',
                'examples': 'фильтрация данных, вычисление статистик, работа с numpy/pandas структурами',
                'template': 'def analyze_data(data):\n    # Ваш код здесь\n    pass'
            },
            'QA Engineer': {
                'language': 'python',
                'focus': 'тестирование, валидация данных, проверка граничных случаев',
                'examples': 'написание тестовых функций, проверка корректности данных',
                'template': 'def test_function():\n    # Ваш код здесь\n    pass'
            }
        }
        
        return contexts.get(position, contexts['Backend разработчик'])
        
    def generate_task(self, position: str, level: str, language: str = "python", 
                     task_number: int = 1, total_tasks: int = 10) -> CodingTask:
        """Генерирует задачу через LLM"""
        try:
            # Определяем сложность на основе прогресса И уровня кандидата
            difficulty = self.get_difficulty_for_task_number(task_number, total_tasks, level)
            # Определяем тематику на основе должности
            topic = self.get_topic_for_task(position, task_number)
            # Получаем специфичный контекст для должности
            context = self.get_position_specific_context(position, language)
            
            # Переопределяем язык если должность требует конкретный
            if position == 'Frontend разработчик':
                language = 'javascript'
            elif position in ['Backend разработчик', 'Data Scientist', 'QA Engineer']:
                language = 'python'
            
            difficulty_ru = {'easy': 'легкая', 'medium': 'средняя', 'hard': 'сложная'}[difficulty]
            
            prompt = f"""Создай СПЕЦИАЛИЗИРОВАННУЮ задачу для {position} {level}.
Язык: {language}
Сложность: {difficulty_ru}
Тематика: {topic}
Фокус: {context['focus']}

ВАЖНО: Задача должна быть релевантна именно для {position}!
Примеры задач: {context['examples']}

Задача #{task_number} из {total_tasks}.

ВЕРНИ СТРОГО ВАЛИДНЫЙ JSON БЕЗ КОММЕНТАРИЕВ:
{{
    "title": "Название задачи (релевантное для {position})",
    "description": "Описание с примером входа/выхода (контекст {position})",
    "difficulty": "{difficulty}",
    "test_cases": [
        {{"input": "test1", "expected": "result1", "description": "тест 1", "is_hidden": false}},
        {{"input": "test2", "expected": "result2", "description": "тест 2", "is_hidden": false}},
        {{"input": "test3", "expected": "result3", "description": "тест 3", "is_hidden": true}}
    ],
    "solution_template": "{context['template'].replace(chr(10), '\\n')}",
    "time_limit": 5,
    "memory_limit": 128,
    "hints": ["подсказка по {topic}"],
    "tags": ["{topic}"]
}}

ВАЖНО: Используй ТОЛЬКО двойные кавычки, без одинарных!"""
            
            messages = [
                {
                    "role": "system",
                    "content": f"Генератор задач для {position}. Создавай задачи специфичные для этой роли. СТРОГО: верни только валидный JSON. Используй ТОЛЬКО двойные кавычки."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = self.client.chat.completions.create(
                model="qwen3-coder-30b-a3b-instruct-fp8",  # Модель для кода
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            task_json = response.choices[0].message.content.strip()
            print(f"📝 Сырой ответ LLM: {task_json[:200]}...")
            
            task_json = self._clean_json_response(task_json)
            print(f"✨ Очищенный JSON: {task_json[:200]}...")
            
            task_data = json.loads(task_json)
            
            # Создаем объект задачи
            test_cases = [
                TestCase(
                    input_data=tc['input'],
                    expected_output=tc['expected'],
                    description=tc['description'],
                    is_hidden=tc.get('is_hidden', False)
                )
                for tc in task_data['test_cases']
            ]
            
            task = CodingTask(
                task_id=f"task_{position}_{level}_{language}_{task_number}_{difficulty}",
                title=task_data['title'],
                description=task_data['description'],
                difficulty=difficulty,
                language=language,
                test_cases=test_cases,
                solution_template=task_data.get('solution_template', ''),
                time_limit=task_data.get('time_limit', 5),
                memory_limit=task_data.get('memory_limit', 128),
                hints=task_data.get('hints', []),
                tags=task_data.get('tags', [])
            )
            
            return task
            
        except Exception as e:
            print(f"❌ Ошибка генерации задачи: {e}")
            print("🔄 Используем fallback задачу")
            return self._get_fallback_task(position, level, language)
    
    def _map_level_to_difficulty(self, level: str) -> str:
        """Маппинг уровня на сложность"""
        mapping = {
            "Junior": "easy",
            "Middle": "medium",
            "Senior": "hard",
            "Team Lead": "hard"
        }
        return mapping.get(level, "medium")
    
    def _clean_json_response(self, text: str) -> str:
        """Очистка JSON от markdown и лишних символов"""
        import re
        
        # Удаляем теги <think>...</think>
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        # Удаляем markdown блоки кода
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Удаляем все до первой {
        start = text.find('{')
        if start == -1:
            raise ValueError("Не найден JSON объект в ответе")
        
        # Находим последнюю закрывающую }
        end = text.rfind('}')
        if end == -1:
            raise ValueError("Не найдена закрывающая скобка JSON")
        
        # Вырезаем только JSON
        text = text[start:end+1]
        
        # Заменяем одинарные кавычки на двойные (если они используются для строк)
        # Осторожно: это может сломать валидный JSON с апострофами внутри строк
        # text = text.replace("'", '"')
        
        return text.strip()
    
    def _get_fallback_task(self, position: str, level: str, language: str) -> CodingTask:
        """Резервная задача если LLM недоступна"""
        
        if language.lower() == "python":
            if level == "Junior":
                return CodingTask(
                    task_id=f"fallback_python_junior",
                    title="Сумма чисел в списке",
                    description="""Напишите функцию sum_numbers(numbers), которая принимает список чисел и возвращает их сумму.

Пример:
sum_numbers([1, 2, 3, 4, 5]) -> 15
sum_numbers([]) -> 0
sum_numbers([-1, 1, -2, 2]) -> 0
""",
                    difficulty="easy",
                    language="python",
                    test_cases=[
                        TestCase([1, 2, 3, 4, 5], 15, "Простой случай", False),
                        TestCase([], 0, "Пустой список", False),
                        TestCase([-1, 1, -2, 2], 0, "Отрицательные числа", False),
                        TestCase([100], 100, "Один элемент", True),
                        TestCase([0, 0, 0], 0, "Нули", True),
                    ],
                    solution_template="""def sum_numbers(numbers):
    # Ваш код здесь
    pass
""",
                    time_limit=2,
                    memory_limit=64,
                    hints=["Используйте встроенную функцию sum()", "Рассмотрите краевые случаи"],
                    tags=["списки", "базовые операции"]
                )
            else:
                return CodingTask(
                    task_id=f"fallback_python_middle",
                    title="Поиск дубликатов в массиве",
                    description="""Напишите функцию find_duplicates(arr), которая находит все дубликаты в массиве.

Функция должна вернуть список уникальных дубликатов в порядке их первого появления.

Пример:
find_duplicates([1, 2, 3, 2, 4, 3]) -> [2, 3]
find_duplicates([1, 2, 3, 4, 5]) -> []
find_duplicates([1, 1, 1, 1]) -> [1]
""",
                    difficulty="medium",
                    language="python",
                    test_cases=[
                        TestCase([1, 2, 3, 2, 4, 3], [2, 3], "Несколько дубликатов", False),
                        TestCase([1, 2, 3, 4, 5], [], "Нет дубликатов", False),
                        TestCase([1, 1, 1, 1], [1], "Все одинаковые", False),
                        TestCase([], [], "Пустой массив", True),
                        TestCase([5, 4, 3, 2, 1, 2, 3, 4, 5], [5, 4, 3, 2], "Обратный порядок", True),
                    ],
                    solution_template="""def find_duplicates(arr):
    # Ваш код здесь
    pass
""",
                    time_limit=3,
                    memory_limit=128,
                    hints=["Используйте множества для отслеживания", "Сохраняйте порядок появления"],
                    tags=["массивы", "хэш-таблицы", "алгоритмы"]
                )
        
        # JavaScript fallback
        return CodingTask(
            task_id=f"fallback_js_basic",
            title="Проверка палиндрома",
            description="""Напишите функцию isPalindrome(str), которая проверяет, является ли строка палиндромом.

Пример:
isPalindrome("radar") -> true
isPalindrome("hello") -> false
isPalindrome("") -> true
""",
            difficulty="easy",
            language="javascript",
            test_cases=[
                TestCase("radar", True, "Палиндром", False),
                TestCase("hello", False, "Не палиндром", False),
                TestCase("", True, "Пустая строка", False),
                TestCase("a", True, "Один символ", True),
                TestCase("racecar", True, "Длинный палиндром", True),
            ],
            solution_template="""function isPalindrome(str) {
    // Ваш код здесь
}
""",
            time_limit=2,
            memory_limit=64,
            hints=["Сравните строку с её обратной версией", "Игнорируйте регистр"],
            tags=["строки", "алгоритмы"]
        )

# Предопределенные задачи для разных позиций и языков
PREDEFINED_TASKS = {
    "python": {
        "junior": [
            {
                "title": "Фибоначчи",
                "description": "Напишите функцию fibonacci(n), возвращающую n-ое число Фибоначчи",
                "test_cases": [
                    {"input": 0, "expected": 0, "description": "Первое число", "is_hidden": False},
                    {"input": 1, "expected": 1, "description": "Второе число", "is_hidden": False},
                    {"input": 10, "expected": 55, "description": "Десятое число", "is_hidden": False},
                    {"input": 15, "expected": 610, "description": "Пятнадцатое число", "is_hidden": True},
                ]
            }
        ],
        "middle": [
            {
                "title": "Сортировка слиянием",
                "description": "Реализуйте алгоритм сортировки слиянием",
                "test_cases": [
                    {"input": [3, 1, 4, 1, 5, 9, 2, 6], "expected": [1, 1, 2, 3, 4, 5, 6, 9], "description": "Обычный массив", "is_hidden": False},
                    {"input": [], "expected": [], "description": "Пустой массив", "is_hidden": False},
                    {"input": [1], "expected": [1], "description": "Один элемент", "is_hidden": True},
                ]
            }
        ]
    }
}
