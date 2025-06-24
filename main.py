# main.py — Telegram Bot to Collect GI Risk Data and Output Scoring (Webhook version)

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler, CallbackQueryHandler,
                          filters, ConversationHandler, ContextTypes)
from fastapi import FastAPI, Request, Response, HTTPException

from health_logic import calculate_total_risk, interpret_risk, nsaid_groups

# Telegram Bot Token
BOT_TOKEN = "7329446852:AAEcaewwKxlLO-w3vniZsTg4lZyBzlWZTB8"

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# States for conversation
(GET_NSAID, GET_NSAID_GROUP, GET_NSAID_NAME, GET_NSAID_DOSE,
 GET_ANTIPLATELET, GET_ANTICOAGULANT, GET_PPI_DOSE, GET_PPI_ROUTE,
 GET_INDICATIONS, CALCULATE_SCORE) = range(10)

# Data storage
data_store = {}

# FastAPI app
app = FastAPI()

# Initialize telegram app
application = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    data_store[user_id] = {
        'nsaid': False, 'nsaid_group': '', 'nsaid_name': '', 'nsaid_dose': 0,
        'antiplatelet': False, 'anticoagulant': False,
        'ppi_dose': 0, 'ppi_route': '',
        'indications': []
    }

    welcome_text = (
        "*PPIcheck.ai Delta Built_1.0*\n"
        "India's First Indigenously-Built AI Tool for Optimizing PPI Therapy\n\n"
        "PPIcheck.ai is revolutionizing the way clinicians make PPI deprescribing decisions.\n\n"
        "Our application combines established clinical guidelines with cutting-edge machine learning "
        "to provide evidence-based risk assessments, enabling healthcare professionals to optimize PPI therapy effectively.\n\n"
        "_Developed by Dr. Nabyendu Biswas, Department of Pharmacology, in collaboration with the Medicine Department, MKCG Medical College & Hospital_\n\n"
        "Let's begin your assessment.\nAre you currently taking an NSAID?"
    )

    keyboard = [[InlineKeyboardButton("Yes", callback_data="nsaid_Yes"),
                 InlineKeyboardButton("No", callback_data="nsaid_No")]]

    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_NSAID

async def get_nsaid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.callback_query.answer()
    data_store[user_id]['nsaid'] = (update.callback_query.data == "nsaid_Yes")

    if not data_store[user_id]['nsaid']:
        return await ask_antiplatelet(update, context)

    groups = list(nsaid_groups.keys())
    keyboard = [[InlineKeyboardButton(group, callback_data=f"group_{group}")] for group in groups if group != "None"]
    await update.callback_query.edit_message_text("Select NSAID Group:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_NSAID_GROUP

async def get_nsaid_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.callback_query.answer()
    group = update.callback_query.data.split("group_")[1]
    data_store[user_id]['nsaid_group'] = group

    names = list(nsaid_groups[group].keys())
    keyboard = [[InlineKeyboardButton(name, callback_data=f"name_{name}")] for name in names if name != "None"]
    await update.callback_query.edit_message_text("Select NSAID Name:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_NSAID_NAME

async def get_nsaid_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.callback_query.answer()
    name = update.callback_query.data.split("name_")[1]
    data_store[user_id]['nsaid_name'] = name
    await update.callback_query.edit_message_text("Enter NSAID dose in mg:")
    return GET_NSAID_DOSE

async def get_nsaid_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    try:
        dose = int(update.message.text)
        data_store[user_id]['nsaid_dose'] = dose
    except ValueError:
        await update.message.reply_text("Please enter a valid number (mg)")
        return GET_NSAID_DOSE
    return await ask_antiplatelet(update, context)

async def ask_antiplatelet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[InlineKeyboardButton("Yes", callback_data="ap_Yes"),
                 InlineKeyboardButton("No", callback_data="ap_No")]]
    await update.message.reply_text("Are you using an antiplatelet agent?", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ANTIPLATELET

async def get_antiplatelet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.callback_query.answer()
    data_store[user_id]['antiplatelet'] = (update.callback_query.data == "ap_Yes")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="ac_Yes"),
                 InlineKeyboardButton("No", callback_data="ac_No")]]
    await update.callback_query.edit_message_text("Are you using an anticoagulant?", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_ANTICOAGULANT

async def get_anticoagulant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.callback_query.answer()
    data_store[user_id]['anticoagulant'] = (update.callback_query.data == "ac_Yes")
    await update.callback_query.edit_message_text("Enter PPI Dose in mg:")
    return GET_PPI_DOSE

async def get_ppi_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    try:
        data_store[user_id]['ppi_dose'] = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid dose (mg)")
        return GET_PPI_DOSE
    keyboard = [[InlineKeyboardButton("Oral", callback_data="route_Oral"),
                 InlineKeyboardButton("IV", callback_data="route_IV")]]
    await update.message.reply_text("Select PPI route:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GET_PPI_ROUTE

async def get_ppi_route(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    data_store[user_id]['ppi_route'] = update.callback_query.data.split("route_")[1]

    indication_buttons = [
        [InlineKeyboardButton("Peptic ulcer treatment", callback_data="ind_Peptic ulcer treatment")],
        [InlineKeyboardButton("NSAID & ulcer/GIB history", callback_data="ind_NSAID & ulcer/GIB history")],
        [InlineKeyboardButton("Done", callback_data="ind_DONE")]
    ]
    await update.callback_query.edit_message_text("Select applicable indications (press 'Done' when finished):", reply_markup=InlineKeyboardMarkup(indication_buttons))
    return GET_INDICATIONS

async def get_indications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    user_id = update.effective_user.id
    ind = update.callback_query.data.replace("ind_", "")

    if ind == "DONE":
        return await calculate_final(update, context)

    if ind not in data_store[user_id]['indications']:
        data_store[user_id]['indications'].append(ind)

    return GET_INDICATIONS

async def calculate_final(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    inputs = data_store[user_id]
    score_details = calculate_total_risk(inputs)
    result_text, recommendation = interpret_risk(score_details['total_score'])

    message = f"Risk Score: {score_details['total_score']}\n{result_text}\n\nRecommendations:\n{recommendation}"
    await update.callback_query.edit_message_text(message)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

# Handlers
conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GET_NSAID: [CallbackQueryHandler(get_nsaid)],
        GET_NSAID_GROUP: [CallbackQueryHandler(get_nsaid_group)],
        GET_NSAID_NAME: [CallbackQueryHandler(get_nsaid_name)],
        GET_NSAID_DOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nsaid_dose)],
        GET_ANTIPLATELET: [CallbackQueryHandler(get_antiplatelet)],
        GET_ANTICOAGULANT: [CallbackQueryHandler(get_anticoagulant)],
        GET_PPI_DOSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ppi_dose)],
        GET_PPI_ROUTE: [CallbackQueryHandler(get_ppi_route)],
        GET_INDICATIONS: [CallbackQueryHandler(get_indications)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

application.add_handler(conv)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        update_json = await request.json()
        update = Update.de_json(update_json, application.bot)
        await application.process_update(update)
        return Response(content="OK", status_code=200)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
