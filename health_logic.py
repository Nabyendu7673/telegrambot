# health_logic.py

def calculate_bmi(weight_kg, height_cm):
    """Calculates Body Mass Index (BMI)."""
    if height_cm <= 0:
        return 0.0
    return weight_kg / ((height_cm / 100) ** 2)

# --- DIRECTLY FROM YOUR FINAL.PY SNIPPET: NSAID GROUPS WITH BASE RISK ---
# This dictionary structure comes directly from your final.py's nsaid_groups.
# The last value in the tuple (index 3) is the 'nsaid_base_risk'.
nsaid_groups = {
    "Propionic acid derivatives (Profens)": {
        "Ibuprofen": ([0, 200, 400, 600, 800, 2400], "Usual: 200–600 mg; Max: 2400 mg/day", 2400, 3),
        "Naproxen": ([0, 250, 375, 500, 1000], "Usual: 250–500 mg; Max: 1000 mg/day", 1000, 6),
        "Ketoprofen": ([0, 50, 100, 200], "Usual: 50–100 mg; Max: 200 mg/day", 200, 4),
        "Flurbiprofen": ([0, 50, 100, 150, 300], "Usual: 50–150 mg; Max: 300 mg/day", 300, 3)
    },
    "Acetic acid derivatives": {
        "Indomethacin": ([0, 25, 50, 75, 200], "Usual: 25–50 mg; Max: 200 mg/day", 200, 5),
        "Diclofenac": ([0, 25, 50, 75, 100, 150], "Usual: 50–75 mg; Max: 150 mg/day", 150, 4),
        "Etodolac": ([0, 200, 300, 400, 1000], "Usual: 200–400 mg; Max: 1000 mg/day", 1000, 3),
        "Ketorolac": ([0, 10, 20, 30, 120], "Usual: 10–30 mg; Max: 120 mg/day", 120, 4)
    },
    "Enolic acid (Oxicam) derivatives": {
        "Piroxicam": ([0, 10, 20], "Usual: 10–20 mg; Max: 20 mg/day", 20, 4),
        "Meloxicam": ([0, 7.5, 15], "Usual: 7.5–15 mg; Max: 15 mg/day", 15, 2)
    },
    "Selective COX-2 inhibitors": {
        "Celecoxib": ([0, 100, 200, 400], "Usual: 100–200 mg; Max: 400 mg/day", 400, 1)
    },
    "Non-NSAID Analgesics": {
        "Paracetamol": ([0, 500, 1000, 2000, 4000], "Usual: 500–1000 mg; Max: 4000 mg/day", 4000, 0)
    },
    "None": {"None": ([0], "", 0, 0)} # Important to have a 'None' option if no NSAID is selected
}

