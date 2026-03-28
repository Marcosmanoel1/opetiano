from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Estado dos usuários em memória
user_states = {}

SENHA_CORRETA = "amoseresta"
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")


def send_message(to, text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)


def is_positive(text):
    positivos = ["sim", "s", "yes", "y", "claro", "com certeza", "afirmativo"]
    return text.strip().lower() in positivos


def is_negative(text):
    negativos = ["não", "nao", "n", "no", "negativo"]
    return text.strip().lower() in negativos


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    try:
        messages = data["entry"][0]["changes"][0]["value"]["messages"]
    except (KeyError, IndexError):
        return jsonify({"status": "ok"})

    for message in messages:
        phone = message["from"]
        text = message.get("text", {}).get("body", "")
        state = user_states.get(phone, "inicio")

        if state == "inicio":
            send_message(phone, "Olá! Você é petiano?")
            user_states[phone] = "aguarda_petiano"

        elif state == "aguarda_petiano":
            if is_positive(text):
                send_message(phone, "Você é petiano do PET Enfermagem UFC?")
                user_states[phone] = "aguarda_pet_enf"
            elif is_negative(text):
                send_message(phone, "Entendido! Este bot é exclusivo para petianos. Até mais!")
                user_states.pop(phone, None)
            else:
                send_message(phone, "Por favor, responda com Sim ou Não.")

        elif state == "aguarda_pet_enf":
            if is_positive(text):
                send_message(phone, "Ótimo! Por favor, informe a senha de acesso:")
                user_states[phone] = "aguarda_senha"
            elif is_negative(text):
                send_message(phone, "Este bot é exclusivo para o PET Enfermagem UFC. Até mais!")
                user_states.pop(phone, None)
            else:
                send_message(phone, "Por favor, responda com Sim ou Não.")

        elif state == "aguarda_senha":
            if text.strip().lower() == SENHA_CORRETA:
                send_message(phone, "✅ Acesso autorizado! Bem-vindo ao PET Enfermagem UFC!")
                user_states[phone] = "autorizado"
            else:
                send_message(phone, "❌ Senha incorreta. Acesso encerrado.")
                user_states.pop(phone, None)

        elif state == "autorizado":
            send_message(phone, "Você já está autenticado! Em breve mais funcionalidades estarão disponíveis.")

    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=False)
