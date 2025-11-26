from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from openai import OpenAI
import os
import json
import time
from datetime import datetime

# Импорт модулей для работы с задачами и тестированием
from coding_tasks import CodingTaskGenerator, CodingTask
from code_runner import CodeRunner, CodeAnalyzer

app = Flask(__name__)
CORS(app)

# Конфигурация
class Config:
    # Настройки из документации SciBox
    LLM_BASE_URL = "https://llm.t1v.scibox.tech/v1"
    LLM_MODEL = "qwen3-coder-30b-a3b-instruct-fp8"  # Специализированная модель для кода
    LLM_TOKEN = "sk--hwyMZDmxjPMm50_5LXTiA"  # ⚠️ ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ ТОКЕН ⚠️
    
    # Параметры запроса (оптимизированы для скорости)
    TEMPERATURE = 0.7
    TOP_P = 0.9
    MAX_TOKENS = 500  # Уменьшено с 1000 для ускорения
    
    # Настройки приложения
    INTERVIEW_DURATION = 30
    MAX_QUESTIONS = 0  # Теоретических вопросов (отключены)
    MAX_CODING_TASKS = 10  # Задач по программированию
    TOTAL_QUESTIONS = 10  # Всего заданий

app.config.from_object(Config)

# Инициализация OpenAI клиента
client = OpenAI(
    api_key="sk--hwyMZDmxjPMm50_5LXTiA",
    base_url=Config.LLM_BASE_URL
)

# Инициализация генератора задач и раннера кода
task_generator = CodingTaskGenerator(client)
code_runner = CodeRunner()
code_analyzer = CodeAnalyzer()

# Модель данных
class InterviewSession:
    def __init__(self, session_id, position, level, interview_type, company_type):
        self.session_id = session_id
        self.position = position
        self.level = level
        self.interview_type = interview_type
        self.company_type = company_type
        self.questions_asked = []
        self.user_answers = []
        self.current_question = None
        self.start_time = datetime.now()
        self.is_active = True
        self.question_count = 0
        self.coding_task_count = 0
        # Добавляем поля для задач программирования
        self.coding_tasks = []
        self.current_coding_task = None
        self.coding_submissions = []
        # Режим собеседования: 'mixed' - чередование вопросов и задач
        self.interview_mode = 'mixed'
        
    def to_dict(self):
        return {
            'session_id': self.session_id,
            'position': self.position,
            'level': self.level,
            'interview_type': self.interview_type,
            'company_type': self.company_type,
            'questions_asked': self.questions_asked,
            'user_answers': self.user_answers,
            'current_question': self.current_question,
            'start_time': self.start_time.isoformat(),
            'is_active': self.is_active,
            'question_count': self.question_count,
            'current_coding_task': self.current_coding_task.to_dict() if self.current_coding_task else None,
            'coding_submissions': self.coding_submissions
        }

# Хранилище сессий
interview_sessions = {}

# Доступные позиции и уровни
AVAILABLE_POSITIONS = {
    "Frontend разработчик": ["HTML/CSS", "JavaScript", "React", "Vue", "TypeScript", "Webpack"],
    "Backend разработчик": ["Python", "Java", "Node.js", "SQL", "Docker", "REST API"],
    "Fullstack разработчик": ["JavaScript", "Python", "React", "Node.js", "SQL", "Git"],
    "Data Scientist": ["Python", "Pandas", "NumPy", "Machine Learning", "SQL", "Statistics"],
    "QA Engineer": ["Тестирование", "Python", "Selenium", "API Testing", "Bug Tracking"],
    "DevOps инженер": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Networking"],
    "Mobile разработчик": ["Android", "iOS", "React Native", "Flutter", "Kotlin", "Swift"]
}

AVAILABLE_LEVELS = ["Junior", "Middle", "Senior", "Team Lead"]
AVAILABLE_INTERVIEW_TYPES = ["Техническое", "Поведенческое", "Системное проектирование", "Смешанное"]
AVAILABLE_COMPANY_TYPES = ["IT продуктовая", "Аутсорсинг", "Стартап", "Крупная корпорация", "Госучреждение"]