# --- INDICATION WEIGHTS DERIVED FROM YOUR FINAL.PY'S INDICATION LISTS ---
# These keys are directly from your gi_indications, nsaid_ap_indications, and other_indications.
# The *values* (weights) are assigned based on typical risk levels.
# YOU MUST VERIFY AND ADJUST THESE WEIGHTS to match any specific numerical values
# used in your original Streamlit application's risk calculation.
indication_weights = {
    # GI Indications (from final.py snippet)
    "Non-variceal bleeding": 3,
    "Dyspepsia": 1,
    "GERD & complications": 2,
    "H pylori infection": 2,
    "Peptic ulcer treatment": 3,
    "Zollinger-Ellison syndrome": 3,

    # NSAID/Antiplatelet Indications (from final.py snippet)
    "Prevent NSAID ulcers": 2,
    "NSAID & ulcer/GIB history": 3,
    "NSAID & age > 60": 2,
    "NSAID + cortico/antiplatelet/anticoag": 3,
    "Prophylaxis in high risk antiplatelet users": 2,
    "Antiplatelet & ulcer/GIB history": 3,
    "Antiplatelet + age > 60 or dyspepsia/GERD": 2,
    "Antiplatelet + cortico/NSAID/anticoag": 3,

    # Other Indications (from final.py snippet)
    "Stress ulcer prophylaxis": 2,
    "Coagulopathy (platelet < 50k, INR ≥ 1.5)": 2,
    "Mechanical ventilation > 48h": 2,

    # These are general flags from the bot's questions, which might map to the above detailed indications
    # or contribute directly. Ensure consistent naming and weighting with your final.py.
    # If a bot question like "History of Peptic Ulcer" maps exactly to "Peptic ulcer treatment" above,
    # then you'd use that specific key in the scoring logic below.
    # Adding (Bot Question) suffix for clarity where direct mapping isn't 1:1 with precise indications
    "History of Peptic Ulcer (Bot Question)": 3,
    "GI Bleed Risk Factors (Bot Question)": 2,
    "Cardiovascular Disease Risk (Bot Question)": 1,
    "H. pylori positive (Bot Question)": 2,
    "Renal Impairment (Bot Question)": 1,
    "Hepatic Impairment (Bot Question)": 2,
    "Critical Illness (Bot Question)": 3, # Higher weight
    "Steroid Use (Bot Question)": 2,
    "Comorbidity (Bot Question)": 1,
    "Anticoagulant Use (Bot Question)": 3 # To capture the boolean flag if used in score calc
}


def get_nsaid_score(nsaid_use_flag, age, selected_nsaid_group, selected_nsaid, nsaid_dose):
    """
    Calculates NSAID risk score using the selected NSAID type and dose.
    This logic now fully leverages your `nsaid_groups` data from `final.py`.
    """
    score = 0
    if nsaid_use_flag and selected_nsaid_group != "None" and selected_nsaid != "None" and nsaid_dose > 0:
        nsaid_info = nsaid_groups.get(selected_nsaid_group, {}).get(selected_nsaid)
        if nsaid_info:
            _, _, nsaid_max_dose, nsaid_base_risk = nsaid_info
            score += nsaid_base_risk # Add the base risk for the specific NSAID

            # Implement dose-dependent risk from your final.py
            # Assuming your final.py had logic for high dose, e.g.:
            if nsaid_dose > (nsaid_max_dose * 0.75): # Example threshold for high dose risk
                score += 2 # Additional risk for high dose

            # Apply age-related NSAID risk if present in final.py's specific conditions
            # "NSAID & age > 60" is an indication, so it will be handled in `indication_score` below.
    return score

def get_antiplatelet_score(antiplatelet_use_flag, age):
    """Calculates antiplatelet risk score, including age if relevant from final.py."""
    score = 0
    if antiplatelet_use_flag:
        score += 3 # Base risk for any antiplatelet use
        # "Antiplatelet + age > 60 or dyspepsia/GERD" is an indication, handled in `indication_score`
    return score

def get_anticoagulant_score(anticoagulant_use_flag):
    """Calculates anticoagulant risk score."""
    score = 0
    if anticoagulant_use_flag:
        score += 4 # Generally higher risk for anticoagulants
        # "Coagulopathy (platelet < 50k, INR ≥ 1.5)" is an indication, handled in `indication_score`
    return score

def get_ppi_gastroprotection(ppi_dose_mg, ppi_route, nsaid_flag, antiplatelet_flag, anticoagulant_flag):
    """Calculates PPI gastroprotection score reduction based on dose and route, mimicking final.py logic."""
    reduction = 0
    # PPI protection is usually relevant when other high-risk meds are present
    if (nsaid_flag or antiplatelet_flag or anticoagulant_flag) and ppi_dose_mg > 0 and ppi_route != 'None':
        if ppi_route == "Oral":
            if ppi_dose_mg >= 20: # Assumed standard effective oral dose
                reduction = -2 # Example reduction for effective PPI use
        elif ppi_route == "IV":
            if ppi_dose_mg >= 40: # Assumed standard effective IV dose
                reduction = -3 # Example reduction for effective PPI use
    return reduction


