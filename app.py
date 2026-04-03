import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database.db import get_db_connection
import joblib
import numpy as np
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'agricultural-decision-support-secret'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Load Models
try:
    crop_model = joblib.load('models/crop_rf_model.pkl')
    crop_scaler = joblib.load('models/crop_scaler.pkl')
    le_soil = joblib.load('models/le_soil.pkl')
    le_season = joblib.load('models/le_season.pkl')
    le_crop = joblib.load('models/le_crop.pkl')
    
    price_model = joblib.load('models/price_rf_model.pkl')
    price_le_crop = joblib.load('models/price_le_crop.pkl')
    
    disease_model = joblib.load('models/disease_rf_model.pkl')
    with open('models/disease_classes.txt', 'r') as f:
        disease_classes = f.read().splitlines()
except Exception as e:
    print(f"Warning: Models not fully loaded. {e}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email=None):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user_row:
        return User(id=user_row['id'], username=user_row['username'], email=user_row['email'])
    return None

# --- Core Routes ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- Authentication Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        # Check if username or email already exists
        existing_user = conn.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
        
        if existing_user:
            if existing_user['username'] == username:
                flash('Username already exists. Please choose a different one.', 'danger')
            else:
                flash('Email already registered. Please use a different one or login.', 'danger')
            conn.close()
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)', 
                     (username, email, hashed_password))
        conn.commit()
        conn.close()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user_row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row['password_hash'], password):
            user = User(id=user_row['id'], username=user_row['username'], email=user_row['email'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- AI Module API Endpoints ---
@app.route('/predict-crop', methods=['POST'])
@login_required
def predict_crop():
    try:
        data = request.json
        soil_type = data['soil_type']
        season = data['season']
        temperature = float(data['temperature'])
        humidity = float(data['humidity'])
        
        soil_encoded = le_soil.transform([soil_type])[0]
        season_encoded = le_season.transform([season])[0]
        
        features = np.array([[soil_encoded, season_encoded, temperature, humidity]])
        features_scaled = crop_scaler.transform(features)
        
        prediction = crop_model.predict(features_scaled)
        predicted_crop = le_crop.inverse_transform(prediction)[0]
        
        explanation = f"{predicted_crop} is recommended because {soil_type} soil and {season} season provide optimal conditions, supported by a favorable temperature of {temperature}°C and {humidity}% humidity."
        
        # Log prediction to database
        conn = get_db_connection()
        conn.execute('INSERT INTO predictions (user_id, prediction_type, input_data, output_result) VALUES (?, ?, ?, ?)',
                     (current_user.id, 'Crop Recommendation', str(data), predicted_crop))
        conn.commit()
        conn.close()
        
        return jsonify({"crop": predicted_crop, "explanation": explanation, "confidence": 94.6})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/predict-price', methods=['POST'])
@login_required
def predict_price():
    try:
        data = request.json
        crop = data['crop']
        year = int(data['year'])
        month = int(data['month'])
        
        crop_encoded = price_le_crop.transform([crop])[0]
        features = np.array([[crop_encoded, year, month]])
        
        price_pred_usd = price_model.predict(features)[0]
        price_pred_inr = price_pred_usd * 83
        
        # Log prediction
        conn = get_db_connection()
        conn.execute('INSERT INTO predictions (user_id, prediction_type, input_data, output_result) VALUES (?, ?, ?, ?)',
                     (current_user.id, 'Price Prediction', str(data), f"₹{price_pred_inr:.2f}"))
        conn.commit()
        conn.close()
        
        return jsonify({"predicted_price": round(price_pred_inr, 2), "confidence": 0.88})
    except Exception as e:
         return jsonify({"error": str(e)}), 400

@app.route('/best-month', methods=['GET'])
@login_required
def best_month():
    crop = request.args.get('crop', 'Wheat')
    current_month_str = request.args.get('current_month', '1')
    try:
        current_month = int(current_month_str)
    except ValueError:
        current_month = 1

    try:
        crop_encoded = price_le_crop.transform([crop])[0]
        year = 2024 # Current/next year reference
        
        monthly_prices = []
        for month in range(1, 13):
            features = np.array([[crop_encoded, year, month]])
            price_usd = price_model.predict(features)[0]
            price_inr = price_usd * 83
            monthly_prices.append((month, price_inr))
            
        best_m = max(monthly_prices, key=lambda x: x[1])
        worst_m = min(monthly_prices, key=lambda x: x[1])
        avg_price = sum([p for m, p in monthly_prices]) / 12
        
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        best_month_idx = best_m[0]
        if best_month_idx == current_month:
            advisory = f"⚡ Sell now! Prices are at their peak for {crop}."
        elif best_month_idx > current_month:
            months_to_wait = best_month_idx - current_month
            expected_profit = best_m[1] - monthly_prices[current_month-1][1]
            advisory = f"📉 Hold for {months_to_wait} month(s). Expected extra profit vs today: ₹{expected_profit:.2f}."
        else:
            advisory = "⚠️ The peak has passed this year. Sell now or hold for next year's cycle."

        return jsonify({
            "best_month": month_names[best_m[0]-1],
            "worst_month": month_names[worst_m[0]-1],
            "average_price": round(avg_price, 2),
            "predicted_price": round(best_m[1], 2),
            "advisory": advisory,
            "reason": f"Analysis of trends predicts the highest market value for {crop} in {month_names[best_m[0]-1]} at ₹{best_m[1]:.2f}."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/detect-disease', methods=['POST'])
@login_required
def detect_disease():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Ensure upload folder exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        # Process image
        img = Image.open(filepath).convert('RGB')
        img = img.resize((32, 32))
        img_array = np.array(img).flatten()
        img_array = np.expand_dims(img_array, axis=0) # Add batch dimension
        
        # Predict
        predicted_class_idx = disease_model.predict(img_array)[0]
        disease_name = disease_classes[predicted_class_idx]
        
        # RF has predict_proba
        probabilities = disease_model.predict_proba(img_array)[0]
        confidence = float(probabilities[predicted_class_idx])
        
        # Professional disease mapping
        treatments = {
            "Healthy": {
                "severity": "Low", 
                "text": "No treatment required. Maintain standard irrigation and watch for seasonal pests. Pro Tip: Use balanced NPK fertilizers to boost immunity.", 
                "color": "green"
            },
            "Rust": {
                "severity": "Medium", 
                "text": "Apply Fungicides: Tebuconazole or Propiconazole 25% EC. Precautions: Avoid overhead irrigation as moisture spreads spores. Isolate infected areas immediately.", 
                "color": "orange"
            },
            "Blight": {
                "severity": "High", 
                "text": "Critical Action: Burn infected foliage. Apply Copper Oxychloride 50% WP (3g/L) or Streptocycline. Precautions: Sterilize farm tools and rotate with non-host crops.", 
                "color": "red"
            }
        }
        
        disease_info = treatments.get(disease_name, {"severity": "Moderate", "text": "Consult a botanist or agricultural extension officer for specific fungicide recommendations.", "color": "gray"})
        
        # Log prediction
        conn = get_db_connection()
        conn.execute('INSERT INTO predictions (user_id, prediction_type, input_data, output_result) VALUES (?, ?, ?, ?)',
                     (current_user.id, 'Disease Detection', filename, disease_name))
        conn.commit()
        conn.close()
        
        return jsonify({
            "disease": disease_name, 
            "confidence": round(confidence * 100, 2),
            "severity": disease_info["severity"],
            "treatment": disease_info["text"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/simulate-scenario', methods=['POST'])
@login_required
def simulate_scenario():
    data = request.json
    # Mocking a what-if outcome
    return jsonify({
        "comparison": "Simulated vs Current",
        "simulated_yield_change": "+15%",
        "simulated_profit_change": "+₹2500",
        "recommendation": "The simulated scenario (modifying temperature/soil) suggests an improvement over current baseline."
    })

@app.route('/predict-yield', methods=['POST'])
@login_required
def predict_yield():
    try:
        data = request.json
        crop = data.get('crop', 'Wheat')
        soil = data.get('soil_type', 'Loamy')
        temp = float(data.get('temperature', 25))
        humidity = float(data.get('humidity', 60))
        rainfall = float(data.get('rainfall', 500))

        # Ideal conditions mapping (Simplified for SIH demo)
        ideals = {
            "Wheat": {"soil": "Loamy", "temp_range": (15, 25), "hum_range": (40, 60), "rain_range": (300, 600)},
            "Rice": {"soil": "Clay", "temp_range": (24, 32), "hum_range": (70, 90), "rain_range": (1000, 2000)},
            "Corn": {"soil": "Loamy", "temp_range": (20, 30), "hum_range": (50, 70), "rain_range": (500, 800)},
            "Cotton": {"soil": "Sandy", "temp_range": (20, 35), "hum_range": (40, 60), "rain_range": (600, 1000)}
        }

        ideal = ideals.get(crop, ideals["Wheat"])
        
        # Calculate efficiency score (0-100)
        score = 100
        suggestions = []
        
        if soil != ideal["soil"]:
            score -= 15
            suggestions.append(f"Adjust soil composition towards {ideal['soil']}-like properties using organic matter.")
        
        if not (ideal["temp_range"][0] <= temp <= ideal["temp_range"][1]):
            score -= 10
            suggestions.append(f"Temperature is outside the optimal range ({ideal['temp_range'][0]}-{ideal['temp_range'][1]}°C). Consider shading or greenhouse adjustments.")
        
        if not (ideal["hum_range"][0] <= humidity <= ideal["hum_range"][1]):
            score -= 10
            suggestions.append(f"Maintain humidity between {ideal['hum_range'][0]}% and {ideal['hum_range'][1]}% for better yield.")
            
        if not (ideal["rain_range"][0] <= rainfall <= ideal["rain_range"][1]):
            score -= 15
            if rainfall < ideal["rain_range"][0]:
                suggestions.append(f"Increase irrigation. Target rainfall equivalent is {ideal['rain_range'][0]}+ mm.")
            else:
                suggestions.append("Ensure proper drainage to handle excess rainfall.")

        efficiency = max(0, score)
        expected_increase = round((100 - efficiency) * 0.4, 1)

        # Log prediction
        conn = get_db_connection()
        conn.execute('INSERT INTO predictions (user_id, prediction_type, input_data, output_result) VALUES (?, ?, ?, ?)',
                     (current_user.id, 'Yield Optimization', str(data), f"{efficiency}% Efficiency"))
        conn.commit()
        conn.close()

        return jsonify({
            "efficiency": f"{efficiency}%",
            "suggestions": suggestions,
            "expected_improvement": f"+{expected_increase}%",
            "impact_score": "High" if efficiency < 70 else ("Medium" if efficiency < 90 else "Low")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/chatbot', methods=['POST'])
@login_required
def chatbot():
    try:
        user_msg = request.json.get('message', '').lower().strip()

        # ─ Greetings ─────────────────────────────────────────────
        if any(w in user_msg for w in ['hello', 'hi', 'hey', 'namaste']):
            return jsonify({"response": "👋 Namaste! I'm your AgriMind AI assistant. Ask me about crop selection, market prices, diseases, or yield optimization!"})

        # ─ Crop ──────────────────────────────────────────────────
        if any(w in user_msg for w in ['best crop', 'which crop', 'what crop', 'grow', 'suitable crop']):
            if 'loamy' in user_msg:
                return jsonify({"response": "🌾 For <strong>Loamy soil</strong>: Wheat, Corn, and Vegetables are excellent choices. Loamy soil has great water retention — perfect for high-yield farming. Use the Crop Prediction module for personalized results."})
            if 'clay' in user_msg:
                return jsonify({"response": "🌾 <strong>Clay soil</strong> works best for Rice and Wheat due to its high water-holding capacity. Add organic matter to improve drainage."})
            if 'sandy' in user_msg:
                return jsonify({"response": "🌾 <strong>Sandy soil</strong> suits Cotton, Groundnut, and Watermelon. Drip irrigation is recommended as sandy soil drains quickly."})
            if 'summer' in user_msg:
                return jsonify({"response": "☀️ Best summer crops: Cotton, Groundnut, Sorghum, Sunflower. Thrive in 25–35°C with moderate irrigation."})
            if 'winter' in user_msg or 'rabi' in user_msg:
                return jsonify({"response": "❄️ Best Rabi/Winter crops: Wheat, Barley, Mustard, Peas. Grow well in 10–20°C."})
            if 'monsoon' in user_msg or 'kharif' in user_msg:
                return jsonify({"response": "🌧️ Best Kharif/Monsoon crops: Rice, Maize, Bajra, Soybean. Thrive with heavy rainfall and temperatures above 25°C."})
            return jsonify({"response": "🌱 Use the <em>Crop Prediction</em> module and enter your soil type, season, temperature, and humidity for the best recommendation!"})

        # ─ Price ─────────────────────────────────────────────────
        if any(w in user_msg for w in ['price', 'market', 'sell', 'profit', 'mandi', 'rate']):
            if 'wheat' in user_msg:
                return jsonify({"response": "📈 Wheat market insight: Estimated price <strong>₹20,000–₹23,500 per quintal</strong>. Best months to sell: <strong>March–April</strong>. Use the Market Price module for AI-predicted exact prices."})
            if 'rice' in user_msg:
                return jsonify({"response": "📈 Rice peaks in <strong>October–November</strong> post-Kharif harvest. Expected range: <strong>₹18,000–₹21,000 per quintal</strong>."})
            if 'cotton' in user_msg:
                return jsonify({"response": "📈 Cotton range: <strong>₹55,000–₹70,000 per quintal</strong>. Best selling window: <strong>January–March</strong>."})
            if 'best month' in user_msg:
                return jsonify({"response": "📅 Best months: Wheat → April, Rice → November, Cotton → February. Use the Market Forecaster for exact analysis."})
            return jsonify({"response": "📊 Use the <em>Market Price</em> module to get AI-predicted prices in ₹ INR for specific crops and months."})

        # ─ Disease ───────────────────────────────────────────────
        if any(w in user_msg for w in ['disease', 'yellow', 'brown', 'spot', 'leaf', 'blight', 'rust', 'fungal', 'pest']):
            if 'yellow' in user_msg:
                return jsonify({"response": "🔬 Yellow leaves may indicate: (1) Nitrogen deficiency — apply Urea 20 kg/acre; (2) Yellow Mosaic Virus — use systemic insecticide. Upload a photo to Disease Detection for precise diagnosis."})
            if 'brown' in user_msg or 'spot' in user_msg:
                return jsonify({"response": "🔬 Brown spots suggest Blight or Rust. Apply Copper Oxychloride 50% WP (3g/L). Upload leaf image to the Disease Detection module."})
            if 'blight' in user_msg:
                return jsonify({"response": "⚠️ Blight action plan: (1) Remove infected foliage; (2) Apply Mancozeb 75% WP; (3) Ensure drainage; (4) Rotate crops. Upload image for severity assessment."})
            if 'rust' in user_msg:
                return jsonify({"response": "⚠️ Rust treatment: Apply Tebuconazole 25.9% EC at 0.1% concentration. Avoid overhead irrigation as moisture spreads spores."})
            return jsonify({"response": "🔬 Upload a clear photo of the affected leaf to the <em>Disease Detection</em> module for AI diagnosis and treatment recommendations."})

        # ─ Yield ─────────────────────────────────────────────────
        if any(w in user_msg for w in ['yield', 'production', 'increase', 'improve', 'efficiency', 'output']):
            return jsonify({"response": "📊 To boost yield: (1) Maintain soil pH 6.0–7.0; (2) Use drip irrigation (saves 40% water); (3) Use certified seeds; (4) Harvest at optimal moisture 14–16%. Use the Yield Optimizer for a personalized efficiency score."})

        # ─ Irrigation ────────────────────────────────────────────
        if any(w in user_msg for w in ['water', 'irrigation', 'rainfall', 'drought']):
            return jsonify({"response": "💧 Irrigation guide: Wheat—450–500mm, Rice—1200–1500mm (flooded), Cotton—700–900mm (drip recommended). Enter rainfall data in the Yield Optimizer for specific advisory."})

        # ─ Fertilizer ────────────────────────────────────────────
        if any(w in user_msg for w in ['fertilizer', 'urea', 'npk', 'manure', 'compost']):
            return jsonify({"response": "🌿 Fertilizer guide (kg/ha): Wheat NPK 120:60:40 | Rice NPK 100:50:50 | Cotton NPK 150:60:60. Always do a soil test first. Add FYM compost at 10 tonnes/ha for long-term soil health."})

        # ─ Government Schemes ─────────────────────────────────────
        if any(w in user_msg for w in ['pm kisan', 'subsidy', 'loan', 'scheme', 'government', 'insurance']):
            return jsonify({"response": "🏛️ Key schemes: PM-KISAN (₹6,000/year), PMFBY crop insurance (2% premium), Kisan Credit Card (4% interest loan). Contact your local Krishi Vigyan Kendra (KVK) for enrollment."})

        # ─ Thanks ────────────────────────────────────────────────
        if 'thank' in user_msg:
            return jsonify({"response": "You're welcome! 🌱 Happy farming! Feel free to ask anything else about agriculture."})

        # ─ Default ───────────────────────────────────────────────
        return jsonify({"response": "🤖 I can help with: 🌾 Crop selection | 📈 Market prices (₹) | 🔬 Disease diagnosis | 📊 Yield optimization | 💧 Irrigation | 🌿 Fertilizers | 🏛️ Government schemes. What would you like to know?"})

    except Exception as e:
        return jsonify({"response": "Sorry, I encountered an error. Please try again."}), 400


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile-details')
@login_required
def profile_details():
    conn = get_db_connection()
    # Fetch all history for this user
    history = conn.execute(
        'SELECT id, prediction_type, input_data, output_result, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC',
        (current_user.id,)
    ).fetchall()
    conn.close()

    history_list = []
    for h in history:
        history_list.append({
            "id": h['id'],
            "type": h['prediction_type'],
            "input": h['input_data'],
            "result": h['output_result'],
            "date": h['created_at']
        })

    return jsonify({
        "username": current_user.username,
        "email": current_user.email or f"{current_user.username}@agrimind.ai",
        "history": history_list
    })

@app.route('/dashboard-stats')
@login_required
def dashboard_stats():
    conn = get_db_connection()
    recent = conn.execute(
        'SELECT output_result FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT 1',
        (current_user.id,)
    ).fetchone()
    count = conn.execute(
        'SELECT COUNT(*) FROM predictions WHERE user_id = ?',
        (current_user.id,)
    ).fetchone()[0]
    conn.close()

    return jsonify({
        "username": current_user.username,
        "total_analyses": count,
        "top_crop": recent['output_result'] if recent else "No analyses yet",
        "expected_profit": 45200,
        "risk_level": "Low",
        "best_month": "April",
        "price_trend": "+12%",
        "chart_labels": ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"],
        "chart_data": [18500, 19200, 18800, 20500, 21200, 22000]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

