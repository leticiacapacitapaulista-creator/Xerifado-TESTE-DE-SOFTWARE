import smtplib
import ssl
import os
from email.message import EmailMessage
from flask import Flask, request, jsonify

# Configurações
EMAIL_ORIGEM = "almoxarifadoprojweb@gmail.com" 
EMAIL_SENHA = os.environ.get("GMAIL_APP_SENHA")

# Este será o e-mail padrão para alertas de sistema (estoque baixo), 
# caso nenhum destinatário específico seja informado.
EMAIL_ADMIN_PADRAO = "audemarioestudante@gmail.com"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465 

app = Flask(__name__)

@app.route('/send_email', methods=['POST'])
def send_email():
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "Payload JSON inválido"}), 400

    subject = dados.get('subject')
    body = dados.get('body')
    # Tenta pegar o destinatário do JSON, se não tiver, usa o do Admin
    to_email = dados.get('to_email', EMAIL_ADMIN_PADRAO)

    if not subject or not body:
        return jsonify({"erro": "Faltando 'subject' ou 'body'"}), 400

    print(f"Enviando e-mail para: {to_email} | Assunto: {subject}")

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = EMAIL_ORIGEM
        msg['To'] = to_email # <--- Agora é dinâmico
        msg.set_content(body)

        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as smtp:
            smtp.login(EMAIL_ORIGEM, EMAIL_SENHA)
            smtp.send_message(msg)

        print("E-mail enviado com sucesso!")
        return jsonify({"sucesso": True}), 200

    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        return jsonify({"sucesso": False, "erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)