# Функция для общения с LLM через OpenAI клиент
def chat_with_model(messages, model=Config.LLM_MODEL):
    try:
        print(f"🔧 Отправка запроса к LLM через OpenAI клиент")
        print(f"   Model: {model}")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=Config.TEMPERATURE,
            top_p=Config.TOP_P,
            max_tokens=Config.MAX_TOKENS
        )

        print("✅ LLM ответ получен успешно")
        # Добавьте эту строку для отладки:
        debug_llm_response(response)

        return response

    except Exception as e:
        print(f"❌ Ошибка соединения с LLM: {e}")
        raise e

# Генерация вопросов через LLM
def generate_interview_question(session, previous_answers=None):
    try:
        # Промпт с assistant примером для исключения рассуждений
        messages = [
            {
                "role": "system",
                "content": "Ты технический интервьюер. Задавай вопросы кратко."
            },
            {
                "role": "user",
                "content": f"Задай технический вопрос для {session.position} {session.level}"
            },
            {
                "role": "assistant",
                "content": "Что такое"
            }
        ]

        print(f"🎯 Генерация вопроса для {session.position} {session.level}")
        response = chat_with_model(messages)
        question_part = response.choices[0].message.content.strip()

        # Собираем вопрос из префикса "Что такое" + ответ LLM
        question = "Что такое " + question_part
        
        print(f"📨 Ответ LLM: '{question}'")

        # Улучшенная очистка ответа
        question = clean_llm_response(question)
        
        # Если ответ слишком длинный (больше 200 символов) - рассуждения вслух
        if len(question) > 200:
            print("⚠️ LLM вернул слишком длинный ответ, используем fallback")
            return get_fallback_question(session)
        
        # Если ответ начинается с "Хорошо" или похожих слов - отбрасываем
        skip_words = ['хорошо', 'ок', 'okay', 'понял', 'мне нужно', 'давайте', 'я должен', 'i need', 'let me']
        question_lower = question.lower()
        for skip in skip_words:
            if question_lower.startswith(skip):
                print("⚠️ LLM начал рассуждать, используем fallback")
                return get_fallback_question(session)

        # Более строгая проверка пустого вопроса
        if not question or len(question.strip()) < 15 or not any(char.isalpha() for char in question):
            print("❌ LLM вернул пустой вопрос, используем fallback")
            return get_fallback_question(session)

        # Проверяем, что это действительно вопрос (содержит вопросительный знак или вопросное слово)
        question_words = ['как', 'что', 'почему', 'расскажите', 'объясните', 'опишите', 'приведите']
        has_question_mark = '?' in question
        starts_with_question_word = any(question.lower().startswith(word) for word in question_words)

        if not (has_question_mark or starts_with_question_word):
            print("⚠️ Ответ не похож на вопрос, используем fallback")
            return get_fallback_question(session)

        print(f"✅ Generated question: {question}")
        return question

    except Exception as e:
        print(f"❌ Error generating question with LLM: {e}")
        return get_fallback_question(session)


def remove_think_tags(text):
    """Удаляет теги <think> из ответа LLM"""
    import re
    # Удаляем все между <think> и </think>
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()

def clean_llm_response(text):
    """Очистка ответа от LLM от лишних форматирований"""
    if not text:
        return text

    # Удаляем кавычки в начале и конце
    text = text.strip('"\'').strip()

    # Удаляем маркеры кода и форматирования
    formatting_marks = ['```json', '```python', '```', 'QUESTION:', 'Вопрос:', 'Answer:', 'Ответ:']
    for mark in formatting_marks:
        text = text.replace(mark, '').strip()

    # Удаляем нумерацию в начале (1. 2. и т.д.)
    import re
    text = re.sub(r'^\d+[\.\)]\s*', '', text)

    # Берем первую строку если есть переносы (но сохраняем сложные вопросы)
    lines = text.split('\n')
    if len(lines) > 1:
        # Если первая строка достаточно длинная, используем только ее
        if len(lines[0].strip()) > 20:
            text = lines[0].strip()
        else:
            # Иначе объединяем первые две строки
            text = ' '.join(lines[:2]).strip()

    # Убедимся, что вопрос заканчивается знаком вопроса
    if text and not text.endswith('?') and len(text) > 10:
        text = text + '?'

    return text


