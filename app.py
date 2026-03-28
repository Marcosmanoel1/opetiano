from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

user_states = {}

SENHA_CORRETA = "amoseresta"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)


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

    state = user_states.get(chat_id, "inicio")

    if state == "inicio":
        send_message(chat_id, "Olá! Você é petiano?")
        user_states[chat_id] = "aguarda_petiano"

    elif state == "aguarda_petiano":
        if is_positive(text):
            send_message(chat_id, "Você é petiano do PET Enfermagem UFC?")
            user_states[chat_id] = "aguarda_pet_enf"
        elif is_negative(text):
            send_message(chat_id, "Entendido! Este bot é exclusivo para petianos. Até mais!")
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
            user_states[chat_id] = "autorizado"
        else:
            send_message(chat_id, "❌ Senha incorreta. Acesso encerrado.")
            user_states.pop(chat_id, None)

    elif state == "autorizado":
        send_message(chat_id, "Você já está autenticado! Em breve mais funcionalidades estarão disponíveis.")

    return jsonify({"status": "ok"})


@app.route("/")
def index():
    return "Opetiano bot está rodando!", 200


if __name__ == "__main__":
    app.run(debug=False)
