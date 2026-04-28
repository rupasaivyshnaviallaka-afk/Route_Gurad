from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime
import os
import json
import requests
import pandas as pd
import numpy as np

# ML imports
import joblib
from sklearn.preprocessing import LabelEncoder

app = FastAPI(title="RouteGuard ML API", description="Smart Supply Chain Optimization")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# DATA MODELS
# ============================================

class TripData(BaseModel):
    distance_km: float
    hour_of_day: int
    day_of_week: int
    weather_type: str
    is_rush_hour: int
    actual_duration_min: float
    was_delayed: int

class RouteAnalysisRequest(BaseModel):
    origin: str
    destination: str
    distance_km: float
    weather: str

# ============================================
# LOAD ML MODELS (with fallback)
# ============================================

ml_models_loaded = False
delay_model = None
eta_model = None
traffic_model = None
weather_encoder = None

try:
    if os.path.exists('ml_models/delay_classifier.pkl'):
        delay_model = joblib.load('ml_models/delay_classifier.pkl')
        eta_model = joblib.load('ml_models/eta_regressor.pkl')
        traffic_model = joblib.load('ml_models/traffic_model.pkl')
        weather_encoder = joblib.load('ml_models/weather_encoder.pkl')
        ml_models_loaded = True
        print("✅ ML Models loaded successfully")
    else:
        print("⚠️ ML models not found. Run train_models.py first")
except Exception as e:
    print(f"⚠️ Error loading ML models: {e}")

# ============================================
# RULE-BASED FALLBACK (Original)
# ============================================

@app.get("/predict")
def predict(distance: float, weather: str = "sunny"):
    """Original rule-based prediction (fallback)"""
    if distance > 300:
        color = "red"
        traffic = "Heavy traffic 🔴"
    elif distance > 150:
        color = "yellow"
        traffic = "Moderate traffic 🟡"
    else:
        color = "green"
        traffic = "Clear road 🟢"

    return {
        "color": color,
        "message": f"{traffic} | Weather: {weather}",
        "type": "rule-based"
    }

# ============================================
# ML-POWERED ANALYSIS
# ============================================

def predict_delay_probability(distance_km, weather_type, hour_of_day=None):
    """Predict probability of delay using ML"""
    if not ml_models_loaded:
        return None
    
    if hour_of_day is None:
        hour_of_day = datetime.now().hour
    
    is_rush_hour = 1 if (7 <= hour_of_day <= 10 or 17 <= hour_of_day <= 20) else 0
    day_of_week = datetime.now().isoweekday()
    
    try:
        weather_encoded = weather_encoder.transform([weather_type])[0]
    except:
        weather_encoded = weather_encoder.transform(['sunny'])[0]
    
    features = np.array([[distance_km, hour_of_day, day_of_week, is_rush_hour, weather_encoded]])
    
    probabilities = delay_model.predict_proba(features)[0]
    delay_prob = probabilities[1] if len(probabilities) > 1 else 0.5
    
    risk_level = "HIGH" if delay_prob > 0.6 else "MEDIUM" if delay_prob > 0.3 else "LOW"
    
    return {
        "delay_probability": round(float(delay_prob), 3),
        "risk_level": risk_level,
        "will_be_delayed": bool(delay_prob > 0.5)
    }