def debug_llm_response(response):
    """Детальное логирование ответа LLM"""
    if not response or not hasattr(response, 'choices'):
        print("🔍 DEBUG: No response or invalid response object")
        return

    choice = response.choices[0]
    message = choice.message

    print(f"🔍 DEBUG LLM RESPONSE:")
    print(f"   Finish reason: {choice.finish_reason}")
    print(f"   Content: '{message.content}'")
    print(f"   Content length: {len(message.content)}")
    print(f"   Role: {message.role}")

    # Логируем все атрибуты сообщения
    for attr in dir(message):
        if not attr.startswith('_'):
            value = getattr(message, attr)
            if value and attr != 'content':
                print(f"   {attr}: {value}")

def get_fallback_question(session):
    """Fallback вопросы если LLM недоступна"""
    questions_pool = {
        "Frontend разработчик": {
            "Junior": [
                "Объясните, что такое DOM и как он работает?",
                "В чем разница между let, const и var?",
                "Что такое event delegation и зачем оно нужно?",
            ],
            "Middle": [
                "Расскажите о своем опыте работы с современными фреймворками JavaScript",
                "Как вы обеспечиваете производительность веб-приложений?",
                "Объясните разницу между React и Vue",
            ],
            "Senior": [
                "Опишите архитектуру крупного frontend приложения",
                "Как вы обеспечиваете масштабируемость и поддерживаемость кода?",
                "Расскажите о вашем опыте оптимизации загрузки приложений",
            ]
        },
        "Backend разработчик": {
            "Junior": [
                "Что такое REST API?",
                "Объясните основные принципы ООП",
                "Что такое SQL инъекции и как их предотвратить?",
            ],
            "Middle": [
                "Опишите ваш опыт работы с базами данных",
                "Как вы обеспечиваете безопасность API?",
                "Расскажите о вашем опыте работы с микросервисами",
            ],
            "Senior": [
                "Спроектируйте систему для обработки миллионов запросов",
                "Как вы обеспечиваете отказоустойчивость системы?",
                "Опишите ваш опыт работы с message brokers",
            ]
        }
    }
    
    position_questions = questions_pool.get(session.position, questions_pool["Frontend разработчик"])
    level_questions = position_questions.get(session.level, position_questions["Middle"])
    available_questions = [q for q in level_questions if q not in session.questions_asked]
    
    if available_questions:
        return available_questions[0]
    else:
        return f"Расскажите о самом сложном проекте на позиции {session.position}, с которым вы сталкивались?"

