from flask import Flask, request, jsonify
import requests
import os
import time
import json

app = Flask(__name__)

user_states = {}
user_last_interaction = {}

SENHA_CORRETA = "amoseresta"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TIMEOUT_SEGUNDOS = 30


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"remove_keyboard": True}
    }
    requests.post(url, json=payload)


def send_menu(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    keyboard = {
        "keyboard": [
            ["📋 Comissões", "📅 Atividades gerais"],
            ["📖 História do PET", "📌 Pendências do Notion"],
            ["💰 Bolsa caiu?"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "persistent": True
    }
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard
    }
    requests.post(url, json=payload)


def gemini(system_prompt, user_message):
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_message}]}
        ]
    }
    response = requests.post(url, json=payload)
    data = response.json()
    print("GEMINI RESPONSE:", data)
    if "candidates" not in data:
        print("ERRO GEMINI:", data)
        return "Desculpe, tive um problema interno. Tente novamente."
    return data["candidates"][0]["content"]["parts"][0]["text"]


def verificar_timeout(chat_id):
    agora = time.time()
    ultima = user_last_interaction.get(chat_id, 0)
    if agora - ultima > TIMEOUT_SEGUNDOS and chat_id in user_states:
        user_states.pop(chat_id, None)
        return True
    return False


def detectar_intencao(text, tipo):
    system = f"""Você deve analisar a mensagem do usuário e detectar a intenção.
Responda APENAS com um JSON no formato: {{"intencao": "sim"}} ou {{"intencao": "nao"}} ou {{"intencao": "indefinido"}}
Contexto: o usuário está sendo perguntado se {tipo}.
Detecte se a resposta é positiva, negativa ou indefinida."""
    try:
        resposta = gemini(system, text)
        resposta = resposta.strip().replace("```json", "").replace("```", "")
        data = json.loads(resposta)
        return data.get("intencao", "indefinido")
    except:
        return "indefinido"


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
    except (KeyError, TypeError):
        return jsonify({"status": "ok"})

    expirou = verificar_timeout(chat_id)
    if expirou:
        resposta = gemini(
            "Você é o assistente do PET Enfermagem UFC. Avise ao usuário de forma simpática que a sessão expirou por inatividade e que ele pode enviar uma mensagem para começar novamente.",
            text
        )
        send_message(chat_id, resposta)
        return jsonify({"status": "ok"})

    user_last_interaction[chat_id] = time.time()
    state = user_states.get(chat_id, "inicio")

    if state == "inicio":
        resposta = gemini(
            """Você é o assistente virtual do PET Enfermagem UFC, um grupo de educação tutorial da Universidade Federal do Ceará.
Seja simpático e acolhedor. Cumprimente o usuário de forma inteligente e natural considerando o que ele disse.
Ao final da sua resposta, SEMPRE pergunte: 'Você é petiano?' de forma natural.""",
            text
        )
        send_message(chat_id, resposta)
        user_states[chat_id] = "aguarda_petiano"

    elif state == "aguarda_petiano":
        intencao = detectar_intencao(text, "é petiano")
        if intencao == "sim":
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário confirmou que é petiano.
Reaja de forma animada e natural. Ao final SEMPRE pergunte: 'Você é petiano do PET Enfermagem UFC?' de forma natural.""",
                text
            )
            send_message(chat_id, resposta)
            user_states[chat_id] = "aguarda_pet_enf"
        elif intencao == "nao":
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário disse que NÃO é petiano.
Responda de forma bem-humorada e um pouco debochada dizendo que este bot é exclusivo para petianos e que ele deve sair. Seja criativo!""",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)
        else:
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário não respondeu claramente se é petiano.
Peça gentilmente que ele responda com sim ou não se é petiano.""",
                text
            )
            send_message(chat_id, resposta)

    elif state == "aguarda_pet_enf":
        intencao = detectar_intencao(text, "é petiano do PET Enfermagem UFC")
        if intencao == "sim":
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário confirmou que é do PET Enfermagem UFC.
Reaja com entusiasmo! Ao final SEMPRE peça a senha de acesso de forma natural.""",
                text
            )
            send_message(chat_id, resposta)
            user_states[chat_id] = "aguarda_senha"
        elif intencao == "nao":
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário disse que NÃO é do PET Enfermagem UFC.
Responda de forma simpática dizendo que este bot é exclusivo para o PET Enfermagem UFC especificamente.""",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)
        else:
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário não respondeu claramente.
Peça gentilmente que responda com sim ou não se é do PET Enfermagem UFC.""",
                text
            )
            send_message(chat_id, resposta)

    elif state == "aguarda_senha":
        if text.strip().lower() == SENHA_CORRETA:
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário acabou de se autenticar com sucesso.
Dê as boas vindas de forma calorosa e animada! Seja criativo e mencione que agora ele tem acesso ao sistema.""",
                text
            )
            send_message(chat_id, resposta)
            time.sleep(1)
            send_menu(chat_id, "Sobre o que você deseja saber?")
            user_states[chat_id] = "menu"
        else:
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário digitou uma senha incorreta.
Informe que a senha está incorreta e que o acesso foi encerrado. Seja simpático mas firme.""",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)

    elif state == "menu":
        if "Comissões" in text:
            send_message(chat_id, "📋 *Comissões*\n\nAqui ficarão as informações sobre as comissões do PET Enfermagem UFC. Em breve!")
            send_menu(chat_id, "O que mais deseja saber?")
        elif "Atividades" in text:
            send_message(chat_id, "📅 *Atividades Gerais*\n\nAqui ficarão as informações sobre as atividades gerais do PET. Em breve!")
            send_menu(chat_id, "O que mais deseja saber?")
        elif "História" in text:
            send_message(chat_id, "📖 *História do PET*\n\nAqui ficará a história do PET Enfermagem UFC. Em breve!")
            send_menu(chat_id, "O que mais deseja saber?")
        elif "Pendências" in text:
            send_message(chat_id, "📌 *Pendências do Notion*\n\nAqui ficarão as pendências registradas no Notion. Em breve!")
            send_menu(chat_id, "O que mais deseja saber?")
        elif "Bolsa" in text:
            send_message(chat_id, "💰 *Bolsa caiu?*\n\nAinda não... mas quando cair você vai saber! 😅")
            send_menu(chat_id, "O que mais deseja saber?")
        else:
            resposta = gemini(
                """Você é o assistente do PET Enfermagem UFC. O usuário está autenticado e enviou uma mensagem fora do menu.
Responda de forma simpática e peça que escolha uma das opções do menu disponível.""",
                text
            )
            send_message(chat_id, resposta)
            send_menu(chat_id, "O que mais deseja saber?")

    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return "Opetiano bot está rodando!", 200


if __name__ == "__main__":
    app.run(debug=False)
