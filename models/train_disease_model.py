import os
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

# 1. Generate Dummy Image Data
# We will create solid color images to represent "Healthy", "Rust", and "Blight"

dataset_dir = 'models/synthetic_dataset'
classes = ['Healthy', 'Rust', 'Blight']
colors = {
    'Healthy': [34, 139, 34],   # Green
    'Rust': [139, 69, 19],      # Brown
    'Blight': [210, 180, 140]   # Pale Brown/Yellow
}

num_images_per_class = 50
img_size = (32, 32) # Smaller size for simple RF classifier

os.makedirs(dataset_dir, exist_ok=True)

print("Generating synthetic images...")
X_data = []
y_data = []

for label_idx, cls in enumerate(classes):
    class_dir = os.path.join(dataset_dir, cls)
    os.makedirs(class_dir, exist_ok=True)
    
    for i in range(num_images_per_class):
        color_rgb = colors[cls]
        
        # Add random noise
        noise = np.random.randint(-30, 30, size=3)
        noisy_color = np.clip(np.array(color_rgb) + noise, 0, 255).astype(np.uint8)
        
        img = Image.new('RGB', img_size, color=tuple(noisy_color))
        img.save(os.path.join(class_dir, f'{cls}_{i}.jpg'))
        
        # Flatten image for RandomForest: 32x32x3 = 3072 features
        img_array = np.array(img).flatten()
        X_data.append(img_array)
        y_data.append(label_idx)

print("Synthetic dataset created.")

X = np.array(X_data)
y = np.array(y_data)

# 2. Train a Random Forest Classifier (Substitute for CNN for dummy data)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training Disease Detection model (RandomForest)...")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"Validation Accuracy: {accuracy*100:.2f}%")

# Save Models
os.makedirs('models', exist_ok=True)
joblib.dump(model, 'models/disease_rf_model.pkl')

with open('models/disease_classes.txt', 'w') as f:
    f.write('\n'.join(classes))

print("Disease Detection Model saved successfully.")
