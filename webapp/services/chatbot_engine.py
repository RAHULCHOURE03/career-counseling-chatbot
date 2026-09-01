"""The existing TensorFlow intent chatbot, isolated from Flask routes."""

import json
import pickle
import random
import re
from pathlib import Path

import nltk
import numpy as np
from deep_translator import GoogleTranslator
from nltk.stem import WordNetLemmatizer
from tensorflow.keras.models import load_model

PROJECT_ROOT = Path(__file__).resolve().parents[2]
lemmatizer = WordNetLemmatizer()
_model = None
_intents = None
_words = None
_classes = None


def _load_assets():
    """Load model assets only when a chat request needs them."""
    global _model, _intents, _words, _classes
    if _model is None:
        _model = load_model(str(PROJECT_ROOT / "chatbot_model.keras"))
        _intents = json.loads((PROJECT_ROOT / "intents.json").read_text(encoding="utf8"))
        with (PROJECT_ROOT / "words.pkl").open("rb") as file:
            _words = pickle.load(file)
        with (PROJECT_ROOT / "classes.pkl").open("rb") as file:
            _classes = pickle.load(file)
    return _model, _intents, _words, _classes


def clean_up_sentence(sentence):
    return [lemmatizer.lemmatize(word.lower()) for word in nltk.word_tokenize(sentence)]


def bow(sentence, words):
    sentence_words = clean_up_sentence(sentence)
    return np.array([int(word in sentence_words) for word in words])


def predict_class(sentence, model, words, classes):
    input_data = np.array(
        [bow(sentence, words)],
        dtype=np.float32
    )

    predictions = model.predict(input_data, verbose=0)[0]
    matches = [[index, score] for index, score in enumerate(predictions) if score > 0.80]
    matches.sort(key=lambda item: item[1], reverse=True)
    if not matches:
        return [{"intent": "default", "probability": "0"}]
    return [
        {"intent": classes[index], "probability": str(score)}
        for index, score in matches
    ]


def get_response(predictions, intents):
    tag = predictions[0]["intent"]
    if tag == "default":
        return "Sorry! query not found, please ask the question related to the engineering field"
    for intent in intents["intents"]:
        if intent["tag"] == tag:
            return random.choice(intent["responses"])
    return "Sorry! I couldn't find a relevant answer. Please ask a question related to engineering education, admissions, exams, or careers."


def is_hinglish(text):
    is_latin = bool(re.fullmatch(r"[A-Za-z0-9 ?!.,'\"-]+", text.strip()))
    common_english_words = [
        "what", "is", "how", "are", "the", "you", "about", "engineering", "career"
    ]
    return is_latin and not any(word in text.lower() for word in common_english_words)

def safe_translate(text, target_language):
    try:
        translated = GoogleTranslator(source="auto", target=target_language).translate(text)
        if not translated or translated.startswith("Error "):
            return text
        return translated
    except Exception:
        return text

def reply(message):
    """Return a response from the current TensorFlow intent model."""
    model, intents, words, classes = _load_assets()

    translated_message = safe_translate(message, "en")
    detected_language = "hi" if message != translated_message or is_hinglish(message) else "en"
    processed_message = message if detected_language == "en" else translated_message

    response = get_response(
        predict_class(processed_message, model, words, classes),
        intents,
    )

    if detected_language == "hi":
        return safe_translate(response, "hi")

    return response