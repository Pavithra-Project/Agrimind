import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import root_mean_squared_error, r2_score
import joblib

np.random.seed(42)
num_samples = 2000

crops = ['Wheat', 'Rice', 'Corn', 'Cotton', 'Sugarcane']
years = [2020, 2021, 2022, 2023, 2024]
months = list(range(1, 13))

data = {
    'crop': np.random.choice(crops, num_samples),
    'year': np.random.choice(years, num_samples),
    'month': np.random.choice(months, num_samples)
}

df = pd.DataFrame(data)

# Logic to generate synthetic prices with trends
def generate_price(row):
    base_prices = {'Wheat': 2000, 'Rice': 3000, 'Corn': 1500, 'Cotton': 5000, 'Sugarcane': 2500}
    price = base_prices[row['crop']]
    
    # Yearly inflation trend
    price += (row['year'] - 2020) * 150 
    
    # Seasonality / Month trend (e.g., higher prices in winter)
    if row['month'] in [11, 12, 1, 2]:
        price += 300
    elif row['month'] in [5, 6, 7]:
        price -= 200 # harvest season, lower prices
        
    # Random noise
    price += np.random.normal(0, 150)
    
    return max(500, price) # Ensure no negative prices

df['price'] = df.apply(generate_price, axis=1)

le_crop = LabelEncoder()
df['crop_encoded'] = le_crop.fit_transform(df['crop'])

X = df[['crop_encoded', 'year', 'month']]
y = df['price']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
rmse = root_mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"Price Prediction RMSE: {rmse:.2f}")
print(f"Price Prediction R2 Score: {r2:.2f}")

os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/price_rf_model.pkl')
joblib.dump(le_crop, 'models/price_le_crop.pkl')

print("Price Prediction Model saved successfully!")
