# coding: utf-8
# Импортирует поддержку UTF-8.
from __future__ import unicode_literals

# Импортируем модули для работы с JSON и логами.
import json
import logging
import random

# Импортируем подмодули Flask для запуска веб-сервиса.

from flask import Flask, request

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

# Хранилище данных о сессиях.
sessionStorage = {}
questions = {}
reverse_questions = {}


# Задаем параметры приложения Flask.
@app.route("/", methods=['POST'])
def main():
    # Функция получает тело запроса и возвращает ответ.
    logging.info('Request: %r', request.json)

    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False
        }
    }

    fill_questions()

    handle_dialog(request.json, response)

    logging.info('Response: %r', response)
    clear_sessions()
    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )


# Функция для непосредственной обработки диалога.
def handle_dialog(req, res):
    user_id = req['session']['user_id']

    if req['session']['new'] or user_id not in sessionStorage.keys():
        # Это новый пользователь.
        # Инициализируем сессию и поприветствуем его.

        sessionStorage[user_id] = {
            'questions': [],
            'strike': 0,
            'last': "Вопрос отсутствует"
        }

        res['response']['text'] = 'Привет! Давай поиграем в \"Угадай столицу\"! Я буду называть страну, а ты угадывать' \
                                  ' её столицу. Или я буду называть город, а ты должен будешь угадать,' \
                                  ' столицей какого государства он является. Если ты не можешь угадать ответ - просто' \
                                  ' скажи \"дальше\", и мы пропустим этот вопрос.' \
                                  ' Для того, чтобы начать, скажи \"начать\".' \
                                  ' Для завершения игры скажите \"выйти\". Ну что, начнём?'
        res['response']['buttons'] = [{
            'title': 'Начать',
            'hide': True
        }]

        return

    words = req['request']['original_utterance'].lower().split()

    if 'выход' in words or 'хватит' in words or 'выйти' in words:
        res['response']['text'] = "Пока-пока!"
        res['response']['end_session'] = True
        sessionStorage.pop(user_id)
        return

    if 'помощь' in words or 'помоги' in words or 'умеешь' in words:
        res['response']['text'] = 'Я - навык Алисы - игра \"Угадай столицу\"! Я буду называть страну, а ты угадывать' \
                                  ' её столицу. Или я буду называть город, а ты должен будешь угадать,' \
                                  ' столицей какого государства он является. Если ты не можешь угадать ответ - просто' \
                                  ' скажи \"дальше\", и мы пропустим этот вопрос.' \
                                  ' Для того, чтобы начать, скажи \"начать\".' \
                                  ' Чтобы повторить вопрос, скажи мне \"вопрос\".' \
                                  ' Для завершения игры скажите \"выйти\".'
        res['response']['buttons'] = [
            {
                'title': 'Начать',
                'hide': True
            },
            {
                'title': 'Помощь',
                'hide': True
            }
        ]
        return

    if len(sessionStorage[user_id]['questions']) == 0:
        if 'начать' in words or 'начнем' in words or 'вопрос' in words:
            res['response']['text'] = 'Итак, первый вопрос: '
            question = random.choice(list(questions.keys()))
            res['response']['text'] += 'Какой город является столицей ' + question + '?'
            sessionStorage[user_id]['questions'].append((question, True))

            res['response']['buttons'] = [{
                'title': 'Дальше',
                'hide': True
            }]
            sessionStorage[user_id]['last'] = res['response']['text']
            return
        else:
            res['response']['text'] = "Я не знаю такой команды. Скажите \"начать\", чтобы начать игру." \
                                      " Также можете получить помощь, сказав мне \"помощь\""
            res['response']['buttons'] = [{
                'title': 'Начать',
                'hide': True
            }]
            return

    last_question, is_last_country = sessionStorage[user_id]['questions'][-1]

    if is_last_country:
        right_answer = questions[last_question]
    else:
        right_answer = reverse_questions[last_question]

    if 'дальше' in words or 'далее' in words:
        sessionStorage[user_id]['strike'] = 0
        res['response']['text'] = "Не страшно! В следующий раз угадаешь."
        res['response']['text'] += " Правильный ответ - " + right_answer + ". "

        new_ask(user_id, res)
        return

    right_answer = right_answer.lower()
    if 'вопрос' in words or 'повтори' in words or 'начать' in words:
        res['response']['text'] = sessionStorage[user_id]['last']
        return

    if is_truth_answer(req['request']['original_utterance'].lower(), right_answer):
        res['response']['text'] = "Правильно! "
        sessionStorage[user_id]['strike'] += 1
        if sessionStorage[user_id]['strike'] % 5 == 0:
            res['response']['text'] += "Ты ответил правильно на " + \
                                       str(sessionStorage[user_id]['strike']) + " вопросов подряд! "
        new_ask(user_id, res)
    else:
        sessionStorage[user_id]['strike'] = 0
        res['response']['text'] = "Не правильно! Попробуй еще раз."
        res['response']['buttons'] = [
            {
                'title': 'Дальше',
                'hide': True
            },
            {
                'title': 'Вопрос',
                'hide': True
            }
        ]


def fill_questions():
    with open("questions.txt", "r", encoding="utf-8") as f:
        for line in f.readlines():
            question, answer = line.split(" - ")
            answer = answer[:-1] if answer[-1] == "\n" else answer
            questions[question] = answer
            reverse_questions[answer] = question


def generate_question(existing_questions):
    if len(existing_questions) > 0:
        countries = [e_q[0] for e_q in list(existing_questions) if e_q[1]]
        capitals = [e_q[0] for e_q in list(existing_questions) if not e_q[1]]
        questions_pull = {
            country: capital for country, capital in questions.items()
            if country not in countries and capital not in capitals
        }
    else:
        questions_pull = questions

    is_country = bool(random.getrandbits(1))

    if is_country:
        return random.choice(list(questions_pull.keys())), True

    return random.choice(list(reverse_questions.keys())), False


def new_ask(user_id, res):
    question, is_country = generate_question(sessionStorage[user_id]['questions'])
    ask = ''
    if is_country:
        ask += 'Какой город является столицей ' + question + '?'
        sessionStorage[user_id]['questions'].append((question, True))
    else:
        ask += 'Столицей какого государства является ' + question + '?'
        sessionStorage[user_id]['questions'].append((question, False))

    res['response']['text'] += ask
    sessionStorage[user_id]['last'] = ask

    res['response']['buttons'] = [{
        'title': 'Дальше',
        'hide': True
    },
        {
            'title': 'Вопрос',
            'hide': True
        }
    ]


def clear_sessions():
    if len(sessionStorage.keys()) > 1000:
        margin = 850
        for i in sessionStorage.keys():
            sessionStorage.pop(i)
            margin -= 1
            if margin < 1:
                break


def is_truth_answer(answer, truth):
    words = answer.lower().split()
    if truth[:-1] == answer.lower()[:-1] or truth == answer.lower()[:-1] or truth[:-1] == answer.lower():
        return True
    if truth in words:
        return True
    if answer.lower() == " ".join(truth.split("-")):
        return True
    return False


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, ssl_context=('cert.pem', 'key.pem'))
