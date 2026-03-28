from flask import Flask, request, jsonify
import requests
import os
import time

app = Flask(__name__)

user_states = {}
user_last_interaction = {}

SENHA_CORRETA = "amoseresta"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TIMEOUT_SEGUNDOS = 30  # 30 segundos


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
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


def verificar_timeout(chat_id):
    agora = time.time()
    ultima = user_last_interaction.get(chat_id, 0)
    if agora - ultima > TIMEOUT_SEGUNDOS and chat_id in user_states:
        user_states.pop(chat_id, None)
        return True
    return False


def is_positive(text):
    positivos = ["sim", "s", "yes", "y", "claro", "com certeza", "afirmativo"]
    return text.strip().lower() in positivos


def is_negative(text):
    negativos = ["não", "nao", "n", "no", "negativo"]
    return text.strip().lower() in negativos


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        message = data["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
    except (KeyError, TypeError):
        return jsonify({"status": "ok"})

    # Verifica timeout antes de processar
    expirou = verificar_timeout(chat_id)
    if expirou:
        send_message(chat_id, "⏱️ Sua sessão foi encerrada por inatividade. Envie qualquer mensagem para começar novamente.")

    # Atualiza o tempo da última interação
    user_last_interaction[chat_id] = time.time()

    state = user_states.get(chat_id, "inicio")

    if state == "inicio":
        send_message(chat_id, "Olá! Você é petiano?")
        user_states[chat_id] = "aguarda_petiano"

    elif state == "aguarda_petiano":
        if is_positive(text):
            send_message(chat_id, "Você é petiano do PET Enfermagem UFC?")
            user_states[chat_id] = "aguarda_pet_enf"
        elif is_negative(text):
            send_message(chat_id, "Saia daqui, não quero falar com você! 😤")
            user_states.pop(chat_id, None)
        else:
            send_message(chat_id, "Por favor, responda com Sim ou Não.")

    elif state == "aguarda_pet_enf":
        if is_positive(text):
            send_message(chat_id, "Ótimo! Por favor, informe a senha de acesso:")
            user_states[chat_id] = "aguarda_senha"
        elif is_negative(text):
            send_message(chat_id, "Este bot é exclusivo para o PET Enfermagem UFC. Até mais!")
            user_states.pop(chat_id, None)
        else:
            send_message(chat_id, "Por favor, responda com Sim ou Não.")

    elif state == "aguarda_senha":
        if text.strip().lower() == SENHA_CORRETA:
            send_message(chat_id, "✅ Acesso autorizado! Bem-vindo ao PET Enfermagem UFC!")
            time.sleep(1)
            send_menu(chat_id, "Sobre o que você deseja saber?")
            user_states[chat_id] = "menu"
        else:
            send_message(chat_id, "❌ Senha incorreta. Acesso encerrado.")
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
            send_menu(chat_id, "Por favor, escolha uma das opções do menu.")

    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return "Opetiano bot está rodando!", 200


if __name__ == "__main__":
    app.run(debug=False)