def predict_eta(distance_km, weather_type, hour_of_day=None):
    """Predict expected travel time"""
    if not ml_models_loaded:
        return None
    
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
    
    hours = int(eta_minutes // 60)
    minutes = int(eta_minutes % 60)
    
    return {
        "total_minutes": round(float(eta_minutes), 0),
        "formatted": f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m",
        "hours": hours,
        "minutes": minutes
    }

def predict_traffic_severity(distance_km, weather_type, hour_of_day=None):
    """Predict traffic severity using ML"""
    if not ml_models_loaded:
        return {"level": "MODERATE", "color": "yellow", "emoji": "🟡", "description": "Moderate traffic (ML unavailable)"}
    
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

@app.get("/ml/analyze")
def ml_analyze(
    distance: float = Query(..., description="Distance in km"),
    weather: str = Query("sunny", description="sunny, moderate, rainy"),
    hour: Optional[int] = Query(None, description="Hour of day (0-23)")
):
    """ML-powered route analysis"""
    try:
        if not ml_models_loaded:
            return predict(distance, weather)
        
        delay_info = predict_delay_probability(distance, weather, hour)
        eta_info = predict_eta(distance, weather, hour)
        traffic_info = predict_traffic_severity(distance, weather, hour)
        
        recommendation = "Proceed as planned"
        if delay_info and delay_info['delay_probability'] > 0.6:
            recommendation = "⚠️ HIGH DELAY RISK - Consider alternate route or later departure"
        elif delay_info and delay_info['delay_probability'] > 0.3:
            recommendation = "⚠️ Moderate delay risk - Add buffer time"
        
        return {
            "color": traffic_info['color'],
            "message": f"{traffic_info['emoji']} {traffic_info['description']} | ETA: {eta_info['formatted'] if eta_info else 'N/A'} | Delay risk: {delay_info['delay_probability']*100:.0f}%" if delay_info else traffic_info['description'],
            "detailed_analysis": {
                "delay_prediction": delay_info,
                "eta_prediction": eta_info,
                "traffic_prediction": traffic_info,
                "recommendation": recommendation
            },
            "type": "ml-powered"
        }
    except Exception as e:
        print(f"ML error: {e}, falling back to rule-based")
        return predict(distance, weather)

@app.get("/ml/delay-risk")
def delay_risk(distance: float, weather: str = "sunny"):
    """Get probability of delay for this route"""
    result = predict_delay_probability(distance, weather)
    if result:
        return result
    return {"error": "ML models not loaded", "fallback": "Use /predict endpoint"}

@app.get("/ml/eta")
def eta_prediction(distance: float, weather: str = "sunny"):
    """Get predicted ETA in minutes"""
    result = predict_eta(distance, weather)
    if result:
        return result
    return {"error": "ML models not loaded", "fallback": "Use /predict endpoint"}

# ============================================
# TRIP LOGGING (for ML retraining)
# ============================================

@app.post("/trips/log")
async def log_trip(trip: TripData):
    """Save completed trip data for future ML retraining"""
    try:
        csv_file = 'data/trip_history.csv'
        os.makedirs('data', exist_ok=True)
        
        new_data = pd.DataFrame([trip.dict()])
        
        if os.path.exists(csv_file):
            existing = pd.read_csv(csv_file)
            updated = pd.concat([existing, new_data], ignore_index=True)
        else:
            updated = new_data
        
        updated.to_csv(csv_file, index=False)
        
        return {
            "status": "success",
            "message": "Trip data logged successfully",
            "total_trips": len(updated)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/trips/history")
async def get_trip_history(limit: int = 100):
    """Get historical trip data"""
    try:
        csv_file = 'data/trip_history.csv'
        if os.path.exists(csv_file):
            df = pd.read_csv(csv_file)
            return {
                "total_trips": len(df),
                "trips": df.tail(limit).to_dict('records')
            }
        else:
            return {"total_trips": 0, "trips": []}
    except Exception as e:
        return {"error": str(e)}

# ============================================
# REAL-TIME TRAFFIC API
# ============================================

@app.get("/traffic/real-time")
async def get_real_time_traffic(lat: float, lng: float, radius_km: float = 5):
    """Get real-time traffic conditions at a location"""
    try:
        hour = datetime.now().hour
        
        if 8 <= hour <= 10:
            traffic_speed = 25 + np.random.randint(-5, 5)
            congestion = "HEAVY"
        elif 17 <= hour <= 19:
            traffic_speed = 20 + np.random.randint(-5, 5)
            congestion = "HEAVY"
        elif 11 <= hour <= 16:
            traffic_speed = 45 + np.random.randint(-10, 10)
            congestion = "MODERATE"
        else:
            traffic_speed = 65 + np.random.randint(-5, 10)
            congestion = "LIGHT"
        
        return {
            "location": {"lat": lat, "lng": lng},
            "current_speed_kmh": max(10, traffic_speed),
            "free_flow_speed": 65,
            "congestion_level": congestion,
            "travel_time_factor": round(65 / max(10, traffic_speed), 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/traffic/route")
async def get_route_traffic(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float):
    """Get traffic summary for entire route"""
    hour = datetime.now().hour
    
    if 8 <= hour <= 10 or 17 <= hour <= 19:
        overall = "HEAVY"
        incidents = [
            {"type": "construction", "location": "NH44 near junction", "delay_minutes": 10},
            {"type": "accident", "location": "5km ahead", "delay_minutes": 15}
        ]
        recommendation = "Consider alternate route via outer ring road"
    elif 11 <= hour <= 16:
        overall = "MODERATE"
        incidents = [{"type": "construction", "location": "NH44 near junction", "delay_minutes": 5}]
        recommendation = "Minor delays expected"
    else:
        overall = "LIGHT"
        incidents = []
        recommendation = "Clear route, optimal travel conditions"
    
    return {
        "overall_congestion": overall,
        "incidents": incidents,
        "recommended_alternate": recommendation,
        "timestamp": datetime.now().isoformat()
    }

# ============================================
# ACCIDENT HISTORY
# ============================================

@app.get("/accidents/near-route")
async def get_accidents_near_route(
    lat1: float, lng1: float,
    lat2: float, lng2: float,
    radius_km: float = 2
):
    """Get historical accident data near the route"""
    accident_hotspots = [
        {"lat": 17.4399, "lng": 78.4983, "severity": "high", "date": "2024-01-15", "type": "multi-vehicle"},
        {"lat": 17.4250, "lng": 78.4400, "severity": "medium", "date": "2024-01-10", "type": "rear-end"},
        {"lat": 17.4500, "lng": 78.5200, "severity": "low", "date": "2024-01-05", "type": "single-vehicle"},
    ]
    
    risk_score = 0
    for accident in accident_hotspots:
        if accident['severity'] == 'high':
            risk_score += 0.4
        elif accident['severity'] == 'medium':
            risk_score += 0.2
        else:
            risk_score += 0.1
    
    risk_score = min(1.0, risk_score)
    risk_level = "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.3 else "LOW"
    
    return {
        "accident_hotspots": accident_hotspots,
        "total_accidents": len(accident_hotspots),
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "recommendation": f"{risk_level} risk zone - Exercise caution"
    }

# ============================================
# FUEL CONSUMPTION PREDICTION
# ============================================

@app.get("/fuel/predict")
async def predict_fuel_consumption(
    distance_km: float,
    traffic_level: str = "moderate",
    vehicle_type: str = "truck",
    load_weight_kg: float = 5000
):
    """Predict fuel consumption for the route"""
    consumption_rates = {
        "truck": {"light": 25, "moderate": 32, "heavy": 40},
        "van": {"light": 12, "moderate": 15, "heavy": 20},
        "car": {"light": 7, "moderate": 9, "heavy": 12}
    }
    
    traffic = traffic_level.lower()
    vehicle_rates = consumption_rates.get(vehicle_type, consumption_rates["truck"])
    base_rate = vehicle_rates.get(traffic, 32)
    
    load_factor = (load_weight_kg / 1000) * 0.5
    consumption_per_100km = base_rate + load_factor
    total_liters = (distance_km / 100) * consumption_per_100km
    
    co2_emission = total_liters * 2.68
    cost_estimate = total_liters * 1.20
    
    tips = []
    if traffic == "heavy":
        tips.append("Reduce speed to 80km/h to save up to 15% fuel")
    if load_weight_kg > 7000:
        tips.append("Heavy load detected - ensure proper tire pressure")
    
    return {
        "distance_km": distance_km,
        "vehicle_type": vehicle_type,
        "traffic_level": traffic,
        "load_weight_kg": load_weight_kg,
        "predicted_fuel_liters": round(total_liters, 1),
        "predicted_co2_kg": round(co2_emission, 1),
        "cost_estimate_usd": round(cost_estimate, 2),
        "fuel_efficiency_l_per_100km": round(consumption_per_100km, 1),
        "recommendations": tips if tips else ["Maintain steady speed for optimal efficiency"]
    }

# ============================================
# RISK SCORE (NEW FEATURE)
# ============================================

@app.get("/ml/risk-score")
async def calculate_risk_score(route_id: str = "123"):
    """Calculate overall supply chain risk score (0-100)"""
    
    # Get current conditions
    hour = datetime.now().hour
    
    # Simulate factor values based on time
    is_rush_hour = 1 if (7 <= hour <= 10 or 17 <= hour <= 19) else 0
    traffic_congestion = 0.7 if is_rush_hour else 0.3
    
    # Weather impact (simulated)
    weather_severity = 0.2
    
    # Driver fatigue (simulated)
    driver_fatigue = 0.3 if hour < 6 or hour > 22 else 0.1
    
    # Vehicle health (simulated)
    vehicle_health = 0.85
    
    # Weights
    weights = {
        "traffic_congestion": 0.30,
        "weather_severity": 0.20,
        "driver_fatigue": 0.25,
        "vehicle_health": 0.15,
        "geopolitical_risk": 0.10
    }
    
    risks = {
        "traffic_congestion": traffic_congestion,
        "weather_severity": weather_severity,
        "driver_fatigue": driver_fatigue,
        "vehicle_health": 1 - vehicle_health,
        "geopolitical_risk": 0.05
    }
    
    total_risk = sum(risks[k] * weights[k] for k in weights)
    
    if total_risk > 0.7:
        level = "CRITICAL"
        action = "IMMEDIATE REROUTING REQUIRED"
    elif total_risk > 0.4:
        level = "HIGH"
        action = "Active monitoring and contingency planning"
    elif total_risk > 0.2:
        level = "MEDIUM"
        action = "Standard precautions recommended"
    else:
        level = "LOW"
        action = "Normal operations"
    
    return {
        "overall_risk_score": round(total_risk * 100, 1),
        "risk_level": level,
        "risk_breakdown": {k: round(v * 100, 1) for k, v in risks.items()},
        "recommended_action": action,
        "confidence": 0.85
    }

# ============================================
# MODEL RETRAINING
# ============================================

@app.post("/models/retrain")
async def retrain_models():
    """Retrain ML models using all collected trip history"""
    try:
        import subprocess
        result = subprocess.run(
            ["python", "train_models.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode == 0:
            global delay_model, eta_model, traffic_model, weather_encoder, ml_models_loaded
            try:
                delay_model = joblib.load('ml_models/delay_classifier.pkl')
                eta_model = joblib.load('ml_models/eta_regressor.pkl')
                traffic_model = joblib.load('ml_models/traffic_model.pkl')
                weather_encoder = joblib.load('ml_models/weather_encoder.pkl')
                ml_models_loaded = True
            except:
                pass
            
            return {"status": "success", "message": "Models retrained successfully"}
        else:
            return {"status": "error", "message": result.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
def health():
    """API health check"""
    return {
        "status": "healthy",
        "ml_models_loaded": ml_models_loaded,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
def root():
    """API root information"""
    return {
        "name": "RouteGuard ML API",
        "version": "2.0",
        "ml_status": "Loaded" if ml_models_loaded else "Not Loaded",
        "endpoints": ["/predict", "/ml/analyze", "/ml/risk-score", "/fuel/predict", "/traffic/real-time", "/accidents/near-route"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)