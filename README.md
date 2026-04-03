# AI Agricultural Decision Support System

A complete full-stack AI-Based Agricultural Decision Support System, built with Python Flask, Scikit-learn, TensorFlow, and modern HTML/CSS/JS.

## Features
- **Crop Recommendation System:** Recommends the best crop based on soil type, season, temperature, and humidity.
- **Market Price Prediction System:** Predicts the market price for a selected crop and future date.
- **Best Month to Sell:** Analyzes historical price trends to suggest the best month to sell.
- **Crop Disease Detection:** Uses a CNN to classify diseases from crop leaf image uploads and recommends treatment.
- **User Authentication:** Secure registration and login.
- **Professional Dashboard:** A sleek, responsive user interface with Chart.js visualizations.

## Project Structure
- `app.py`: Main Flask application and REST APIs.
- `models/`: Machine learning training scripts and saved models.
- `database/`: SQLite database initialization and schema.
- `static/`: CSS styling, JavaScript logic, and image uploads.
- `templates/`: HTML templates for the frontend UI.

## Setup Instructions

1. **Install Dependencies**
   It's recommended to create a virtual environment first, then run:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize Database and Train Models**
   Before running the app, you need to set up the database and train the machine learning models.
   ```bash
   python database/db.py
   python models/train_crop_recommendation.py
   python models/train_price_prediction.py
   python models/train_disease_model.py
   ```

3. **Run the Application**
   ```bash
   python app.py
   ```
   Open your browser and navigate to `http://127.0.0.1:5000`

## Usage
- Register for an account or login.
- Access the dashboard to use the various AI modules.
