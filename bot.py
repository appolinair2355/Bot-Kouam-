# bot.py
from telegram import Update
from telegram.ext import ContextTypes
import re
import os

# --- 🔍 Regex ---
PATTERN_EDIT = r'#N?(\d+)\.\s*(?:[^()]*(?:\([^)]*\)[^()]*)?-\s*)?\w*\(([^)]+)\)(?:\s*(?:▶|➡️)|\s*#T\d+.*?(?:▶|➡️))?'
PATTERN_NEW = r'#N?(\d+)\.\s*\w*\(([^)]+)\)'

# --- 🧠 Stockage ---
active_predictions = {}

# --- 🔎 Fonctions utilitaires ---
def extract_cards(text):
    return re.findall(r'\d{1,2}[♥️♦️♣️♠️]|[JQKA][♥️♦️♣️♠️]', text)

def get_suit(card):
    if '♥️' in card: return '♥️'
    elif '♦️' in card: return '♦️'
    elif '♣️' in card: return '♣️'
    elif '♠️' in card: return '♠️'
    return ''

# --- 📤 Envoi vers le canal ---
async def envoyer_prediction(context: ContextTypes.DEFAULT_TYPE, text: str):
    channel = context.bot_data.get('target_channel')
    if not channel:
        return None
    try:
        msg = await context.bot.send_message(chat_id=channel, text=text)
        return msg.message_id
    except Exception as e:
        print(f"[bot.py] Impossible d'envoyer à {channel} : {e}")
        return None

# --- 🤖 Commandes ---
async def demarrer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_id = os.getenv("ADMIN_ID")

    if str(user_id) != admin_id:
        await update.message.reply_text("❌ Accès refusé.")
        return

    context.bot_data['predictions_active'] = True
    await update.message.reply_text("🟢 Prédiction automatique activée !\nLes prédictions seront envoyées dans le canal configuré.")

async def lien(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin_id = os.getenv("ADMIN_ID")

    if str(user_id) != admin_id:
        await update.message.reply_text("❌ Accès refusé.")
        return

    if not context.args:
        await update.message.reply_text("UsageId : `/lien @nom_du_canal` ou `https://t.me/nom_du_canal`")
        return

    channel_input = " ".join(context.args).strip()
    channel_id = None

    if channel_input.startswith('@'):
        channel_id = channel_input
    elif 't.me/' in channel_input:
        channel_id = '@' + channel_input.split('t.me/')[-1].split('/')[0]
    else:
        await update.message.reply_text("❌ Format invalide.")
        return

    context.bot_data['target_channel'] = channel_id
    await update.message.reply_text(f"📤 Canal de prédiction défini : {channel_id}")

async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            await update.message.reply_text("Salut je suis le bot de prédiction automatique de Kouamé")

# --- ✏️ Message édité → lance prédiction ---
async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.bot_data.get('predictions_active', False):
        return

    message = update.edited_message
    text = message.text or message.caption
    if not text:
        return

    match = re.search(PATTERN_EDIT, text)
    if not match:
        return

    try:
        numero = int(match.group(1))
        second_parentheses = match.group(2)
        cards = extract_cards(second_parentheses)

        if len(cards) < 2:
            return

        second_card = cards[1]
        suit = get_suit(second_card)
        if not suit:
            return

        numero_predit = numero + 2
        prediction_msg = f"🔵{numero_predit}🔵{suit} statut : ⌛"

        message_id = await envoyer_prediction(context, prediction_msg)

        if message_id:
            active_predictions[numero_predit] = {
                'suit': suit,
                'message_id': message_id,
                'chat_id': context.bot_data['target_channel'],
                'attempts': 0
            }

    except Exception as e:
        print(f"[bot.py] Erreur handle_edited: {e}")

# --- 📥 Nouveau message → vérifie déplacement ---
async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or update.message.caption
    if not text:
        return

    match = re.search(PATTERN_NEW, text)
    if not match:
        return

    try:
        numero = int(match.group(1))
        first_hand = match.group(2)
        cards = extract_cards(first_hand)
        suits_in_hand = [get_suit(c) for c in cards if get_suit(c)]

        channel = context.bot_data.get('target_channel')
        if not channel:
            return

        # ✅0️⃣
        if numero in active_predictions:
            pred = active_predictions[numero]
            if pred['suit'] in suits_in_hand:
                new_text = f"🔵{numero}🔵{pred['suit']} statut : ✅0️⃣"
                await context.bot.edit_message_text(
                    chat_id=channel,
                    message_id=pred['message_id'],
                    text=new_text
                )
                del active_predictions[numero]

        # ✅1️⃣
        for pred_num, pred in list(active_predictions.items()):
            if pred['attempts'] >= 1:
                continue
            if numero == pred_num + 1:
                if pred['suit'] in suits_in_hand:
                    new_text = f"🔵{pred_num}🔵{pred['suit']} statut : ✅1️⃣"
                    await context.bot.edit_message_text(
                        chat_id=channel,
                        message_id=pred['message_id'],
                        text=new_text
                    )
                else:
                    pred['attempts'] = 1
                return

        # ✅2️⃣ ou ⭕⭕
        for pred_num, pred in list(active_predictions.items()):
            if pred['attempts'] < 2:
                pred['attempts'] = 2
            if numero == pred_num + 2:
                if pred['suit'] in suits_in_hand:
                    new_text = f"🔵{pred_num}🔵{pred['suit']} statut : ✅2️⃣"
                else:
                    new_text = f"🔵{pred_num}🔵{pred['suit']} statut : ⭕⭕"
                await context.bot.edit_message_text(
                    chat_id=channel,
                    message_id=pred['message_id'],
                    text=new_text
                )
                del active_predictions[pred_num]

    except Exception as e:
        print(f"[bot.py] Erreur handle_new: {e}")
