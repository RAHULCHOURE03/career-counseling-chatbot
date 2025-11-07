import nltk
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import pickle
import numpy as np
import os

#from keras.models import load_model
from tensorflow.keras.models import load_model
model = load_model('chatbot_model')
#model.save('chatbot_model')
import json
import random
intents = json.loads(open('intents.json', encoding="utf8").read())
words = pickle.load(open('words.pkl','rb'))
classes = pickle.load(open('classes.pkl','rb'))


def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence

def bow(sentence, words, show_details=True):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)
    # bag of words - matrix of N words, vocabulary matrix
    bag = [0]*len(words)
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s:
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print ("found in bag: %s" % w)
    return(np.array(bag))

def predict_class(sentence, model):
    # filter out predictions below a threshold
    p = bow(sentence, words,show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.80
    results = [[i,r] for i,r in enumerate(res) if r>ERROR_THRESHOLD]
    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)

    if not results:
        print("No matching intents found, default response triggered.", flush=True)
        return [{"intent": "default", "probability": "0"}]
    
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

def getResponse(ints, intents_json):
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']

    if tag == "default":
        return "Sorry! query not found, please ask the question related to the engineering field"
    
    for i in list_of_intents:
        if(i['tag']== tag):
            result = random.choice(i['responses'])
            break
    return result

import re
from deep_translator import GoogleTranslator
# translator = GoogleTranslator()

def is_hinglish(text):
    # Check: only contains alphabets, spaces, digits (no Devanagari)
    is_latin = bool(re.fullmatch(r'[A-Za-z0-9 ?!.,\'"-]+', text.strip()))
    
    # Check if message has very few English keywords (adjust as needed)
    common_english_words = ['what', 'is', 'how', 'are', 'the', 'you', 'about', 'engineering', 'career']
    contains_english = any(word in text.lower() for word in common_english_words)
    
    return is_latin and not contains_english


def chatbot_response(msg):

    hinglish = is_hinglish(msg)

    # Detect Language by Translating to English
    translated_msg = GoogleTranslator(source="auto", target="en").translate(msg)
        
   # check the detected language
    if msg == translated_msg:
        detected_lang = "hi" if hinglish else "en"
    else:
        detected_lang = "hi"
    print(f"Detected Language: {detected_lang}")
        
    # If English, use original message; otherwise, use translated version
    processed_msg = msg if detected_lang == "en" else translated_msg
       
    ints = predict_class(processed_msg, model)
    res = getResponse(ints, intents)
    
    # Translate back to Hindi if original input was in Hindi/Hinglish
    if detected_lang == "hi":
        res = GoogleTranslator(source="auto", target="hi").translate(res)

    return res

# Store each question in questions.json
def store_question(question, filename="questions.json"):
    try:
        # Check if the file exists and read its contents
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf8") as file:
                questions_data = json.load(file)
        else:
            questions_data = []  # Initialize as an empty list if file does not exist

       # Check for an exact match with 100% similarity
        if any(q['question'] == question for q in questions_data):
            print(f"Question '{question}' is already in the file.")  # Debug: Confirm duplicate found
            return
        
        # Append the question if not an exact duplicate
        questions_data.append({"question": question})
        print(f"Added question: '{question}'")

        # Write the updated list back to the file
        with open(filename, "w", encoding="utf8") as file:
            json.dump(questions_data, file, indent=4)
    except Exception as e:
        print("Error in store_question:", e)  # Print detailed error for debugging


''' Flask code '''


from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)

# Configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost/chatbot'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Create tables before first request
@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.form
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')

        if User.query.filter_by(email=email).first():
            return render_template('signup.html', message='User already exists')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user'] = email
            session['username'] = user.name
            return redirect(url_for('index'))
        
        return render_template('login.html', message='Invalid credentials')
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear user session
    return jsonify({"success": True})  # Ensure JSON response

@app.route('/home/<name>', methods=['GET'])
# @jwt_required()
def hello_name(name):
    dec_msg = name.replace("+", " ")
    store_question(dec_msg)
    response = chatbot_response(dec_msg)
    return jsonify({"top": {"res": response}})

@app.route('/get-user')
def get_user():
    if 'user' in session:
        user = User.query.filter_by(email=session['user']).first()
        if user:
            return jsonify({"name": user.name, "email": user.email})
    return jsonify({"error": "User not found"}), 404

# from here to undo
from datetime import datetime, timedelta

HISTORY_FILE = "history.json"


def load_history():
    """Load history from history.json, ensuring it is correctly initialized."""
    if not os.path.exists(HISTORY_FILE) or os.stat(HISTORY_FILE).st_size == 0:
        # If file does not exist or is empty, create it with an empty dictionary
        with open(HISTORY_FILE, "w") as file:
            json.dump({}, file)
        return {}

    with open(HISTORY_FILE, "r") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            # If file is corrupted, reset it
            with open(HISTORY_FILE, "w") as file:
                json.dump({}, file)
            return {}

def save_history(history):
    """Save the updated history to history.json."""
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file, indent=4)

def clean_old_history(history):
    """Remove history older than 7 days."""
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    for user in list(history.keys()):
        for date in list(history[user].keys()):
            if date < seven_days_ago:
                del history[user][date]

        # Remove user if they have no remaining history
        if not history[user]:
            del history[user]

    return history

@app.route('/store-search', methods=['POST'])
def store_search():
    """Store chatbot history for the logged-in user, ensuring 7-day retention."""
    data = request.json
    print("received data:", data)
    
    email = data.get("user_email")
    question = data.get("question")
    answer = data.get("answer")

    if not email or not question or not answer:
        print("Error: Invalid data received!")
        return jsonify({"error": "Invalid data"}), 400

    history = load_history()

    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")

    # Ensure user history exists
    if email not in history:
        history[email] = {}

    # Ensure date entry exists
    if today not in history[email]:
        history[email][today] = []

    # Add new entry
    history[email][today].append({"question": question, "answer": answer})
    print("Updated history:")

    # Clean old data
    history = clean_old_history(history)

    # Save back to file
    save_history(history)
    print("History saved!")

    return jsonify({"message": "History saved successfully"}), 200

import sys
# Route to fetch user history
@app.route('/get-history', methods=['GET'])
def get_history():
    user_email = request.args.get('user_email')
    print(f"Fetching history for user: {user_email}")  # Debugging print
    sys.stdout.flush()  # Ensure immediate output

    if not user_email:
        return jsonify({"error": "User email is required"}), 400

    #history_file = os.path.join(HISTORY_FILE, f"{user_email}.json")
    history_file = "history.json"

    if not os.path.exists(history_file):
        return jsonify({})  # Return empty history if no file exists

    with open(history_file, 'r') as file:
        history = json.load(file)
    
    user_history = history.get(user_email, {})
    sys.stdout.flush()
    return jsonify(user_history)

@app.route('/history/<user_email>/<date>', methods=['GET'])
def get_history_by_date(user_email, date):
    # Ensure history file exists
    if not os.path.exists(HISTORY_FILE):
        return jsonify([])  # Return empty array if file doesn't exist

    # Load the entire history file (shared for all users)
    with open(HISTORY_FILE, 'r') as file:
        history_data = json.load(file)

    # Extract user-specific history
    user_history = history_data.get(user_email, {})

    # Get only the requested date's history
    day_history = user_history.get(date, [])

    return jsonify(day_history)  # Return the chat history for the selected date


@app.route('/', methods=['GET'])
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True, threaded=False)