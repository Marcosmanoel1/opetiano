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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
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


def groq(system_prompt, user_message):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    instrucao_base = "Responda em UMA frase curta e casual, sem enrolação. Seja direto e leve, como uma mensagem de WhatsApp. Proibido listas ou textos longos."
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": f"{instrucao_base}\n\n{system_prompt}"},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 60
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    if "choices" not in data:
        return "Desculpe, tive um problema interno. Tente novamente."
    return data["choices"][0]["message"]["content"]


def verificar_timeout(chat_id):
    agora = time.time()
    ultima = user_last_interaction.get(chat_id, 0)
    if agora - ultima > TIMEOUT_SEGUNDOS and chat_id in user_states:
        user_states.pop(chat_id, None)
        return True
    return False


def detectar_intencao(text, tipo):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    system = f'Responda APENAS com o JSON {{"intencao": "sim"}} ou {{"intencao": "nao"}} ou {{"intencao": "indefinido"}}. O usuário está sendo perguntado se {tipo}.'
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text}
        ],
        "max_tokens": 20
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        resposta = data["choices"][0]["message"]["content"]
        resposta = resposta.strip().replace("```json", "").replace("```", "")
        parsed = json.loads(resposta)
        return parsed.get("intencao", "indefinido")
    except:
        return "indefinido"


def quer_sair(text):
    palavras = ["nada", "sair", "tchau", "encerrar", "não quero", "nao quero",
                "obrigado", "obg", "valeu", "até", "ate", "flw", "bye", "nada mais"]
    return any(p in text.strip().lower() for p in palavras)


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
        send_message(chat_id, "⏱️ Sessão encerrada por inatividade. Manda uma mensagem pra começar de novo!")
        return jsonify({"status": "ok"})

    user_last_interaction[chat_id] = time.time()
    state = user_states.get(chat_id, "inicio")

    if state == "inicio":
        resposta = groq(
            "Você é o assistente do PET Enfermagem UFC. Cumprimente o usuário e pergunte se ele é petiano.",
            text
        )
        send_message(chat_id, resposta)
        user_states[chat_id] = "aguarda_petiano"

    elif state == "aguarda_petiano":
        intencao = detectar_intencao(text, "é petiano")
        if intencao == "sim":
            resposta = groq(
                "Usuário confirmou que é petiano. Reaja brevemente e pergunte se é do PET Enfermagem UFC.",
                text
            )
            send_message(chat_id, resposta)
            user_states[chat_id] = "aguarda_pet_enf"
        elif intencao == "nao":
            resposta = groq(
                "Usuário disse que NÃO é petiano. Responda de forma bem-humorada dizendo que este bot é só para petianos.",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)
        else:
            resposta = groq(
                "Usuário não respondeu claramente. Peça para responder sim ou não se é petiano.",
                text
            )
            send_message(chat_id, resposta)

    elif state == "aguarda_pet_enf":
        intencao = detectar_intencao(text, "é petiano do PET Enfermagem UFC")
        if intencao == "sim":
            resposta = groq(
                "Usuário confirmou que é do PET Enfermagem UFC. Reaja e peça a senha de acesso.",
                text
            )
            send_message(chat_id, resposta)
            user_states[chat_id] = "aguarda_senha"
        elif intencao == "nao":
            resposta = groq(
                "Usuário disse que NÃO é do PET Enfermagem UFC. Diga que o bot é exclusivo para o PET Enfermagem UFC.",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)
        else:
            resposta = groq(
                "Usuário não respondeu claramente. Peça para responder sim ou não se é do PET Enfermagem UFC.",
                text
            )
            send_message(chat_id, resposta)

    elif state == "aguarda_senha":
        if text.strip().lower() == SENHA_CORRETA:
            resposta = groq(
                "Usuário se autenticou com sucesso. Dê boas vindas curtas e animadas.",
                text
            )
            send_message(chat_id, resposta)
            time.sleep(1)
            send_menu(chat_id, "Sobre o que você deseja saber?")
            user_states[chat_id] = "menu"
        else:
            resposta = groq(
                "Usuário digitou senha incorreta. Informe que a senha está errada e o acesso foi encerrado.",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)

    elif state == "menu":
        if quer_sair(text):
            resposta = groq(
                "Usuário quer encerrar a conversa. Despeça-se de forma simpática e curta.",
                text
            )
            send_message(chat_id, resposta)
            user_states.pop(chat_id, None)
        elif "Comissões" in text:
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
            resposta = groq(
                "Usuário autenticado enviou mensagem fora do menu. Peça que escolha uma opção do menu.",
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
