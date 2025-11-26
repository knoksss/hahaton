# code_runner.py - Безопасное выполнение кода с проверкой тестов

import sys
import io
import time
import traceback
import json
import signal
from contextlib import contextmanager
from typing import Dict, Any, List
import ast
import re

# resource доступен только на Unix
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

class TimeoutException(Exception):
    """Исключение при превышении времени выполнения"""
    pass

class MemoryLimitException(Exception):
    """Исключение при превышении лимита памяти"""
    pass

class CodeExecutionResult:
    """Результат выполнения кода"""
    def __init__(self):
        self.success = False
        self.output = ""
        self.error = ""
        self.execution_time = 0
        self.memory_used = 0
        self.test_results = []
        self.passed_tests = 0
        self.total_tests = 0
        
    def to_dict(self):
        return {
            'success': self.success,
            'output': self.output,
            'error': self.error,
            'execution_time': round(self.execution_time, 3),
            'memory_used': self.memory_used,
            'test_results': self.test_results,
            'passed_tests': self.passed_tests,
            'total_tests': self.total_tests,
            'pass_rate': round(self.passed_tests / self.total_tests * 100, 1) if self.total_tests > 0 else 0
        }

class TestResult:
    """Результат одного теста"""
    def __init__(self, test_case, passed, actual_output=None, error=None):
        self.test_case = test_case
        self.passed = passed
        self.actual_output = actual_output
        self.error = error
        
    def to_dict(self):
        result = {
            'description': self.test_case.get('description', 'Test'),
            'passed': self.passed,
            'input': str(self.test_case.get('input')),
            'expected': str(self.test_case.get('expected')),
        }
        
        if self.actual_output is not None:
            result['actual'] = str(self.actual_output)
        if self.error:
            result['error'] = self.error
            
        return result

@contextmanager
def time_limit(seconds):
    """Контекстный менеджер для ограничения времени выполнения"""
    def signal_handler(signum, frame):
        raise TimeoutException(f"Превышено время выполнения ({seconds}с)")
    
    # Устанавливаем обработчик только на Unix-подобных системах
    if hasattr(signal, 'SIGALRM'):
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
    else:
        # На Windows используем простой таймаут без сигналов
        yield

@contextmanager
def memory_limit(max_memory_mb):
    """Контекстный менеджер для ограничения памяти (только Unix)"""
    if HAS_RESOURCE and hasattr(resource, 'RLIMIT_AS'):
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_mb * 1024 * 1024, hard))
        try:
            yield
        finally:
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
    else:
        # На Windows просто пропускаем ограничение памяти
        yield

