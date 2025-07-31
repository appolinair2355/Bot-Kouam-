# app.py
from flask import Flask, request
from telegram.ext import Application
import os
import threading
import time

app = Flask(__name__)

# === 🔐 Variables d'environnement ===
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# === 🌐 Webhook URL auto (Render) ===
SERVICE_NAME = os.getenv("RENDER_SERVICE_NAME")
if SERVICE_NAME:
    WEBHOOK_URL = f"https://{SERVICE_NAME}.onrender.com/webhook"
else:
    WEBHOOK_URL = "https://localhost/webhook"

# === 🤖 Initialisation du bot ===
bot_app = Application.builder().token(TOKEN).build()

# Importer les fonctions de bot.py
from bot import (
    demarrer,
    lien,
    handle_new_chat_members,
    handle_edited_message,
    handle_new_message
)

from telegram.ext import CommandHandler
import telegram.ext.filters as filters

# Enregistrer les gestionnaires
bot_app.add_handler(CommandHandler("demarrer", demarrer))
bot_app.add_handler(CommandHandler("lien", lien))
bot_app.add_handler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_chat_members)
bot_app.add_handler(filters.EDITED_MESSAGE & (filters.TEXT | filters.CAPTION), handle_edited_message)
bot_app.add_handler(filters.TEXT & ~filters.EDITED_MESSAGE, handle_new_message)

# === 📡 Webhook route ===
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if update:
        try:
            bot_app.process_update([update])
        except Exception as e:
            print(f"[app.py] Erreur webhook: {e}")
    return 'OK', 200

@app.route('/')
def index():
    return "🟢 Bot de prédiction de Kouamé est en ligne !", 200

# === 🚀 Démarrer après Flask ===
def start_webhook():
    try:
        bot_app.bot.delete_webhook(drop_pending_updates=True)
        bot_app.bot.set_webhook(url=WEBHOOK_URL)
        print(f"✅ Webhook configuré sur : {WEBHOOK_URL}")
    except Exception as e:
        print(f"[app.py] Échec du webhook: {e}")

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    thread = threading.Thread(target=run_flask, daemon=True)
    thread.start()
    time.sleep(3)
    start_webhook()
    while True:
        time.sleep(10)
