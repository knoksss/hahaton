from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from openai import OpenAI
import os
import json
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Конфигурация
class Config:
    # Настройки из документации SciBox
    LLM_BASE_URL = "https://llm.t1v.scibox.tech/v1"
    LLM_MODEL = "qwen3-32b-awq"
    LLM_TOKEN = "sk--hwyMZDmxjPMm50_5LXTiA"  # ⚠️ ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ ТОКЕН ⚠️
    
    # Параметры запроса
    TEMPERATURE = 0.7
    TOP_P = 0.9
    MAX_TOKENS = 1000
    
    # Настройки приложения
    INTERVIEW_DURATION = 30
    MAX_QUESTIONS = 5

app.config.from_object(Config)

# Инициализация OpenAI клиента
client = OpenAI(
    api_key="sk--hwyMZDmxjPMm50_5LXTiA",
    base_url=Config.LLM_BASE_URL
)

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
            'question_count': self.question_count
        }

# Хранилище сессий
interview_sessions = {}

# Доступные позиции и уровни
AVAILABLE_POSITIONS = {
    "Frontend разработчик": ["HTML/CSS", "JavaScript", "React", "Vue", "TypeScript", "Webpack"],
    "Backend разработчик": ["Python", "Java", "Node.js", "SQL", "Docker", "AWS"],
    "Data Scientist": ["Python", "Machine Learning", "SQL", "Statistics", "Deep Learning"],
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
        # Более простой и конкретный промпт
        prompt = f"""
Вопросы задавать на русском языке
ROLE: Technical interviewer for {session.position} {session.level} position
INTERVIEW TYPE: {session.interview_type}
COMPANY: {session.company_type}

PREVIOUS QUESTIONS: {session.questions_asked[-2:] if session.questions_asked else 'None'}

TASK: Generate exactly ONE technical interview question.

REQUIREMENTS:
- Must be a single question only
- Technical and relevant to {session.position}
- Appropriate for {session.level} level
- Different from previous questions
- Practical and skills-focused

FORMAT: Return ONLY the question text, nothing else.

QUESTION:
"""

        messages = [
            {
                "role": "system",
                "content": "You are a technical interviewer. Generate exactly one interview question. Return ONLY the question text without any additional text, explanations, or formatting."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        print(f"🎯 Generating question for {session.position} {session.level}")
        response = chat_with_model(messages)
        question = response.choices[0].message.content.strip()

        print(f"📨 Raw LLM response: '{question}'")

        # Улучшенная очистка ответа
        question = clean_llm_response(question)

        # Более строгая проверка пустого вопроса
        if not question or len(question.strip()) < 15 or not any(char.isalpha() for char in question):
            print("❌ LLM returned empty or invalid question, using fallback")
            return get_fallback_question(session)

        # Проверяем, что это действительно вопрос (содержит вопросительный знак или вопросное слово)
        question_words = ['как', 'что', 'почему', 'расскажите', 'объясните', 'how', 'what', 'why', 'explain']
        has_question_mark = '?' in question
        starts_with_question_word = any(question.lower().startswith(word) for word in question_words)

        if not (has_question_mark or starts_with_question_word):
            print("⚠️ LLM response doesn't look like a question, using fallback")
            return get_fallback_question(session)

        print(f"✅ Generated question: {question}")
        return question

    except Exception as e:
        print(f"❌ Error generating question with LLM: {e}")
        return get_fallback_question(session)


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
        if contains_code:
            prompt = f"""
            ВОПРОС: {question}
            КОД ({language}):
            {answer}

            Проанализируй код кандидата по критериям:
            1. Корректность решения
            2. Качество и читаемость кода
            3. Эффективность алгоритма
            4. Обработка edge cases
            5. Следование best practices

            ОЦЕНКА: от 1 до 10
            СИЛЬНЫЕ СТОРОНЫ: 2-3 пункта
            РЕКОМЕНДАЦИИ: 2-3 пункта

            Формат ответа:
            ОЦЕНКА: [число]/10
            СИЛЬНЫЕ СТОРОНЫ: [пункт1], [пункт2], [пункт3]
            РЕКОМЕНДАЦИИ: [пункт1], [пункт2], [пункт3]
            """
        else:
            prompt = f"""
            ВОПРОС: {question}
            ОТВЕТ: {answer}

            Проанализируй ответ кандидата по критериям:
            1. Техническая глубина и точность
            2. Практическая применимость знаний
            3. Структура и ясность изложения
            4. Соответствие уровню позиции {level}
            5. Наличие конкретных примеров

            ОЦЕНКА: от 1 до 10
            СИЛЬНЫЕ СТОРОНЫ: 2-3 пункта
            РЕКОМЕНДАЦИИ: 2-3 пункта

            Формат ответа:
            ОЦЕНКА: [число]/10
            СИЛЬНЫЕ СТОРОНЫ: [пункт1], [пункт2], [пункт3]
            РЕКОМЕНДАЦИИ: [пункт1], [пункт2], [пункт3]
            """

        messages = [
            {
                "role": "system",
                "content": """Ты строгий технический интервьюер. Анализируй ответы кандидатов и давай конструктивную обратную связь.

Всегда отвечай в строгом формате:
ОЦЕНКА: [число]/10
СИЛЬНЫЕ СТОРОНЫ: [пункт1], [пункт2], [пункт3]
РЕКОМЕНДАЦИИ: [пункт1], [пункт2], [пункт3]

Не добавляй никакого дополнительного текста."""
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

@app.route('/api/start_interview', methods=['POST'])
def start_interview():
    try:
        data = request.json
        position = data.get('position', 'Frontend разработчик')
        level = data.get('level', 'Middle')
        interview_type = data.get('interview_type', 'Техническое')
        company_type = data.get('company_type', 'IT продуктовая')
        
        # Генерация ID сессии
        session_id = f"session_{int(time.time())}_{len(interview_sessions)}"
        
        # Создание новой сессии
        session = InterviewSession(session_id, position, level, interview_type, company_type)
        interview_sessions[session_id] = session
        
        # Генерация первого вопроса через LLM
        print(f"🎯 Генерация первого вопроса для {position} {level}")
        first_question = generate_interview_question(session)
        session.current_question = first_question
        session.questions_asked.append(first_question)
        session.question_count += 1
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'question': first_question,
            'question_number': session.question_count,
            'total_questions': Config.MAX_QUESTIONS
        })
        
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
            'timestamp': datetime.now().isoformat()
        })
        
        # Проверка на завершение собеседования
        if session.question_count >= Config.MAX_QUESTIONS:
            session.is_active = False
            summary = generate_interview_summary(session)
            return jsonify({
                'success': True,
                'interview_complete': True,
                'evaluation': evaluation,
                'summary': summary
            })
        
        # Генерация следующего вопроса через LLM
        print("🔄 Генерация следующего вопроса...")
        next_question = generate_interview_question(session, session.user_answers)
        session.current_question = next_question
        session.questions_asked.append(next_question)
        session.question_count += 1
        
        return jsonify({
            'success': True,
            'interview_complete': False,
            'question': next_question,
            'question_number': session.question_count,
            'total_questions': Config.MAX_QUESTIONS,
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
                "content": "Ты опытный HR специалист и технический рекрутер. Ты анализируешь результаты собеседований и предоставляешь конструктивную обратную связь. Ты возвращаешь только валидный JSON."
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

if __name__ == '__main__':
    print("🚀 Запуск Interview AI с OpenAI клиентом")
    print(f"🔧 Конфигурация:")
    print(f"   Base URL: {Config.LLM_BASE_URL}")
    print(f"   Model: {Config.LLM_MODEL}")
    print(f"   Token: {'***' + Config.LLM_TOKEN[-4:] if Config.LLM_TOKEN else 'None'}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
