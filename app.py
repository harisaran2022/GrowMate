import os
import logging
import requests
import markdown
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from disease_detection import analyze_plant_disease, get_gemini_analysis, fetch_gemini_response

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file upload size to 16MB

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Utility function to create unique filenames for uploads
def make_unique_filename(filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)):
        unique_filename = f"{base}_{counter}{ext}"
        counter += 1
    return unique_filename

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/disease-detection', methods=['GET', 'POST'])
def disease_detection():
    if request.method == 'POST':
        file = request.files.get('image')
        if not file or file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        filename = make_unique_filename(filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        try:
            result = analyze_plant_disease(file_path)  # Analyze disease from the uploaded image
            gemini_analysis = get_gemini_analysis(result['prediction'], result['confidence'])  # Get Gemini analysis
        except Exception as e:
            logger.error(f"Error analyzing plant disease: {e}")
            flash('Error analyzing plant disease')
            return redirect(request.url)
        image_url = url_for('static', filename=f'uploads/{filename}')
        logger.info(f"Result: {result}")
        logger.info(f"Gemini Analysis: {gemini_analysis}")
        gemini_analysis_html = markdown.markdown(gemini_analysis)
        return render_template('result.html', result=result, gemini_analysis=gemini_analysis_html, image_url=image_url)
    return render_template('disease_detection.html')
@app.route('/farm-management', methods=['GET', 'POST'])
def farm_management():
    """Handle farm management recommendations."""
    if request.method == 'POST':
        area = request.form.get('area')
        water_content = request.form.get('water_content')
        location = request.form.get('location')
        recommendation = get_farm_recommendations(area, water_content, location)
        
        # Convert recommendation to HTML using markdown
        recommendation_html = markdown.markdown(recommendation)
        
        return render_template('farm_management.html', recommendation=recommendation_html)
    return render_template('farm_management.html')
def get_farm_recommendations(area, water_content, location):
    """Get farm recommendations using the Gemini API."""
    prompt = (
        f"Provide farm management recommendations for an area of {area} in acre, "
        f"with {water_content} water moisture level, located in {location}. "
        "Include crop suggestions and basic care instructions."
        "And Also provide important points and Method of division of crops"
        "Always reply like your a Bot Called Growmate"
       )
     
    return fetch_gemini_response(prompt)
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    """Handle chatbot interactions."""
    if 'chat_history' not in session:
        session['chat_history'] = []  # Initialize chat history
    if request.method == 'POST':
        message = request.form['message']
        raw_response = get_gemini_reply(message)
        # Convert raw response to HTML using markdown
        formatted_response = markdown.markdown(raw_response)
        session['chat_history'].append(("You", message))
        session['chat_history'].append(("Bot", formatted_response))  # Use the formatted response
        return jsonify({"response": formatted_response})
    return render_template('chatbot.html', chat_history=session['chat_history'])
def get_gemini_reply(message):
    """Get chatbot reply using the Gemini API."""
    return fetch_gemini_response(message)
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
        logger.info(f"Gemini analysis response data: {response_data}")
        if 'candidates' in response_data and response_data['candidates']:
            candidate = response_data['candidates'][0]
            text_part = candidate.get('content', {}).get('parts', [{}])[0]
            return text_part.get('text', "Unable to fetch detailed analysis.")
        else:
            logger.warning("No candidates found in response.")
            return "Unable to generate analysis at this time."
    except requests.RequestException as e:
        logger.error(f"Error fetching Gemini analysis: {e}")
        return "Error occurred while fetching analysis."
@app.route('/analyze', methods=['POST'])
def analyze():
    file = request.files.get('image')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400
    filename = secure_filename(file.filename)
    filename = make_unique_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    try:
        result = analyze_plant_disease(file_path)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error analyzing plant disease: {e}")
        return jsonify({'error': 'Failed to analyze disease'}), 500
@app.route('/about_us')
def about_us():
    return render_template('about_us.html')
@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

# Serve robots.txt
@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
