import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
import joblib
import os

# Create models directory if it doesn't exist
os.makedirs('ml_models', exist_ok=True)

# Load your historical data
print("📊 Loading training data...")
df = pd.read_csv('../data/historical_trips.csv')

# ============================================
# MODEL 1: DELAY PREDICTION CLASSIFIER
# Predicts: Will this trip be delayed? (Yes/No)
# ============================================
print("\n🤖 Training Delay Prediction Model...")

# Prepare features
features = ['distance_km', 'hour_of_day', 'day_of_week', 'is_rush_hour']
X = df[features].copy()

# Encode weather (convert text to numbers)
weather_encoder = LabelEncoder()
X['weather_encoded'] = weather_encoder.fit_transform(df['weather_type'])

# Add weather encoded to features
X = pd.concat([X[features], X['weather_encoded']], axis=1)

# Target: was_delayed (0 or 1)
y = df['was_delayed']

# Train model
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
delay_model = RandomForestClassifier(n_estimators=100, random_state=42)
delay_model.fit(X_train, y_train)

# Save model and encoder
joblib.dump(delay_model, 'ml_models/delay_classifier.pkl')
joblib.dump(weather_encoder, 'ml_models/weather_encoder.pkl')

accuracy = delay_model.score(X_test, y_test)
print(f"✅ Delay model accuracy: {accuracy:.2%}")

# ============================================
# MODEL 2: ETA PREDICTION REGRESSOR
# Predicts: How many minutes will this trip take?
# ============================================
print("\n⏱️ Training ETA Prediction Model...")

# Same features
X_eta = X.copy()
y_eta = df['actual_duration_min']

eta_model = RandomForestRegressor(n_estimators=100, random_state=42)
eta_model.fit(X_train, y_train)

joblib.dump(eta_model, 'ml_models/eta_regressor.pkl')

r2_score = eta_model.score(X_test, y_test)
print(f"✅ ETA model R² score: {r2_score:.2%}")

# ============================================
# MODEL 3: TRAFFIC SEVERITY (Multi-class)
# ============================================
print("\n🚦 Training Traffic Severity Model...")

def get_traffic_severity(duration, distance):
    """Calculate traffic severity based on actual vs expected speed"""
    expected_speed = 50  # km/h normal
    actual_speed = (distance / duration) * 60
    ratio = actual_speed / expected_speed
    
    if ratio < 0.4:
        return 2  # Heavy
    elif ratio < 0.7:
        return 1  # Moderate
    else:
        return 0  # Light

df['traffic_severity'] = df.apply(
    lambda row: get_traffic_severity(row['actual_duration_min'], row['distance_km']), 
    axis=1
)

traffic_model = RandomForestClassifier(n_estimators=100, random_state=42)
traffic_model.fit(X_train, df.loc[X_train.index, 'traffic_severity'])

joblib.dump(traffic_model, 'ml_models/traffic_model.pkl')

print(f"✅ Traffic model trained (classes: 0=Light, 1=Moderate, 2=Heavy)")

print("\n🎉 All models trained successfully!")
print("📁 Models saved in 'ml_models' folder")