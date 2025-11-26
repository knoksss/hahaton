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
    LLM_TOKEN = "sk-1234"  # ⚠️ ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ ТОКЕН ⚠️
    
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
        print(f"   Messages: {len(messages)}")
        
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=Config.TEMPERATURE,
            top_p=Config.TOP_P,
            max_tokens=Config.MAX_TOKENS
        )
        
        print("✅ LLM ответ получен успешно")
        return response
        
    except Exception as e:
        print(f"❌ Ошибка соединения с LLM: {e}")
        raise e

# Генерация вопросов через LLM
def generate_interview_question(session, previous_answers=None):
    try:
        prompt = f"""
        Ты - профессиональный технический интервьюер на позицию {session.position} уровня {session.level}.
        Тип собеседования: {session.interview_type}
        Тип компании: {session.company_type}
        
        Уже заданные вопросы: {session.questions_asked[-3:] if session.questions_asked else 'Нет'}
        
        Сгенерируй ОДИН релевантный технический вопрос для собеседования.
        Вопрос должен быть:
        - Конкретным и техническим
        - Соответствовать уровню позиции {session.level}
        - Не повторять предыдущие вопросы
        - Помочь оценить реальные навыки кандидата
        
        Верни ТОЛЬКО текст вопроса без дополнительных комментариев.
        """
        
        messages = [
            {
                "role": "system", 
                "content": "Ты опытный технический интервьюер. Генерируй только вопросы без дополнительного текста."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = chat_with_model(messages)
        question = response.choices[0].message.content.strip()
        
        # Очистка ответа от возможных мета-комментариев
        question = clean_llm_response(question)
            
        # Если LLM вернула пустой вопрос, используем fallback
        if not question or len(question) < 10:
            print("LLM вернула пустой вопрос, использую fallback")
            return get_fallback_question(session)
            
        print(f"✅ Сгенерирован вопрос: {question}")
        return question
        
    except Exception as e:
        print(f"❌ Ошибка генерации вопроса с LLM: {e}")
        return get_fallback_question(session)

def clean_llm_response(text):
    """Очистка ответа от LLM от лишних форматирований"""
    if not text:
        return text
        
    # Удаляем маркеры кода
    text = text.replace('```json', '').replace('```', '').strip()
    
    # Удаляем возможные префиксы
    prefixes = ["Вопрос:", "Ответ:", "Оценка:", "JSON:"]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    
    # Берем первую строку если есть переносы
    if "\n" in text:
        text = text.split("\n")[0].strip()
        
    return text

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
            [СТРОГАЯ ИНСТРУКЦИЯ: ВЕРНИ ТОЛЬКО JSON БЕЗ ЛЮБОГО ДОПОЛНИТЕЛЬНОГО ТЕКСТА]

            Ты - технический интервьюер на позицию {position} уровня {level}.
            Проанализируй код кандидата и дай объективную оценку.

            ВОПРОС: {question}
            
            КОД КАНДИДАТА (язык: {language}):
            ```{language}
            {answer}
            ```

            Проанализируй код по критериям и поставь оценку от 1 до 10:
            - Корректность решения
            - Качество и читаемость кода
            - Эффективность алгоритма  
            - Обработка edge cases
            - Следование best practices

            ВЕРНИ ТОЛЬКО JSON:
            {{
                "score": число от 1 до 10,
                "feedback": "конкретная обратная связь",
                "strengths": ["сильная сторона 1", "сильная сторона 2"],
                "improvements": ["улучшение 1", "улучшение 2"],
                "code_analysis": {{
                    "correctness": "оценка корректности",
                    "readability": "оценка читаемости",
                    "efficiency": "оценка эффективности",
                    "best_practices": "следование best practices"
                }}
            }}
            """
        else:
            prompt = f"""
            [СТРОГАЯ ИНСТРУКЦИЯ: ВЕРНИ ТОЛЬКО JSON БЕЗ ЛЮБОГО ДОПОЛНИТЕЛЬНОГО ТЕКСТА]

            Ты - технический интервьюер на позицию {position} уровня {level}.
            Оцени ответ кандидата на вопрос.

            ВОПРОС: {question}
            
            ОТВЕТ КАНДИДАТА: {answer}

            Проанализируй ответ по критериям и поставь оценку от 1 до 10:
            - Техническая глубина и точность
            - Практическая применимость знаний
            - Структура и ясность изложения
            - Соответствие уровню позиции
            - Наличие конкретных примеров

            ВЕРНИ ТОЛЬКО JSON:
            {{
                "score": число от 1 до 10,
                "feedback": "конкретная обратная связь",
                "strengths": ["сильная сторона 1", "сильная сторона 2"],
                "improvements": ["улучшение 1", "улучшение 2"]
            }}
            """

        messages = [
            {
                "role": "system",
                "content": "Ты строгий технический интервьюер. Возвращай ТОЛЬКО валидный JSON. Никакого дополнительного текста."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        print(f"📊 Отправка запроса на оценку ответа")
        response = chat_with_model(messages)
        evaluation_text = response.choices[0].message.content.strip()
        
        print(f"📨 Получен ответ от LLM: {evaluation_text[:200]}...")
        
        # Очистка и парсинг JSON
        evaluation_text = clean_llm_response(evaluation_text)
        evaluation = json.loads(evaluation_text)
        
        # Валидация оценки
        if 'score' not in evaluation:
            evaluation['score'] = 5
        else:
            evaluation['score'] = max(1, min(10, int(evaluation['score'])))
            
        # Добавляем анализ кода если это код
        if contains_code and 'code_analysis' not in evaluation:
            evaluation['code_analysis'] = {
                "correctness": "Анализ не выполнен",
                "readability": "Анализ не выполнен", 
                "efficiency": "Анализ не выполнен",
                "best_practices": "Анализ не выполнен"
            }
            
        print(f"✅ Оценка сформирована: {evaluation['score']}/10")
        return evaluation
        
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return get_fallback_evaluation(contains_code, 5)
    except Exception as e:
        print(f"❌ Ошибка оценки ответа: {e}")
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