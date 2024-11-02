import os
import logging
import requests
from tensorflow.keras.models import load_model
from PIL import Image
import numpy as np
import json  # Importing json module

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load your pre-trained model
MODEL_PATH = 'plant_model_v5-beta.h5'  # Replace with your actual model path
model = load_model(MODEL_PATH)

# Load class indices from JSON file
def load_class_indices(json_file):
    """Load class indices from a JSON file."""
    with open(json_file, 'r') as file:
        return json.load(file)

class_indices = load_class_indices('class_indices.json')

def analyze_plant_disease(image_path):
    """Analyze the plant disease based on the uploaded image."""
    try:
        # Preprocess the image
        img = Image.open(image_path)
        img = img.resize((224, 224))  # Adjust size based on your model
        img_array = np.array(img) / 255.0  # Normalize the image
        img_array = np.expand_dims(img_array, axis=0)

        # Make prediction
        predictions = model.predict(img_array)
        predicted_class_index = np.argmax(predictions, axis=1)[0]
        confidence = np.max(predictions) * 100

        # Map predicted class to label
        predicted_class = class_indices.get(str(predicted_class_index), "Unknown")
        result = {
            'prediction': predicted_class,
            'confidence': confidence,
        }
        logger.info(f"Prediction: {result['prediction']} with confidence: {result['confidence']:.2f}%")
        return result
    except Exception as e:
        logger.error(f"Error analyzing plant disease: {e}")
        raise

def get_gemini_analysis(prediction, confidence):
    """Get Gemini analysis based on prediction and confidence."""
    prompt = (f"Provide a detailed analysis of the plant disease prediction: '{prediction}' with a confidence of {confidence:.2f}%. "
            f"Ensure the response includes care tips and specific recommendations. "
            "If the prediction seems incomplete or unclear, Just tell Retry")

    response = fetch_gemini_response(prompt)
    return response

def fetch_gemini_response(prompt):
    """Fetch response from Gemini API."""
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Store the API key securely
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()
        
        if 'candidates' in response_data and response_data['candidates']:
            candidate = response_data['candidates'][0]
            return candidate.get('content', {}).get('parts', [{}])[0].get('text', "Unable to fetch analysis.")
        else:
            logger.warning("No candidates found in response.")
            return "No analysis available."
    except requests.RequestException as e:
        logger.error(f"Error fetching Gemini analysis: {e}")
        return "Error occurred while fetching analysis."