# Оценка ответов через LLM
def evaluate_answer(question, answer, position, level, contains_code=False, language=None):
    try:
        # Упрощенный промпт для ускорения
        if contains_code:
            prompt = f"""Оцени код кандидата по 10-балльной шкале.

Вопрос: {question}
Код: {answer[:500]}

Верни ТОЛЬКО в формате:
ОЦЕНКА: X/10
СИЛЬНЫЕ СТОРОНЫ: пункт1, пункт2
РЕКОМЕНДАЦИИ: пункт1, пункт2"""
        else:
            prompt = f"""Оцени ответ кандидата по 10-балльной шкале.

Вопрос: {question}
Ответ: {answer[:300]}
Уровень: {level}

Верни ТОЛЬКО в формате:
ОЦЕНКА: X/10
СИЛЬНЫЕ СТОРОНЫ: пункт1, пункт2
РЕКОМЕНДАЦИИ: пункт1, пункт2"""

        messages = [
            {
                "role": "system",
                "content": "Оценщик. Формат: ОЦЕНКА, СИЛЬНЫЕ СТОРОНЫ, РЕКОМЕНДАЦИИ."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        print(f"📊 Отправка запроса на оценку ответа")
        response = chat_with_model(messages)
        evaluation_text = response.choices[0].message.content.strip()

        print(f"📨 Получен ответ от LLM: {evaluation_text}")

        # Парсим текстовый ответ вместо JSON
        evaluation = parse_text_evaluation(evaluation_text, contains_code)

        print(f"✅ Оценка сформирована: {evaluation['score']}/10")
        return evaluation

    except Exception as e:
        print(f"❌ Ошибка оценки ответа: {e}")
        return get_fallback_evaluation(contains_code, 5)


def parse_text_evaluation(text, contains_code=False):
    """Парсит текстовый ответ от LLM в структурированную оценку"""
    try:
        # Инициализируем дефолтную оценку
        evaluation = {
            "score": 5,
            "feedback": "Ответ требует более детального анализа",
            "strengths": [],
            "improvements": []
        }

        if contains_code:
            evaluation["code_analysis"] = {
                "correctness": "Требует проверки",
                "readability": "Требует проверки",
                "efficiency": "Требует проверки",
                "best_practices": "Требует проверки"
            }

        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Парсим оценку
            if line.startswith('ОЦЕНКА:') or line.startswith('SCORE:'):
                try:
                    # Ищем число в строке
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = int(numbers[0])
                        evaluation["score"] = max(1, min(10, score))
                except:
                    pass

            # Парсим сильные стороны
            elif line.startswith('СИЛЬНЫЕ СТОРОНЫ:') or line.startswith('STRENGTHS:'):
                content = line.split(':', 1)[1].strip()
                strengths = [s.strip() for s in content.split(',') if s.strip()]
                evaluation["strengths"] = strengths[:3]  # Берем первые 3

            # Парсим рекомендации
            elif line.startswith('РЕКОМЕНДАЦИИ:') or line.startswith('IMPROVEMENTS:') or line.startswith(
                    'RECOMMENDATIONS:'):
                content = line.split(':', 1)[1].strip()
                improvements = [s.strip() for s in content.split(',') if s.strip()]
                evaluation["improvements"] = improvements[:3]  # Берем первые 3

        # Создаем фидбек на основе оценки
        if evaluation["score"] >= 8:
            evaluation["feedback"] = "Отличный ответ! Продемонстрированы глубокие знания и практический опыт."
        elif evaluation["score"] >= 6:
            evaluation["feedback"] = "Хороший ответ, но есть возможности для улучшения."
        else:
            evaluation["feedback"] = "Ответ требует более глубокого раскрытия темы и практических примеров."

        # Если не нашли сильных сторон/рекомендаций, добавляем дефолтные
        if not evaluation["strengths"]:
            evaluation["strengths"] = ["Базовое понимание темы", "Структурированный ответ"]

        if not evaluation["improvements"]:
            evaluation["improvements"] = ["Добавить больше технических деталей", "Привести практические примеры"]

        return evaluation

    except Exception as e:
        print(f"❌ Ошибка парсинга текстовой оценки: {e}")
        return get_fallback_evaluation(contains_code, 5)

def get_fallback_evaluation(contains_code=False, score=5):
    """Fallback оценка если LLM недоступна"""
    if contains_code:
        return {
            "score": score,
            "feedback": "Анализ кода временно недоступен. Требуется ручная проверка.",
            "strengths": ["Решение представлено"],
            "improvements": ["Требуется дополнительный анализ"],
            "code_analysis": {
                "correctness": "Не проверено",
                "readability": "Не проверено",
                "efficiency": "Не проверено", 
                "best_practices": "Не проверено"
            }
        }
    else:
        return {
            "score": score,
            "feedback": "Анализ ответа временно недоступен. Требуется ручная проверка.",
            "strengths": ["Ответ предоставлен"],
            "improvements": ["Требуется дополнительный анализ"]
        }

# Маршруты Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/setup')
def setup_interview():
    return render_template('setup.html', 
                         positions=AVAILABLE_POSITIONS,
                         levels=AVAILABLE_LEVELS,
                         interview_types=AVAILABLE_INTERVIEW_TYPES,
                         company_types=AVAILABLE_COMPANY_TYPES)

@app.route('/chat')
def chat():
    session_id = request.args.get('session_id')
    if not session_id or session_id not in interview_sessions:
        return redirect(url_for('setup_interview'))
    
    session = interview_sessions[session_id]
    return render_template('chat.html', session=session.to_dict())

@app.route('/coding')
def coding():
    session_id = request.args.get('session_id')
    if not session_id or session_id not in interview_sessions:
        return redirect(url_for('setup_interview'))
    
    session = interview_sessions[session_id]
    return render_template('coding.html', session=session.to_dict())

@app.route('/api/start_interview', methods=['POST'])
def start_interview():
    try:
        data = request.json
        position = data.get('position', 'Frontend разработчик')
        level = data.get('level', 'Middle')
        # Фиксированные значения
        interview_type = 'Техническое'
        company_type = 'IT продуктовая'
        
        # Генерация ID сессии
        session_id = f"session_{int(time.time())}_{len(interview_sessions)}"
        
        # Создание новой сессии
        session = InterviewSession(session_id, position, level, interview_type, company_type)
        interview_sessions[session_id] = session
        
        # Генерация первой задачи по программированию
        print(f"🎯 Генерация первой задачи для {position} {level}")
        try:
            coding_task = task_generator.generate_task(
                position, level, 'python',
                task_number=1, total_tasks=Config.TOTAL_QUESTIONS
            )
            session.current_coding_task = coding_task
            session.coding_tasks.append(coding_task)
            session.coding_task_count += 1
            
            response_data = {
                'success': True,
                'session_id': session_id,
                'next_type': 'coding_task',
                'task': coding_task.to_dict(),
                'question_number': 1,
                'total_questions': Config.TOTAL_QUESTIONS
            }
            print(f"✅ Отправка ответа: task_id={coding_task.task_id}, title={coding_task.title}")
            return jsonify(response_data)
        except Exception as e:
            print(f"❌ Ошибка генерации задачи: {e}")
            return jsonify({'success': False, 'error': f'Ошибка генерации задачи: {str(e)}'}), 500
        
    except Exception as e:
        print(f"❌ Ошибка запуска собеседования: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/submit_answer', methods=['POST'])
def submit_answer():
    try:
        data = request.json
        session_id = data.get('session_id')
        answer = data.get('answer', '')
        contains_code = data.get('contains_code', False)
        language = data.get('language', 'javascript')
        
        if session_id not in interview_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session = interview_sessions[session_id]
        
        if not session.is_active:
            return jsonify({'success': False, 'error': 'Interview completed'}), 400
        
        print(f"📝 Оценка ответа для вопроса: {session.current_question[:100]}...")
        print(f"📋 Тип ответа: {'код' if contains_code else 'текст'}")
        
        # Оценка ответа через LLM
        evaluation = evaluate_answer(
            session.current_question, 
            answer, 
            session.position, 
            session.level,
            contains_code,
            language
        )
        
        # Сохранение ответа
        session.user_answers.append({
            'question': session.current_question,
            'answer': answer,
            'evaluation': evaluation,
            'contains_code': contains_code,
            'language': language if contains_code else None,
            'timestamp': datetime.now().isoformat(),
            'type': 'theory'
        })
        
        session.question_count += 1
        total_items = session.question_count + session.coding_task_count
        
        # Проверка на завершение собеседования (5 вопросов + 5 задач = 10)
        if total_items >= Config.TOTAL_QUESTIONS:
            session.is_active = False
            summary = generate_interview_summary(session)
            return jsonify({
                'success': True,
                'interview_complete': True,
                'evaluation': evaluation,
                'summary': summary
            })
        
        # Определяем что давать дальше: вопрос или задачу
        # Чередуем: если вопросов < 5 и (задач >= вопросов), даем вопрос
        # иначе даем задачу
        should_give_question = (
            session.question_count < Config.MAX_QUESTIONS and 
            session.coding_task_count >= session.question_count
        )
        
        if should_give_question:
            # Генерация следующего вопроса через LLM
            print("🔄 Генерация следующего теоретического вопроса...")
            next_question = generate_interview_question(session, session.user_answers)
            session.current_question = next_question
            session.questions_asked.append(next_question)
            
            return jsonify({
                'success': True,
                'interview_complete': False,
                'next_type': 'question',
                'question': next_question,
                'question_number': total_items + 1,
                'total_questions': Config.TOTAL_QUESTIONS,
                'evaluation': evaluation
            })
        else:
            # Генерация задачи по программированию
            print("🔄 Генерация задачи по программированию...")
            try:
                coding_task = task_generator.generate_task(
                    session.position, 
                    session.level, 
                    'python'
                )
                session.current_coding_task = coding_task
                session.coding_tasks.append(coding_task)
                
                return jsonify({
                    'success': True,
                    'interview_complete': False,
                    'next_type': 'coding_task',
                    'task': coding_task.to_dict(),
                    'question_number': total_items + 1,
                    'total_questions': Config.TOTAL_QUESTIONS,
                    'evaluation': evaluation
                })
            except Exception as e:
                print(f"❌ Ошибка генерации задачи: {e}")
                # Если не удалось сгенерировать задачу, даем вопрос
                next_question = generate_interview_question(session, session.user_answers)
                session.current_question = next_question
                session.questions_asked.append(next_question)
                
                return jsonify({
                    'success': True,
                    'interview_complete': False,
                    'next_type': 'question',
                    'question': next_question,
                    'question_number': total_items + 1,
                    'total_questions': Config.TOTAL_QUESTIONS,
                    'evaluation': evaluation
                })
        
    except Exception as e:
        print(f"❌ Ошибка отправки ответа: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_llm', methods=['POST'])
def test_llm():
    """Тестирование подключения к LLM"""
    try:
        test_data = request.json or {}
        message = test_data.get('message', 'Привет! Ответь коротко - ты работаешь?')
        
        messages = [{"role": "user", "content": message}]
        
        print(f"🧪 Тестирование LLM с сообщением: {message}")
        response = chat_with_model(messages)
        answer = response.choices[0].message.content
        
        return jsonify({
            'success': True,
            'request': message,
            'response': answer,
            'model': Config.LLM_MODEL,
            'base_url': Config.LLM_BASE_URL
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'model': Config.LLM_MODEL,
            'base_url': Config.LLM_BASE_URL
        }), 500

@app.route('/api/test_stream', methods=['POST'])
def test_stream():
    """Тестирование потокового ответа"""
    try:
        test_data = request.json or {}
        message = test_data.get('message', 'Расскажи о себе кратко')
        
        def generate():
            try:
                stream = client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{"role": "user", "content": message}],
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        yield f"data: {chunk.choices[0].delta.content}\n\n"
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                yield f"data: ❌ Ошибка: {str(e)}\n\n"
        
        return app.response_class(generate(), mimetype='text/plain')
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test')
def test_llm_page():
    return render_template('test_llm.html')

def generate_interview_summary(session):
    """Генерация итогов собеседования через LLM"""
    try:
        answers_text = "\n".join([
            f"Вопрос {i+1}: {qa['question']}\nОтвет: {qa['answer'][:150]}...\nОценка: {qa['evaluation']['score']}/10"
            for i, qa in enumerate(session.user_answers)
        ])
        
        prompt = f"""
        Проанализируй результаты технического собеседования и предоставь итоговую обратную связь.

        ДОЛЖНОСТЬ: {session.position}
        УРОВЕНЬ: {session.level}
        ТИП КОМПАНИИ: {session.company_type}
        ВСЕГО ВОПРОСОВ: {len(session.user_answers)}

        ОТВЕТЫ КАНДИДАТА:
        {answers_text}

        Проанализируй общую картину и предоставь развернутую обратную связь в JSON формате:
        {{
            "final_score": "средний балл/10 с комментарием",
            "summary": "общая оценка кандидата (2-3 предложения)",
            "strengths": ["основные сильные стороны (3-4 пункта)", ...],
            "improvements": ["ключевые области для улучшения (3-4 пункта)", ...], 
            "recommendations": ["рекомендации по развитию (2-3 пункта)", ...],
            "verdict": "рекомендация к найму (Рекомендуем к найму/Рассмотреть кандидата/Не рекомендовать)"
        }}
        """

        messages = [
            {
                "role": "system",
                "content": "HR аналитик. Верни ТОЛЬКО валидный JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = chat_with_model(messages)
        summary_text = response.choices[0].message.content.strip()
        summary_text = clean_llm_response(summary_text)
        llm_summary = json.loads(summary_text)
        
        # Объединяем с базовой информацией
        final_score = calculate_final_score(session)
        summary = {
            'position': session.position,
            'level': session.level,
            'interview_type': session.interview_type,
            'company_type': session.company_type,
            'total_questions': session.question_count,
            'final_score': final_score,
            'duration_minutes': round((datetime.now() - session.start_time).total_seconds() / 60, 1),
            'strengths': llm_summary.get('strengths', []),
            'improvements': llm_summary.get('improvements', []),
            'recommendations': llm_summary.get('recommendations', []),
            'verdict': llm_summary.get('verdict', 'Рассмотреть кандидата'),
            'summary_text': llm_summary.get('summary', f'Кандидат набрал {final_score}/10 баллов.')
        }
        
        return summary
        
    except Exception as e:
        print(f"❌ Ошибка генерации summary с LLM: {e}")
        return generate_basic_summary(session)

def generate_basic_summary(session):
    """Базовый summary если LLM недоступна"""
    total_score = calculate_final_score(session)
    
    if total_score >= 8:
        verdict = "Рекомендуем к найму"
        recommendations = ["Отличные технические навыки", "Подходит для позиции", "Быстрое обучение"]
    elif total_score >= 6:
        verdict = "Рассмотреть кандидата" 
        recommendations = ["Хорошая техническая база", "Требуется менторство", "Потенциал для роста"]
    else:
        verdict = "Не рекомендовать"
        recommendations = ["Требуется серьезное обучение", "Рассмотреть через 6-12 месяцев", "Улучшить базовые навыки"]
    
    return {
        'position': session.position,
        'level': session.level,
        'total_questions': session.question_count,
        'final_score': total_score,
        'duration_minutes': round((datetime.now() - session.start_time).total_seconds() / 60, 1),
        'strengths': ["Технические знания", "Опыт работы", "Мотивация"],
        'improvements': ["Углубить практический опыт", "Улучшить навыки решения задач", "Изучить дополнительные технологии"],
        'recommendations': recommendations,
        'verdict': verdict,
        'summary_text': f'Кандидат показал результат {total_score}/10 баллов на техническом собеседовании.'
    }

def calculate_final_score(session):
    """Расчет итогового балла"""
    if not session.user_answers:
        return 0
    
    total_score = sum(answer['evaluation'].get('score', 0) for answer in session.user_answers)
    return round(total_score / len(session.user_answers), 1)

# ========== API endpoints для задач программирования ==========

@app.route('/api/generate_coding_task', methods=['POST'])
def generate_coding_task():
    """Генерация новой задачи по программированию"""
    try:
        data = request.json
        session_id = data.get('session_id')
        language = data.get('language', 'python')
        
        if session_id not in interview_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session = interview_sessions[session_id]
        
        print(f"🎯 Генерация задачи для {session.position} {session.level} на {language}")
        
        # Генерируем задачу через LLM
        task = task_generator.generate_task(session.position, session.level, language)
        
        # Сохраняем задачу в сессии
        session.current_coding_task = task
        session.coding_tasks.append(task)
        
        return jsonify({
            'success': True,
            'task': task.to_dict()
        })
        
    except Exception as e:
        print(f"❌ Ошибка генерации задачи: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/submit_code', methods=['POST'])
def submit_code():
    """Отправка кода на проверку и продолжение собеседования"""
    try:
        data = request.json
        session_id = data.get('session_id')
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        if session_id not in interview_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session = interview_sessions[session_id]
        
        if not session.current_coding_task:
            return jsonify({'success': False, 'error': 'No active coding task'}), 400
        
        print(f"📝 Проверка кода для задачи: {session.current_coding_task.title}")
        
        # Получаем все тесты (включая скрытые)
        all_tests = session.current_coding_task.get_all_tests()
        
        # Запускаем код с тестами
        if language.lower() == 'python':
            result = code_runner.run_python_code(
                code, 
                all_tests,
                session.current_coding_task.time_limit,
                session.current_coding_task.memory_limit
            )
        else:
            result = code_runner.run_javascript_code(code, all_tests)
        
        # Анализ качества кода
        code_quality = code_analyzer.analyze_code(code, language)
        
        # Сохраняем результат
        submission = {
            'task_id': session.current_coding_task.task_id,
            'task_title': session.current_coding_task.title,
            'task': session.current_coding_task.description,
            'code': code,
            'language': language,
            'result': result.to_dict(),
            'code_quality': code_quality,
            'timestamp': datetime.now().isoformat(),
            'passed': result.success,
            'type': 'coding',
            'evaluation': {
                'score': calculate_code_score(result, code_quality),
                'feedback': f"Тесты: {result.passed_tests}/{result.total_tests}, Качество: {code_quality['quality_score']}/100"
            }
        }
        
        session.coding_submissions.append(submission)
        session.user_answers.append(submission)  # Добавляем в общий список
        session.coding_task_count += 1
        session.current_coding_task = None  # Очищаем текущую задачу
        
        total_items = session.question_count + session.coding_task_count
        
        print(f"✅ Тесты пройдено: {result.passed_tests}/{result.total_tests}")
        print(f"📊 Качество кода: {code_quality['quality_score']}/100")
        print(f"📈 Прогресс: {total_items}/{Config.TOTAL_QUESTIONS}")
        
        # Проверка на завершение (5+5=10)
        if total_items >= Config.TOTAL_QUESTIONS:
            session.is_active = False
            summary = generate_interview_summary(session)
            return jsonify({
                'success': True,
                'test_results': result.to_dict(),
                'code_quality': code_quality,
                'interview_complete': True,
                'summary': summary
            })
        
        # Генерация следующей задачи (только задачи программирования)
        next_task_number = total_items + 1
        print(f"🔄 Генерация задачи #{next_task_number}/{Config.TOTAL_QUESTIONS}...")
        try:
            coding_task = task_generator.generate_task(
                session.position, 
                session.level, 
                language,
                task_number=next_task_number,
                total_tasks=Config.TOTAL_QUESTIONS
            )
            session.current_coding_task = coding_task
            session.coding_tasks.append(coding_task)
            
            return jsonify({
                'success': True,
                'test_results': result.to_dict(),
                'code_quality': code_quality,
                'interview_complete': False,
                'next_type': 'coding_task',
                'task': coding_task.to_dict(),
                'question_number': total_items + 1,
                'total_questions': Config.TOTAL_QUESTIONS
            })
        except Exception as e:
            print(f"❌ Ошибка генерации задачи: {e}")
            return jsonify({
                'success': False,
                'error': f'Ошибка генерации задачи: {str(e)}'
            }), 500
        
    except Exception as e:
        print(f"❌ Ошибка проверки кода: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_code_score(result, code_quality):
    """Расчет оценки за задачу по программированию"""
    # 60% за прохождение тестов, 40% за качество кода
    test_score = (result.passed_tests / result.total_tests) * 6
    quality_score = (code_quality['quality_score'] / 100) * 4
    return round(test_score + quality_score, 1)

@app.route('/api/get_coding_task', methods=['GET'])
def get_coding_task():
    """Получение текущей задачи"""
    try:
        session_id = request.args.get('session_id')
        
        if session_id not in interview_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session = interview_sessions[session_id]
        
        if not session.current_coding_task:
            return jsonify({'success': False, 'error': 'No active task'}), 404
        
        return jsonify({
            'success': True,
            'task': session.current_coding_task.to_dict()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_submissions', methods=['GET'])
def get_submissions():
    """Получение всех попыток решения"""
    try:
        session_id = request.args.get('session_id')
        
        if session_id not in interview_sessions:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        session = interview_sessions[session_id]
        
        return jsonify({
            'success': True,
            'submissions': session.coding_submissions,
            'total_submissions': len(session.coding_submissions)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/validate_code', methods=['POST'])
def validate_code():
    """Валидация кода без запуска"""
    try:
        data = request.json
        code = data.get('code', '')
        language = data.get('language', 'python')
        
        is_valid, message = code_runner.validate_code(code, language)
        
        if is_valid:
            # Дополнительный анализ
            analysis = code_analyzer.analyze_code(code, language)
            
            return jsonify({
                'success': True,
                'valid': True,
                'message': 'Код прошел валидацию',
                'analysis': analysis
            })
        else:
            return jsonify({
                'success': True,
                'valid': False,
                'message': message
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск Interview AI с OpenAI клиентом")
    print(f"🔧 Конфигурация:")
    print(f"   Base URL: {Config.LLM_BASE_URL}")
    print(f"   Model: {Config.LLM_MODEL}")
    print(f"   Token: {'***' + Config.LLM_TOKEN[-4:] if Config.LLM_TOKEN else 'None'}")
    print(f"✅ Модули задач и тестирования загружены")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