def assess_risk_and_recommend(patient_data):
    """
    Assesses the patient's GI risk and provides recommendations based on collected data.
    This function's logic and thresholds are designed to closely match your final.py.
    """
    age = patient_data.get('age', 0)
    nsaid_use = patient_data.get('nsaid_use', False) # General NSAID use True/False from bot
    antiplatelet_use = patient_data.get('antiplatelet_use', False)
    anticoagulant_use = patient_data.get('anticoagulant_use', False)

    # Specific NSAID details collected by the bot (new inputs)
    selected_nsaid_group = patient_data.get('selected_nsaid_group', 'None')
    selected_nsaid = patient_data.get('selected_nsaid', 'None')
    nsaid_dose = patient_data.get('nsaid_dose', 0)

    # Boolean flags from bot's detailed questions about indications
    history_peptic_ulcer = patient_data.get('history_peptic_ulcer', False)
    gi_bleed_risk_factors = patient_data.get('gi_bleed_risk_factors', False) # Bot question on other GI bleed risks
    cardiovascular_disease_risk = patient_data.get('cardiovascular_disease_risk', False)
    h_pylori_positive = patient_data.get('h_pylori_positive', False) if patient_data.get('h_pylori_positive') is not None else False
    renal_impairment = patient_data.get('renal_impairment', False)
    hepatic_impairment = patient_data.get('hepatic_impairment', False)
    critical_illness = patient_data.get('critical_illness', False)
    steroid_use = patient_data.get('steroid_use', False)
    comorbidity = patient_data.get('comorbidity', False)

    # PPI details from user input
    selected_ppi = patient_data.get('selected_ppi', 'None')
    ppi_dose = patient_data.get('ppi_dose', 0)
    ppi_route = patient_data.get('ppi_route', 'None')


    # --- RECONSTRUCTED SCORING LOGIC BASED ON FINAL.PY'S STRUCTURE AND BOT'S INPUTS ---

    # Medication-related scores
    nsaid_score = get_nsaid_score(nsaid_use, age, selected_nsaid_group, selected_nsaid, nsaid_dose)
    antiplatelet_score = get_antiplatelet_score(antiplatelet_use, age)
    anticoagulant_score = get_anticoagulant_score(anticoagulant_use)

    # Summing indication-based scores from bot questions, mapping to your `indication_weights`
    indication_score = 0
    # GI Indications
    if history_peptic_ulcer:
        indication_score += indication_weights.get("Peptic ulcer treatment", 0) # Assuming direct map
    if h_pylori_positive:
        indication_score += indication_weights.get("H pylori infection", 0)
    # Add other GI conditions from your final.py if collected by bot questions

    # NSAID/Antiplatelet specific indications (these are from your final.py's lists, mapping to bot questions)
    if nsaid_use and history_peptic_ulcer: # If NSAID used AND history of ulcer/GIB
        indication_score += indication_weights.get("NSAID & ulcer/GIB history", 0)
    if nsaid_use and age > 60:
        indication_score += indication_weights.get("NSAID & age > 60", 0)
    if antiplatelet_use and history_peptic_ulcer: # If AP used AND history of ulcer/GIB
        indication_score += indication_weights.get("Antiplatelet & ulcer/GIB history", 0)
    if antiplatelet_use and age > 60: # Simplified, assuming dyspepsia/GERD not asked specifically
        indication_score += indication_weights.get("Antiplatelet + age > 60 or dyspepsia/GERD", 0)
    # NSAID/AP with cortico/antiplatelet/anticoag - these are separate questions in bot, so sum them
    if nsaid_use and (steroid_use or antiplatelet_use or anticoagulant_use):
        indication_score += indication_weights.get("NSAID + cortico/antiplatelet/anticoag", 0)
    if antiplatelet_use and (steroid_use or nsaid_use or anticoagulant_use):
         indication_score += indication_weights.get("Antiplatelet + cortico/NSAID/anticoag", 0)


    # Other Indications (from final.py lists, mapped to bot questions)
    if critical_illness:
        indication_score += indication_weights.get("Stress ulcer prophylaxis", 0) # Assuming critical illness implies need for SUP
    if anticoagulant_use: # If anticoagulant use, may contribute to coagulopathy risk
        indication_score += indication_weights.get("Coagulopathy (platelet < 50k, INR ≥ 1.5)", 0) # Adjust if you have a separate question for this
    if renal_impairment:
        indication_score += indication_weights.get("Renal Impairment", 0)
    if hepatic_impairment:
        indication_score += indication_weights.get("Hepatic Impairment", 0)
    if steroid_use:
        indication_score += indication_weights.get("Steroid Use", 0)
    if comorbidity:
        indication_score += indication_weights.get("Comorbidity", 0)
    if cardiovascular_disease_risk:
        indication_score += indication_weights.get("Cardiovascular Disease Risk", 0)
    if gi_bleed_risk_factors: # General GI bleed risk flag
        indication_score += indication_weights.get("GI Bleed Risk Factors", 0)
    # Add any other indications from your final.py that are triggered by bot's boolean flags


    total_medication_risk = nsaid_score + antiplatelet_score + anticoagulant_score

    # Triple therapy combination check
    triple_combo_bonus = 0
    if nsaid_use and antiplatelet_use and anticoagulant_use:
        triple_combo_bonus = 2 # Example bonus from your final.py. Adjust if different.

    # Overall high risk flag (based on medication and indications)
    high_risk_flag_bonus = 0
    # Your final.py likely has thresholds for high risk. Example:
    if total_medication_risk >= 6 or indication_score >= 6 or history_peptic_ulcer or critical_illness:
        high_risk_flag_bonus = 1 # Example bonus. Adjust if different.

    # PPI gastroprotection score reduction
    ppi_reduction = get_ppi_gastroprotection(ppi_dose, ppi_route, nsaid_use, antiplatelet_use, anticoagulant_use)

    # Final Risk Score Calculation - Mimicking the cumulative nature of your Streamlit app
    # THIS FORMULA IS THE MOST CRITICAL TO MATCH YOUR FINAL.PY EXACTLY.
    risk_score = total_medication_risk + indication_score + triple_combo_bonus + high_risk_flag_bonus + ppi_reduction

    # --- END OF RECONSTRUCTED SCORING LOGIC ---


    # --- RISK INTERPRETATION AND RECOMMENDATIONS (FROM YOUR FINAL.PY) ---
    risk_rating_text = "N/A"
    recommendations_text = "No specific recommendations available."

    # Using the exact thresholds and texts from your final.py snippet's example output.
    if risk_score >= 10:
        risk_rating_text = "🔴 Very High Risk – Continue Current PPI Therapy"
        recommendations_text = (
            "Review risk factors every 3 months. Consider GI specialist consultation. "
            "Monitor for long-term PPI complications. Full guidelines apply."
        )
    elif risk_score >= 7:
        risk_rating_text = "🟠 High Risk – Optimize PPI Therapy"
        recommendations_text = (
            "Reassess in 4-6 weeks. Monitor for breakthrough symptoms. "
            "Consider dose adjustment based on full clinical picture."
        )
    elif 4 <= risk_score < 7:
        risk_rating_text = "🟡 Moderate Risk – Consider Step-down Therapy"
        recommendations_text = (
            "Consider gradual dose reduction. Implement step-down protocol. "
            "Monitor for symptom recurrence. Schedule follow-up in 4 weeks."
        )
    else: # risk_score < 4
        risk_rating_text = "🟢 Low Risk Assessment – PPI Deprescribing Protocol Initiation"
        recommendations_text = (
            "Implement gradual dose reduction protocol. Consider step-down to on-demand therapy. "
            "Assess for symptom recurrence. Initial review: 2 weeks post-initiation."
        )

    return risk_rating_text, recommendations_text

