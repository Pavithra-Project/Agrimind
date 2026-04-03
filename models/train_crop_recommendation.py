import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score
import joblib

# Create synthetic data with explanation rules
# Crops: Wheat, Rice, Corn, Cotton, Sugarcane
# Soils: Loamy, Clay, Sandy, Peaty, Saline
# Seasons: Summer, Winter, Monsoon, Spring

np.random.seed(42)
num_samples = 1000

soils = ['Loamy', 'Clay', 'Sandy', 'Peaty', 'Saline']
seasons = ['Summer', 'Winter', 'Monsoon', 'Spring']
crops = ['Wheat', 'Rice', 'Corn', 'Cotton', 'Sugarcane']

data = {
    'soil_type': np.random.choice(soils, num_samples),
    'season': np.random.choice(seasons, num_samples),
    'temperature': np.random.uniform(10, 40, num_samples), # Celsius
    'humidity': np.random.uniform(20, 90, num_samples)    # Percentage
}

df = pd.DataFrame(data)

# Logic for assigning crops
def determine_crop(row):
    temp = row['temperature']
    hum = row['humidity']
    season = row['season']
    soil = row['soil_type']
    
    if season == 'Winter' and temp < 25 and soil in ['Loamy', 'Clay']:
        return 'Wheat'
    elif season == 'Monsoon' and hum > 70 and soil == 'Clay':
        return 'Rice'
    elif temp > 25 and soil == 'Sandy':
        return 'Cotton'
    elif hum > 60 and temp > 20 and soil in ['Loamy', 'Peaty']:
        return 'Sugarcane'
    else:
        return 'Corn'

df['crop'] = df.apply(determine_crop, axis=1)

# Encode categorical variables
le_soil = LabelEncoder()
le_season = LabelEncoder()
le_crop = LabelEncoder()

df['soil_encoded'] = le_soil.fit_transform(df['soil_type'])
df['season_encoded'] = le_season.fit_transform(df['season'])
df['crop_encoded'] = le_crop.fit_transform(df['crop'])

X = df[['soil_encoded', 'season_encoded', 'temperature', 'humidity']]
y = df['crop_encoded']

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Scaling
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Model Training
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train_scaled, y_train)

# Evaluation
y_pred = model.predict(X_test_scaled)
print(f"Crop Recommendation Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")

# Save Models and Encoders
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/crop_rf_model.pkl')
joblib.dump(scaler, 'models/crop_scaler.pkl')
joblib.dump(le_soil, 'models/le_soil.pkl')
joblib.dump(le_season, 'models/le_season.pkl')
joblib.dump(le_crop, 'models/le_crop.pkl')

print("Crop Recommendation Model saved successfully!")
