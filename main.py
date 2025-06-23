# main.py (Webhook Bot for Vercel)

import os
import logging
import asyncio
from typing import Dict # Import Dict for type hinting

from fastapi import FastAPI, Request, Response, HTTPException # FastAPI for the web server
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, ContextTypes

# Import functions and data from your health_logic.py
from health_logic import calculate_bmi, assess_risk_and_recommend, nsaid_groups

# Set up logging for better visibility in Vercel logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Telegram Bot Setup ---
# Your Telegram Bot API Token. It's CRUCIAL to get this from environment variables
# when deploying to Vercel for security.
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize the Application outside of any function to keep it persistent for webhooks
# We don't run polling here, so no `run_polling()`
application = Application.builder().token(BOT_TOKEN).build()

# Define states for the conversation
(
    GET_AGE, GET_GENDER, GET_WEIGHT, GET_HEIGHT, GET_NSAID_USE,
    GET_NSAID_GROUP, GET_SPECIFIC_NSAID, GET_NSAID_DOSE, # New states for detailed NSAID input
    GET_ANTIPLATELET_USE, GET_HISTORY_PEPTIC_ULCER, GET_GI_BLEED_RISK, GET_CARDIO_RISK, GET_H_PYLORI,
    GET_RENAL_IMPAIRMENT, GET_HEPATIC_IMPAIRMENT, GET_CRITICAL_ILLNESS,
    GET_STEROID_USE, GET_ANTICOAGULANT_USE, GET_COMORBIDITY, GET_PPI_USE,
    GET_PPI_DOSE, GET_PPI_ROUTE, FINAL_ASSESSMENT
) = range(23) # Increased range for new NSAID states

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Hello! I can help assess your health risk. Let's start. What is your age?")
    context.user_data['patient_data'] = {}
    context.user_data['patient_data']['selected_nsaid_group'] = 'None'
    context.user_data['patient_data']['selected_nsaid'] = 'None'
    context.user_data['patient_data']['nsaid_dose'] = 0
    return GET_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        if not (0 <= age <= 120):
            raise ValueError("Invalid age")
        context.user_data['patient_data']['age'] = age
        keyboard = [[InlineKeyboardButton("Male", callback_data="gender_Male")],
                    [InlineKeyboardButton("Female", callback_data="gender_Female")],
                    [InlineKeyboardButton("Other", callback_data="gender_Other")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("What is your gender?", reply_markup=reply_markup)
        return GET_GENDER
    except ValueError:
        await update.message.reply_text("Please enter a valid age (e.g., 30).")
        return GET_AGE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['gender'] = query.data.split('_')[1]
    await query.edit_message_text(f"Your gender: {query.data.split('_')[1]}. Please enter your weight in kg (e.g., 70.5).")
    return GET_WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight_kg = float(update.message.text)
        context.user_data['patient_data']['weight_kg'] = weight_kg
        await update.message.reply_text("Please enter your height in cm (e.g., 175).")
        return GET_HEIGHT
    except ValueError:
        await update.message.reply_text("Please enter a valid weight in kg (e.g., 65.2).")
        return GET_WEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height_cm = float(update.message.text)
        context.user_data['patient_data']['height_cm'] = height_cm
        bmi = calculate_bmi(context.user_data['patient_data']['weight_kg'], height_cm)
        context.user_data['patient_data']['bmi'] = bmi
        await update.message.reply_text(f"Your BMI is: {bmi:.2f}.")

        keyboard = [[InlineKeyboardButton("Yes", callback_data="nsaid_True")],
                    [InlineKeyboardButton("No", callback_data="nsaid_False")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Are you currently taking NSAIDs (Non-Steroidal Anti-Inflammatory Drugs)?", reply_markup=reply_markup)
        return GET_NSAID_USE
    except ValueError:
        await update.message.reply_text("Please enter a valid height in cm (e.g., 168.5).")
        return GET_HEIGHT

async def get_nsaid_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    nsaid_currently_used = (query.data == "nsaid_True")
    context.user_data['patient_data']['nsaid_use'] = nsaid_currently_used

    if nsaid_currently_used:
        nsaid_group_options = list(nsaid_groups.keys())
        # Remove "None" if it's explicitly in your nsaid_groups.keys()
        if "None" in nsaid_group_options:
            nsaid_group_options.remove("None")

        keyboard = [[InlineKeyboardButton(group, callback_data=f"nsaid_group_{group}")] for group in nsaid_group_options]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Which NSAID group are you taking?", reply_markup=reply_markup)
        return GET_NSAID_GROUP
    else:
        context.user_data['patient_data']['selected_nsaid_group'] = 'None'
        context.user_data['patient_data']['selected_nsaid'] = 'None'
        context.user_data['patient_data']['nsaid_dose'] = 0
        return await ask_antiplatelet_use(update, context)

async def get_nsaid_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_group = query.data.split('_')[2]
    context.user_data['patient_data']['selected_nsaid_group'] = selected_group

    nsaid_options = list(nsaid_groups.get(selected_group, {}).keys())
    if "None" in nsaid_options:
        nsaid_options.remove("None")

    if not nsaid_options:
        await query.edit_message_text("No specific NSAIDs found for this group. Please select another group or type /cancel.")
        return GET_NSAID_GROUP

    keyboard = [[InlineKeyboardButton(nsaid, callback_data=f"specific_nsaid_{nsaid}")] for nsaid in nsaid_options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Which specific NSAID are you taking from {selected_group}?", reply_markup=reply_markup)
    return GET_SPECIFIC_NSAID

async def get_specific_nsaid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_nsaid = query.data.split('_')[2]
    context.user_data['patient_data']['selected_nsaid'] = selected_nsaid

    selected_group = context.user_data['patient_data']['selected_nsaid_group']
    nsaid_info = nsaid_groups.get(selected_group, {}).get(selected_nsaid)

    if nsaid_info:
        nsaid_dose_options, _, _, _ = nsaid_info
        # Ensure dose options are strings for callback_data
        keyboard = [[InlineKeyboardButton(str(dose), callback_data=f"nsaid_dose_{dose}")] for dose in nsaid_dose_options]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"What is your {selected_nsaid} dose (mg)?", reply_markup=reply_markup)
        return GET_NSAID_DOSE
    else:
        await query.edit_message_text("Could not find dose information for this NSAID. Please try again or type /cancel.")
        return GET_SPECIFIC_NSAID

async def get_nsaid_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        nsaid_dose_val = int(query.data.split('_')[2])
        context.user_data['patient_data']['nsaid_dose'] = nsaid_dose_val
        return await ask_antiplatelet_use(update, context)
    except ValueError:
        await query.edit_message_text("Invalid dose. Please select a valid dose from the options.")
        return GET_NSAID_DOSE

async def ask_antiplatelet_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[InlineKeyboardButton("Yes", callback_data="antiplatelet_True")],
                [InlineKeyboardButton("No", callback_data="antiplatelet_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Check if called from a callback_query or direct message
    if update.callback_query:
        await update.callback_query.edit_message_text("Are you currently taking antiplatelet medications (e.g., Aspirin, Clopidogrel)?", reply_markup=reply_markup)
    else: # This path might be for initial /start, though it usually goes through NSAID use first.
        await update.message.reply_text("Are you currently taking antiplatelet medications (e.g., Aspirin, Clopidogrel)?", reply_markup=reply_markup)
    return GET_ANTIPLATELET_USE

# The rest of the state-handling functions remain largely the same,
# they mostly store data and transition to the next state.
# I'm including them for completeness in the Canvas.

async def get_antiplatelet_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['antiplatelet_use'] = (query.data == "antiplatelet_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="ulcer_True")],
                [InlineKeyboardButton("No", callback_data="ulcer_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have a history of peptic ulcer?", reply_markup=reply_markup)
    return GET_HISTORY_PEPTIC_ULCER

async def get_history_peptic_ulcer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['history_peptic_ulcer'] = (query.data == "ulcer_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="gib_risk_True")],
                [InlineKeyboardButton("No", callback_data="gib_risk_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have other GI bleed risk factors (e.g., chronic liver disease, inflammatory bowel disease)?", reply_markup=reply_markup)
    return GET_GI_BLEED_RISK

async def get_gi_bleed_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['gi_bleed_risk_factors'] = (query.data == "gib_risk_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="cvd_risk_True")],
                [InlineKeyboardButton("No", callback_data="cvd_risk_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have significant cardiovascular disease risk factors?", reply_markup=reply_markup)
    return GET_CARDIO_RISK

async def get_cardio_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['cardiovascular_disease_risk'] = (query.data == "cvd_risk_True")
    keyboard = [[InlineKeyboardButton("Positive", callback_data="hpylori_True")],
                [InlineKeyboardButton("Negative", callback_data="hpylori_False")],
                [InlineKeyboardButton("Unknown", callback_data="hpylori_Unknown")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you H. pylori positive?", reply_markup=reply_markup)
    return GET_H_PYLORI

async def get_h_pylori(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    hp_status = query.data.split('_')[1]
    context.user_data['patient_data']['h_pylori_positive'] = True if hp_status == 'True' else (False if hp_status == 'False' else None)

    keyboard = [[InlineKeyboardButton("Yes", callback_data="renal_True")],
                [InlineKeyboardButton("No", callback_data="renal_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have renal impairment?", reply_markup=reply_markup)
    return GET_RENAL_IMPAIRMENT

async def get_renal_impairment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['renal_impairment'] = (query.data == "renal_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="hepatic_True")],
                [InlineKeyboardButton("No", callback_data="hepatic_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have hepatic impairment?", reply_markup=reply_markup)
    return GET_HEPATIC_IMPAIRMENT

async def get_hepatic_impairment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['hepatic_impairment'] = (query.data == "hepatic_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="critical_True")],
                [InlineKeyboardButton("No", callback_data="critical_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you critically ill?", reply_markup=reply_markup)
    return GET_CRITICAL_ILLNESS

async def get_critical_illness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['critical_illness'] = (query.data == "critical_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="steroid_True")],
                [InlineKeyboardButton("No", callback_data="steroid_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently using steroids?", reply_markup=reply_markup)
    return GET_STEROID_USE

async def get_steroid_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['steroid_use'] = (query.data == "steroid_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="anticoagulant_True")],
                [InlineKeyboardButton("No", callback_data="anticoagulant_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently taking anticoagulants (blood thinners)?", reply_markup=reply_markup)
    return GET_ANTICOAGULANT_USE

async def get_anticoagulant_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['anticoagulant_use'] = (query.data == "anticoagulant_True")
    keyboard = [[InlineKeyboardButton("Yes", callback_data="comorbidity_True")],
                [InlineKeyboardButton("No", callback_data="comorbidity_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have any other significant comorbidities (e.g., diabetes, heart failure, etc.)?", reply_markup=reply_markup)
    return GET_COMORBIDITY

async def get_comorbidity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['comorbidity'] = (query.data == "comorbidity_True")

    keyboard = [[InlineKeyboardButton("Yes", callback_data="ppi_use_True")],
                [InlineKeyboardButton("No", callback_data="ppi_use_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently taking a PPI (Proton Pump Inhibitor)?", reply_markup=reply_markup)
    return GET_PPI_USE

async def get_ppi_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    ppi_currently_used = (query.data == "ppi_use_True")
    context.user_data['patient_data']['ppi_currently_used'] = ppi_currently_used

    if ppi_currently_used:
        ppi_options = ["Pantoprazole", "Omeprazole", "Esomeprazole", "Rabeprazole"]
        keyboard = [[InlineKeyboardButton(ppi, callback_data=f"ppi_type_{ppi}")] for ppi in ppi_options]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Which PPI are you taking?", reply_markup=reply_markup)
        return GET_PPI_DOSE
    else:
        context.user_data['patient_data']['selected_ppi'] = 'None'
        context.user_data['patient_data']['ppi_dose'] = 0
        context.user_data['patient_data']['ppi_route'] = 'None'
        return await assess_and_send_result(update, context)

async def get_ppi_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected_ppi_type = query.data.split('_')[2]
    context.user_data['patient_data']['selected_ppi'] = selected_ppi_type

    if selected_ppi_type in ["Pantoprazole", "Esomeprazole"]:
        dose_options = ["20", "40", "80"]
    elif selected_ppi_type == "Omeprazole":
        dose_options = ["20", "40"]
    elif selected_ppi_type == "Rabeprazole":
        dose_options = ["10", "20"]
    else:
        dose_options = ["0", "20", "40", "80"]

    keyboard = [[InlineKeyboardButton(d, callback_data=f"ppi_dose_{d}")] for d in dose_options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"What is your {selected_ppi_type} dose (mg)?", reply_markup=reply_markup)
    return GET_PPI_ROUTE

async def get_ppi_route(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    try:
        ppi_dose_val = int(query.data.split('_')[2])
        context.user_data['patient_data']['ppi_dose'] = ppi_dose_val

        keyboard = [[InlineKeyboardButton("Oral", callback_data="ppi_route_Oral")],
                    [InlineKeyboardButton("IV", callback_data="ppi_route_IV")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("What is the PPI administration route?", reply_markup=reply_markup)
        return FINAL_ASSESSMENT
    except ValueError:
        await query.edit_message_text("Invalid PPI dose. Please choose from the options or enter a valid number.")
        return GET_PPI_DOSE

async def assess_and_send_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query and query.data.startswith('ppi_route_'):
        context.user_data['patient_data']['ppi_route'] = query.data.split('_')[2]
        await query.answer()

    patient_data = context.user_data['patient_data']
    risk_rating, recommendations = assess_risk_and_recommend(patient_data)

    response_text = (
        f"--- Risk Assessment Result ---\n"
        f"**Risk Rating:** {risk_rating}\n\n"
        f"**Recommendations:** {recommendations}\n\n"
        f"Type /start to begin a new assessment."
    )
    
    if query:
        await query.edit_message_text(response_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(response_text, parse_mode='Markdown')

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Assessment cancelled. Type /start to begin a new one.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("I am a health risk assessment bot. Use /start to begin an assessment.")

# --- Conversation Handler Setup ---
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
        GET_GENDER: [CallbackQueryHandler(get_gender, pattern='^gender_')],
        GET_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
        GET_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
        GET_NSAID_USE: [CallbackQueryHandler(get_nsaid_use, pattern='^nsaid_')],
        GET_NSAID_GROUP: [CallbackQueryHandler(get_nsaid_group, pattern='^nsaid_group_')],
        GET_SPECIFIC_NSAID: [CallbackQueryHandler(get_specific_nsaid, pattern='^specific_nsaid_')],
        GET_NSAID_DOSE: [CallbackQueryHandler(get_nsaid_dose, pattern='^nsaid_dose_')], # Handle NSAID dose selection

        GET_ANTIPLATELET_USE: [CallbackQueryHandler(get_antiplatelet_use, pattern='^antiplatelet_')],
        GET_HISTORY_PEPTIC_ULCER: [CallbackQueryHandler(get_history_peptic_ulcer, pattern='^ulcer_')],
        GET_GI_BLEED_RISK: [CallbackQueryHandler(get_gi_bleed_risk, pattern='^gib_risk_')],
        GET_CARDIO_RISK: [CallbackQueryHandler(get_cardio_risk, pattern='^cvd_risk_')],
        GET_H_PYLORI: [CallbackQueryHandler(get_h_pylori, pattern='^hpylori_')],
        GET_RENAL_IMPAIRMENT: [CallbackQueryHandler(get_renal_impairment, pattern='^renal_')],
        GET_HEPATIC_IMPAIRMENT: [CallbackQueryHandler(get_hepatic_impairment, pattern='^hepatic_')],
        GET_CRITICAL_ILLNESS: [CallbackQueryHandler(get_critical_illness, pattern='^critical_')],
        GET_STEROID_USE: [CallbackQueryHandler(get_steroid_use, pattern='^steroid_')],
        GET_ANTICOAGULANT_USE: [CallbackQueryHandler(get_anticoagulant_use, pattern='^anticoagulant_')],
        GET_COMORBIDITY: [CallbackQueryHandler(get_comorbidity, pattern='^comorbidity_')],
        GET_PPI_USE: [CallbackQueryHandler(get_ppi_use, pattern='^ppi_use_')],
        GET_PPI_DOSE: [CallbackQueryHandler(get_ppi_dose, pattern='^ppi_type_')],
        GET_PPI_ROUTE: [CallbackQueryHandler(get_ppi_route, pattern='^ppi_dose_')],
        FINAL_ASSESSMENT: [CallbackQueryHandler(assess_and_send_result, pattern='^ppi_route_')],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)
application.add_handler(CommandHandler("help", help_command))

# --- FastAPI Webhook Setup ---
app = FastAPI()

# This endpoint is for Vercel to check if the app is alive
@app.get("/")
async def root():
    return Response(content="Telegram Bot is alive!", media_type="text/plain")

# This is the main webhook endpoint where Telegram sends updates
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        # Get the JSON body from the incoming request
        update_json = await request.json()
        # Parse the JSON into a Telegram Update object
        update = Update.de_json(update_json, application.bot)

        # Process the update with the Application (non-blocking)
        # Use put_nowait and create_task for async webhook processing
        # Ensure application is initialized, this happens automatically on first request to a hot lambda
        await application.process_update(update)

        return Response(content="OK", status_code=200)
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        # Return a non-200 status code to Telegram if there's an error
        raise HTTPException(status_code=500, detail=str(e))

