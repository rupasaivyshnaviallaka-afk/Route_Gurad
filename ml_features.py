import joblib
import numpy as np
import pandas as pd
from datetime import datetime
import os

# Load models (do this once when server starts)
MODEL_PATH = 'ml_models'

delay_model = joblib.load(f'{MODEL_PATH}/delay_classifier.pkl')
eta_model = joblib.load(f'{MODEL_PATH}/eta_regressor.pkl')
traffic_model = joblib.load(f'{MODEL_PATH}/traffic_model.pkl')
weather_encoder = joblib.load(f'{MODEL_PATH}/weather_encoder.pkl')

def predict_delay_probability(distance_km, weather_type, hour_of_day=None):
    """
    Predict probability of delay (>30min)
    Returns: probability (0-1), risk_level
    """
    if hour_of_day is None:
        hour_of_day = datetime.now().hour
    
    # Calculate rush hour
    is_rush_hour = 1 if (7 <= hour_of_day <= 10 or 17 <= hour_of_day <= 20) else 0
    
    # Get current day of week (1=Monday to 7=Sunday)
    day_of_week = datetime.now().isoweekday()
    
    # Encode weather
    try:
        weather_encoded = weather_encoder.transform([weather_type])[0]
    except:
        # Default to sunny if unknown
        weather_encoded = weather_encoder.transform(['sunny'])[0]
    
    # Create feature array
    features = np.array([[distance_km, hour_of_day, day_of_week, is_rush_hour, weather_encoded]])
    
    # Get prediction (0 or 1)
    prediction = delay_model.predict(features)[0]
    
    # Get probability
    probabilities = delay_model.predict_proba(features)[0]
    delay_prob = probabilities[1] if len(probabilities) > 1 else float(prediction)
    
    risk_level = "HIGH" if delay_prob > 0.6 else "MEDIUM" if delay_prob > 0.3 else "LOW"
    
    return {
        "delay_probability": round(float(delay_prob), 3),
        "risk_level": risk_level,
        "will_be_delayed": bool(prediction)
    }

def predict_eta(distance_km, weather_type, hour_of_day=None):
    """
    Predict expected travel time in minutes
    """
    if hour_of_day is None:
        hour_of_day = datetime.now().hour
    
    is_rush_hour = 1 if (7 <= hour_of_day <= 10 or 17 <= hour_of_day <= 20) else 0
    day_of_week = datetime.now().isoweekday()
    
    try:
        weather_encoded = weather_encoder.transform([weather_type])[0]
    except:
        weather_encoded = weather_encoder.transform(['sunny'])[0]
    
    features = np.array([[distance_km, hour_of_day, day_of_week, is_rush_hour, weather_encoded]])
    
    eta_minutes = eta_model.predict(features)[0]
    
    # Convert to hours and minutes
    hours = int(eta_minutes // 60)
    minutes = int(eta_minutes % 60)
    
    return {
        "total_minutes": round(float(eta_minutes), 0),
        "formatted": f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m",
        "hours": hours,
        "minutes": minutes
    }

def predict_traffic_severity(distance_km, weather_type, hour_of_day=None):
    """
    Predict traffic severity
    Returns: 0=Light, 1=Moderate, 2=Heavy
    """
    if hour_of_day is None:
        hour_of_day = datetime.now().hour
    
    is_rush_hour = 1 if (7 <= hour_of_day <= 10 or 17 <= hour_of_day <= 20) else 0
    day_of_week = datetime.now().isoweekday()
    
    try:
        weather_encoded = weather_encoder.transform([weather_type])[0]
    except:
        weather_encoded = weather_encoder.transform(['sunny'])[0]
    
    features = np.array([[distance_km, hour_of_day, day_of_week, is_rush_hour, weather_encoded]])
    
    severity = traffic_model.predict(features)[0]
    
    severity_map = {
        0: {"level": "LIGHT", "color": "green", "emoji": "🟢", "description": "Clear road"},
        1: {"level": "MODERATE", "color": "yellow", "emoji": "🟡", "description": "Moderate traffic"},
        2: {"level": "HEAVY", "color": "red", "emoji": "🔴", "description": "Heavy traffic"}
    }
    
    return severity_map[severity]

def get_complete_analysis(distance_km, weather_type, hour_of_day=None):
    """
    Get complete ML analysis for a route
    """
    delay_info = predict_delay_probability(distance_km, weather_type, hour_of_day)
    eta_info = predict_eta(distance_km, weather_type, hour_of_day)
    traffic_info = predict_traffic_severity(distance_km, weather_type, hour_of_day)
    
    # Generate smart recommendation
    recommendation = "Proceed as planned"
    if delay_info['delay_probability'] > 0.6:
        recommendation = "⚠️ HIGH DELAY RISK - Consider alternate route or later departure"
    elif delay_info['delay_probability'] > 0.3:
        recommendation = "⚠️ Moderate delay risk - Add buffer time"
    
    return {
        "delay_prediction": delay_info,
        "eta_prediction": eta_info,
        "traffic_prediction": traffic_info,
        "recommendation": recommendation,
        "summary": f"{traffic_info['emoji']} {traffic_info['description']} | ETA: {eta_info['formatted']} | Delay risk: {delay_info['delay_probability']*100:.0f}%"
    }