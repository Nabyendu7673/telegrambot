# main.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# IMPORTANT: Explicitly import ContextTypes for python-telegram-bot v20.0+
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ConversationHandler, ContextTypes
import logging
from health_logic import calculate_bmi, assess_risk_and_recommend # Import from your health_logic.py

# Your Telegram Bot API Token
# Replace with the token you get from BotFather. KEEP THIS SECURE!
BOT_TOKEN = '7329446852:AAEcaewwKxlLO-w3vniZsTg4lZyBzlWZTB8'

# Enable logging to see what the bot is doing
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states for the conversation using constants for clarity
(
    GET_AGE, GET_GENDER, GET_WEIGHT, GET_HEIGHT, GET_NSAID_USE, GET_ANTIPLATELET_USE,
    GET_HISTORY_PEPTIC_ULCER, GET_GI_BLEED_RISK, GET_CARDIO_RISK, GET_H_PYLORI,
    GET_RENAL_IMPAIRMENT, GET_HEPATIC_IMPAIRMENT, GET_CRITICAL_ILLNESS,
    GET_STEROID_USE, GET_ANTICOAGULANT_USE, GET_COMORBIDITY, GET_PPI_USE,
    GET_PPI_DOSE, GET_PPI_ROUTE, FINAL_ASSESSMENT # Renamed to be more explicit for the last step
) = range(20) # Total 20 states from 0 to 19

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a welcome message and starts the conversation."""
    await update.message.reply_text(
        "Hello! I can help assess your health risk. Let's start. What is your age?"
    )
    context.user_data['patient_data'] = {} # Initialize an empty dictionary to store user's data
    return GET_AGE # Transition to the GET_AGE state

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores age and asks for gender."""
    try:
        age = int(update.message.text)
        if not (0 <= age <= 120): # Validate age to be within a reasonable range
            raise ValueError("Invalid age")
        context.user_data['patient_data']['age'] = age # Store age
        
        # Prepare inline keyboard for gender selection
        keyboard = [
            [InlineKeyboardButton("Male", callback_data="gender_Male")],
            [InlineKeyboardButton("Female", callback_data="gender_Female")],
            [InlineKeyboardButton("Other", callback_data="gender_Other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("What is your gender?", reply_markup=reply_markup)
        return GET_GENDER # Transition to GET_GENDER state
    except ValueError:
        await update.message.reply_text("Please enter a valid age (e.g., 30).")
        return GET_AGE # Stay in GET_AGE state for re-entry

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores gender and asks for weight."""
    query = update.callback_query # Get the callback query from button press
    await query.answer() # Acknowledge the callback query
    context.user_data['patient_data']['gender'] = query.data.split('_')[1] # Store selected gender (e.g., 'Male')
    await query.edit_message_text(f"Your gender: {query.data.split('_')[1]}. Please enter your weight in kg (e.g., 70.5).")
    return GET_WEIGHT # Transition to GET_WEIGHT state

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores weight and asks for height."""
    try:
        weight_kg = float(update.message.text)
        context.user_data['patient_data']['weight_kg'] = weight_kg # Store weight
        await update.message.reply_text("Please enter your height in cm (e.g., 175).")
        return GET_HEIGHT # Transition to GET_HEIGHT state
    except ValueError:
        await update.message.reply_text("Please enter a valid weight in kg (e.g., 65.2).")
        return GET_WEIGHT # Stay in GET_WEIGHT state

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores height, calculates BMI, and asks about NSAID use."""
    try:
        height_cm = float(update.message.text)
        context.user_data['patient_data']['height_cm'] = height_cm # Store height

        # Calculate BMI using the imported function
        bmi = calculate_bmi(context.user_data['patient_data']['weight_kg'], height_cm)
        context.user_data['patient_data']['bmi'] = bmi # Store BMI
        await update.message.reply_text(f"Your BMI is: {bmi:.2f}.")

        # Ask about NSAID use with inline keyboard
        keyboard = [[InlineKeyboardButton("Yes", callback_data="nsaid_True")],
                    [InlineKeyboardButton("No", callback_data="nsaid_False")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Are you currently taking NSAIDs (Non-Steroidal Anti-Inflammatory Drugs)?", reply_markup=reply_markup)
        return GET_NSAID_USE # Transition to GET_NSAID_USE state
    except ValueError:
        await update.message.reply_text("Please enter a valid height in cm (e.g., 168.5).")
        return GET_HEIGHT # Stay in GET_HEIGHT state

async def get_nsaid_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores NSAID use and asks about antiplatelet use."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['nsaid_use'] = (query.data == "nsaid_True") # Store boolean
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="antiplatelet_True")],
                [InlineKeyboardButton("No", callback_data="antiplatelet_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently taking antiplatelet medications (e.g., Aspirin, Clopidogrel)?", reply_markup=reply_markup)
    return GET_ANTIPLATELET_USE # Transition to GET_ANTIPLATELET_USE state

async def get_antiplatelet_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores antiplatelet use and asks about history of peptic ulcer."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['antiplatelet_use'] = (query.data == "antiplatelet_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="ulcer_True")],
                [InlineKeyboardButton("No", callback_data="ulcer_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have a history of peptic ulcer?", reply_markup=reply_markup)
    return GET_HISTORY_PEPTIC_ULCER # Transition to GET_HISTORY_PEPTIC_ULCER state

async def get_history_peptic_ulcer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores history of peptic ulcer and asks about GI bleed risk factors."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['history_peptic_ulcer'] = (query.data == "ulcer_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="gib_risk_True")],
                [InlineKeyboardButton("No", callback_data="gib_risk_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have other GI bleed risk factors (e.g., chronic liver disease, inflammatory bowel disease)?", reply_markup=reply_markup)
    return GET_GI_BLEED_RISK # Transition to GET_GI_BLEED_RISK state

async def get_gi_bleed_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores GI bleed risk factors and asks about cardiovascular disease risk."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['gi_bleed_risk_factors'] = (query.data == "gib_risk_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="cvd_risk_True")],
                [InlineKeyboardButton("No", callback_data="cvd_risk_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have significant cardiovascular disease risk factors?", reply_markup=reply_markup)
    return GET_CARDIO_RISK # Transition to GET_CARDIO_RISK state

async def get_cardio_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores cardiovascular disease risk and asks about H. pylori status."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['cardiovascular_disease_risk'] = (query.data == "cvd_risk_True")
    
    keyboard = [[InlineKeyboardButton("Positive", callback_data="hpylori_True")],
                [InlineKeyboardButton("Negative", callback_data="hpylori_False")],
                [InlineKeyboardButton("Unknown", callback_data="hpylori_Unknown")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you H. pylori positive?", reply_markup=reply_markup)
    return GET_H_PYLORI # Transition to GET_H_PYLORI state

async def get_h_pylori(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores H. pylori status and asks about renal impairment."""
    query = update.callback_query
    await query.answer()
    hp_status = query.data.split('_')[1]
    if hp_status == 'True':
        context.user_data['patient_data']['h_pylori_positive'] = True
    elif hp_status == 'False':
        context.user_data['patient_data']['h_pylori_positive'] = False
    else: # Unknown or not applicable, treat as False for direct boolean usage in health_logic
        context.user_data['patient_data']['h_pylori_positive'] = False 

    keyboard = [[InlineKeyboardButton("Yes", callback_data="renal_True")],
                [InlineKeyboardButton("No", callback_data="renal_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have renal impairment?", reply_markup=reply_markup)
    return GET_RENAL_IMPAIRMENT # Transition to GET_RENAL_IMPAIRMENT state

async def get_renal_impairment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores renal impairment status and asks about hepatic impairment."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['renal_impairment'] = (query.data == "renal_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="hepatic_True")],
                [InlineKeyboardButton("No", callback_data="hepatic_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have hepatic impairment?", reply_markup=reply_markup)
    return GET_HEPATIC_IMPAIRMENT # Transition to GET_HEPATIC_IMPAIRMENT state

async def get_hepatic_impairment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores hepatic impairment status and asks about critical illness."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['hepatic_impairment'] = (query.data == "hepatic_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="critical_True")],
                [InlineKeyboardButton("No", callback_data="critical_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you critically ill?", reply_markup=reply_markup)
    return GET_CRITICAL_ILLNESS # Transition to GET_CRITICAL_ILLNESS state

async def get_critical_illness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores critical illness status and asks about steroid use."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['critical_illness'] = (query.data == "critical_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="steroid_True")],
                [InlineKeyboardButton("No", callback_data="steroid_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently using steroids?", reply_markup=reply_markup)
    return GET_STEROID_USE # Transition to GET_STEROID_USE state

async def get_steroid_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores steroid use and asks about anticoagulant use."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['steroid_use'] = (query.data == "steroid_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="anticoagulant_True")],
                [InlineKeyboardButton("No", callback_data="anticoagulant_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently taking anticoagulants (blood thinners)?", reply_markup=reply_markup)
    return GET_ANTICOAGULANT_USE # Transition to GET_ANTICOAGULANT_USE state

async def get_anticoagulant_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores anticoagulant use and asks about comorbidity."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['anticoagulant_use'] = (query.data == "anticoagulant_True")
    
    keyboard = [[InlineKeyboardButton("Yes", callback_data="comorbidity_True")],
                [InlineKeyboardButton("No", callback_data="comorbidity_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Do you have any other significant comorbidities (e.g., diabetes, heart failure, etc.)?", reply_markup=reply_markup)
    return GET_COMORBIDITY # Transition to GET_COMORBIDITY state

async def get_comorbidity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores comorbidity and asks about PPI use."""
    query = update.callback_query
    await query.answer()
    context.user_data['patient_data']['comorbidity'] = (query.data == "comorbidity_True")

    # Now, ask about PPI use
    keyboard = [[InlineKeyboardButton("Yes", callback_data="ppi_use_True")],
                [InlineKeyboardButton("No", callback_data="ppi_use_False")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Are you currently taking a PPI (Proton Pump Inhibitor)?", reply_markup=reply_markup)
    return GET_PPI_USE # Transition to GET_PPI_USE state

async def get_ppi_use(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores PPI use and asks for PPI type if applicable."""
    query = update.callback_query
    await query.answer()
    ppi_currently_used = (query.data == "ppi_use_True")
    context.user_data['patient_data']['ppi_currently_used'] = ppi_currently_used

    if ppi_currently_used:
        # Offer PPI options from your final.py or common ones
        ppi_options = ["Pantoprazole", "Omeprazole", "Esomeprazole", "Rabeprazole"]
        keyboard = [[InlineKeyboardButton(ppi, callback_data=f"ppi_type_{ppi}")] for ppi in ppi_options]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Which PPI are you taking?", reply_markup=reply_markup)
        return GET_PPI_DOSE # Transition to GET_PPI_DOSE state (to get type and then ask dose)
    else:
        # If no PPI, set defaults and directly proceed to final assessment
        context.user_data['patient_data']['selected_ppi'] = 'None'
        context.user_data['patient_data']['ppi_dose'] = 0
        context.user_data['patient_data']['ppi_route'] = 'None'
        # Call the final assessment directly, as no more PPI questions are needed
        return await assess_and_send_result(update, context)

async def get_ppi_dose(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores selected PPI type and asks for dose."""
    query = update.callback_query
    await query.answer()
    selected_ppi_type = query.data.split('_')[2] # Extract PPI type from callback data
    context.user_data['patient_data']['selected_ppi'] = selected_ppi_type

    # Provide dose options based on the selected PPI type, similar to final.py
    if selected_ppi_type in ["Pantoprazole", "Esomeprazole"]:
        dose_options = ["20", "40", "80"]
    elif selected_ppi_type == "Omeprazole":
        dose_options = ["20", "40"]
    elif selected_ppi_type == "Rabeprazole":
        dose_options = ["10", "20"]
    else:
        dose_options = ["0", "20", "40", "80"] # Fallback options

    keyboard = [[InlineKeyboardButton(d, callback_data=f"ppi_dose_{d}")] for d in dose_options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"What is your {selected_ppi_type} dose (mg)?", reply_markup=reply_markup)
    return GET_PPI_ROUTE # Transition to GET_PPI_ROUTE state

async def get_ppi_route(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores PPI dose and asks for route."""
    query = update.callback_query
    await query.answer()
    try:
        ppi_dose_val = int(query.data.split('_')[2]) # Extract PPI dose
        context.user_data['patient_data']['ppi_dose'] = ppi_dose_val

        # Ask for administration route
        keyboard = [[InlineKeyboardButton("Oral", callback_data="ppi_route_Oral")],
                    [InlineKeyboardButton("IV", callback_data="ppi_route_IV")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("What is the PPI administration route?", reply_markup=reply_markup)
        return FINAL_ASSESSMENT # Transition to FINAL_ASSESSMENT state, awaiting route selection
    except ValueError:
        await query.edit_message_text("Invalid PPI dose. Please choose from the options or enter a valid number.")
        return GET_PPI_DOSE # Stay in GET_PPI_DOSE for re-entry

async def assess_and_send_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Performs the final risk assessment and sends the result to the user."""
    query = update.callback_query # Get the callback query for route selection

    # Ensure ppi_route is stored if the function is called via callback (from route selection)
    if query and query.data.startswith('ppi_route_'):
        context.user_data['patient_data']['ppi_route'] = query.data.split('_')[2]
        await query.answer() # Acknowledge the callback

    patient_data = context.user_data['patient_data'] # Retrieve all collected patient data

    # Call the core logic function to get risk rating and recommendations
    risk_rating, recommendations = assess_risk_and_recommend(patient_data)

    # Format the response message
    response_text = (
        f"--- Risk Assessment Result ---\n"
        f"**Risk Rating:** {risk_rating}\n\n"
        f"**Recommendations:** {recommendations}\n\n"
        f"Type /start to begin a new assessment."
    )
    
    # Send the response. If it was a button click, edit the message; otherwise, send new.
    if query:
        await query.edit_message_text(response_text, parse_mode='Markdown')
    else:
        # This branch would typically be for direct message triggers, less common in this conversation flow
        await update.message.reply_text(response_text, parse_mode='Markdown')

    return ConversationHandler.END # End the conversation

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Assessment cancelled. Type /start to begin a new one."
    )
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /help is issued."""
    await update.message.reply_text("I am a health risk assessment bot. Use /start to begin an assessment.")

def main() -> None:
    """Starts the bot."""
    # Create the Application and pass your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Define the ConversationHandler for the multi-step conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)], # Entry point: /start command
        states={
            GET_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GET_GENDER: [CallbackQueryHandler(get_gender, pattern='^gender_')],
            GET_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            GET_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            GET_NSAID_USE: [CallbackQueryHandler(get_nsaid_use, pattern='^nsaid_')],
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
            FINAL_ASSESSMENT: [CallbackQueryHandler(assess_and_send_result, pattern='^ppi_route_')], # Final trigger for assessment
        },
        fallbacks=[CommandHandler("cancel", cancel)], # Allows user to cancel at any point
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command)) # Add a /help command

    # Start the bot polling for updates. Includes error handling.
    try:
        logger.info("Starting bot polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("Bot polling stopped.")
    except Exception as e:
        logger.error(f"Bot failed to start or encountered an error during polling: {e}", exc_info=True)


if __name__ == "__main__":
    main()