class CodeRunner:
    """Безопасный запуск кода с проверкой тестов"""
    
    def __init__(self):
        self.forbidden_imports = [
            'os', 'sys', 'subprocess', 'eval', 'exec', 
            '__import__', 'open', 'file', 'input',
            'compile', 'execfile', 'reload'
        ]
        
    def validate_code(self, code: str, language: str) -> tuple[bool, str]:
        """Проверка кода на безопасность"""
        
        if language.lower() == 'python':
            # Проверка на запрещенные импорты
            for forbidden in self.forbidden_imports:
                if re.search(r'\b' + forbidden + r'\b', code):
                    return False, f"Запрещено использование '{forbidden}'"
            
            # Проверка на опасные операции
            dangerous_patterns = [
                r'__.*__',  # dunder методы (кроме основных)
                r'eval\s*\(',
                r'exec\s*\(',
                r'compile\s*\(',
                r'globals\s*\(',
                r'locals\s*\(',
                r'vars\s*\(',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, code):
                    return False, f"Обнаружен потенциально опасный код: {pattern}"
            
            # Проверка синтаксиса Python
            try:
                ast.parse(code)
            except SyntaxError as e:
                return False, f"Синтаксическая ошибка: {str(e)}"
                
        return True, "OK"
    
    def run_python_code(self, code: str, test_cases: List[Dict], 
                       time_limit_sec: int = 5, 
                       memory_limit_mb: int = 128) -> CodeExecutionResult:
        """Выполнение Python кода с тестами"""
        
        result = CodeExecutionResult()
        result.total_tests = len(test_cases)
        
        # Валидация кода
        is_valid, validation_error = self.validate_code(code, 'python')
        if not is_valid:
            result.error = validation_error
            return result
        
        # Извлечение имени функции из кода
        function_name = self._extract_function_name(code)
        if not function_name:
            result.error = "Не найдена функция для тестирования"
            return result
        
        # Выполнение тестов
        for test_case in test_cases:
            try:
                test_result = self._run_single_test(
                    code, 
                    function_name, 
                    test_case,
                    time_limit_sec,
                    memory_limit_mb
                )
                
                result.test_results.append(test_result.to_dict())
                if test_result.passed:
                    result.passed_tests += 1
                    
            except Exception as e:
                test_result = TestResult(
                    test_case,
                    False,
                    error=f"Ошибка выполнения теста: {str(e)}"
                )
                result.test_results.append(test_result.to_dict())
        
        result.success = result.passed_tests == result.total_tests
        
        return result
    
    def _extract_function_name(self, code: str) -> str:
        """Извлечение имени функции из кода"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    return node.name
        except:
            pass
        return None
    
    def _run_single_test(self, code: str, function_name: str, 
                        test_case: Dict, time_limit_sec: int,
                        memory_limit_mb: int) -> TestResult:
        """Выполнение одного теста"""
        
        start_time = time.time()
        
        try:
            # Создаем безопасное окружение для выполнения
            safe_globals = {
                '__builtins__': {
                    'range': range,
                    'len': len,
                    'str': str,
                    'int': int,
                    'float': float,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'tuple': tuple,
                    'bool': bool,
                    'abs': abs,
                    'max': max,
                    'min': min,
                    'sum': sum,
                    'sorted': sorted,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'print': print,
                    'True': True,
                    'False': False,
                    'None': None,
                }
            }
            
            # Выполняем код пользователя
            exec(code, safe_globals)
            
            # Получаем функцию
            user_function = safe_globals.get(function_name)
            if not user_function:
                return TestResult(
                    test_case,
                    False,
                    error=f"Функция '{function_name}' не найдена"
                )
            
            # Подготавливаем входные данные
            test_input = test_case['input']
            expected_output = test_case['expected']
            
            # Запускаем с ограничениями
            try:
                with time_limit(time_limit_sec):
                    # Вызываем функцию с тестовыми данными
                    # Если input - это список с одним элементом (аргументы функции), распаковываем
                    if isinstance(test_input, list) and len(test_input) == 1:
                        actual_output = user_function(test_input[0])
                    elif isinstance(test_input, list) and len(test_input) > 1:
                        actual_output = user_function(*test_input)
                    else:
                        actual_output = user_function(test_input)
                    
                    # Сравниваем результат
                    passed = self._compare_outputs(actual_output, expected_output)
                    
                    return TestResult(
                        test_case,
                        passed,
                        actual_output=actual_output
                    )
                    
            except TimeoutException as e:
                return TestResult(
                    test_case,
                    False,
                    error=str(e)
                )
            except RecursionError:
                return TestResult(
                    test_case,
                    False,
                    error="Превышена максимальная глубина рекурсии"
                )
                
        except Exception as e:
            return TestResult(
                test_case,
                False,
                error=f"Ошибка выполнения: {str(e)}"
            )
    
    def _compare_outputs(self, actual, expected) -> bool:
        """Сравнение фактического и ожидаемого результатов"""
        
        # Прямое сравнение
        if actual == expected:
            return True
        
        # Сравнение с преобразованием типов
        try:
            # Для чисел допускаем небольшую погрешность
            if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
                return abs(actual - expected) < 1e-9
            
            # Для списков/множеств сравниваем содержимое
            if isinstance(actual, (list, set, tuple)) and isinstance(expected, (list, set, tuple)):
                return sorted(list(actual)) == sorted(list(expected))
            
            # Строковое сравнение
            return str(actual).strip() == str(expected).strip()
            
        except:
            return False
    
    def run_javascript_code(self, code: str, test_cases: List[Dict]) -> CodeExecutionResult:
        """Заглушка для JavaScript (требует Node.js)"""
        result = CodeExecutionResult()
        result.error = "JavaScript выполнение пока не поддерживается. Используйте Python."
        result.total_tests = len(test_cases)
        return result

class CodeAnalyzer:
    """Анализатор качества кода"""
    
    def analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """Комплексный анализ кода"""
        
        analysis = {
            'lines_of_code': 0,
            'complexity': 0,
            'code_smells': [],
            'quality_score': 0,
            'readability_score': 0,
            'suggestions': []
        }
        
        if language.lower() == 'python':
            analysis = self._analyze_python_code(code)
        
        return analysis
    
    def _analyze_python_code(self, code: str) -> Dict[str, Any]:
        """Анализ Python кода"""
        
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        
        analysis = {
            'lines_of_code': len(non_empty_lines),
            'total_lines': len(lines),
            'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
            'complexity': self._calculate_cyclomatic_complexity(code),
            'code_smells': [],
            'quality_score': 70,  # Базовый скор
            'readability_score': 70,
            'suggestions': []
        }
        
        # Проверки качества
        if analysis['lines_of_code'] == 0:
            analysis['code_smells'].append("Пустой код")
            analysis['quality_score'] = 0
            return analysis
        
        # Проверка на комментарии
        comment_ratio = analysis['comment_lines'] / analysis['total_lines']
        if comment_ratio < 0.1 and analysis['total_lines'] > 10:
            analysis['suggestions'].append("Добавьте комментарии для улучшения читаемости")
            analysis['readability_score'] -= 10
        
        # Проверка длины строк
        long_lines = [i for i, line in enumerate(lines, 1) if len(line) > 100]
        if long_lines:
            analysis['code_smells'].append(f"Слишком длинные строки: {len(long_lines)}")
            analysis['readability_score'] -= 5
        
        # Проверка сложности
        if analysis['complexity'] > 10:
            analysis['code_smells'].append("Высокая цикломатическая сложность")
            analysis['suggestions'].append("Разбейте функцию на более мелкие части")
            analysis['quality_score'] -= 15
        elif analysis['complexity'] > 5:
            analysis['quality_score'] -= 5
        
        # Проверка именования
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.name) < 3:
                        analysis['suggestions'].append(f"Используйте более описательные имена функций")
                        analysis['readability_score'] -= 5
                        break
        except:
            pass
        
        # Итоговый скор
        analysis['quality_score'] = max(0, min(100, analysis['quality_score']))
        analysis['readability_score'] = max(0, min(100, analysis['readability_score']))
        
        return analysis
    
    def _calculate_cyclomatic_complexity(self, code: str) -> int:
        """Упрощенный расчет цикломатической сложности"""
        try:
            tree = ast.parse(code)
            complexity = 1  # Базовая сложность
            
            for node in ast.walk(tree):
                # Увеличиваем сложность за условия и циклы
                if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
                    
            return complexity
        except:
            return 1
