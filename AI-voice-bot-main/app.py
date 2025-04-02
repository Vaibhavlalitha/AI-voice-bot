from flask import Flask, jsonify
import speech_recognition as sr
import asyncio
import edge_tts
import sqlite3
import datetime
import calendar
from pydub import AudioSegment
from pydub.playback import play
import threading
import tempfile
import os
import logging
from flask_cors import CORS
import re

# Setup Flask App
app = Flask(__name__)
CORS(app)  # Enable CORS

# Configure Logging
logging.basicConfig(level=logging.INFO)

# Database Setup
def init_db():
    conn = sqlite3.connect("appointments.db")
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS appointments
           (id INTEGER PRIMARY KEY, name TEXT, date TEXT, time TEXT, reason TEXT)"""
    )
    conn.commit()
    conn.close()

init_db()  # Ensure DB is ready at start

# Function to play AI-generated voice
async def speak(text):
    try:
        temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
        tts = edge_tts.Communicate(text, voice="en-US-JennyNeural")
        await tts.save(temp_audio)
        audio = AudioSegment.from_file(temp_audio, format="mp3")
        play(audio)
        os.remove(temp_audio)  # Clean up file after playing
    except Exception as e:
        logging.error(f"Error in speech synthesis: {e}")

# Function to recognize speech
def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source)
            text = recognizer.recognize_google(audio).lower()
            print(f"You said: {text}")
            return text
        except sr.UnknownValueError:
            asyncio.run(speak("Sorry, I didn't catch that. Can you repeat?"))
            return ""
        except sr.RequestError:
            asyncio.run(speak("There seems to be a network issue. Please check your connection!"))
            return ""

# Function to validate and process date input
def validate_date(date_text):
    today = datetime.datetime.today()
    weekdays = {day.lower(): idx for idx, day in enumerate(calendar.day_name)}
    ordinal_suffixes = {"st", "nd", "rd", "th"}

    if date_text in ["today", "tomorrow"]:
        appointment_date = today if date_text == "today" else today + datetime.timedelta(days=1)
        return appointment_date.strftime("%d %B %Y")

    # Handling "next Sunday", "next Monday"...
    words = date_text.split()
    if "next" in words and any(word in weekdays for word in words):
        for word in words:
            if word in weekdays:
                target_weekday = weekdays[word]
                days_until = (target_weekday - today.weekday() + 7) % 7 or 7
                appointment_date = today + datetime.timedelta(days=days_until)
                return appointment_date.strftime("%d %B %Y")
    
    # Handling "31st March", "22nd April"...
    match = re.match(r"(\d{1,2})(st|nd|rd|th)?\s*(\w+)?", date_text)
    if match:
        day, _, month = match.groups()
        try:
            if month:
                appointment_date = datetime.datetime.strptime(f"{day} {month} {today.year}", "%d %B %Y")
            else:
                appointment_date = datetime.datetime.strptime(f"{day} {today.strftime('%B')} {today.year}", "%d %B %Y")
            if appointment_date.date() >= today.date():
                return appointment_date.strftime("%d %B %Y")
        except ValueError:
            pass
    
    return None

# Function to validate and process time input
def validate_time(time_text):
    try:
        time_text = time_text.replace(".", "").strip().replace("am", " AM").replace("pm", " PM")
        appointment_time = datetime.datetime.strptime(time_text, "%I %p").time()
    except ValueError:
        try:
            appointment_time = datetime.datetime.strptime(time_text, "%I:%M %p").time()
        except ValueError:
            return None

    if datetime.time(10, 0) <= appointment_time <= datetime.time(18, 0):
        return appointment_time.strftime("%I:%M %p")
    return None

# Function to save appointment in the database
def save_appointment(name, date, time, reason):
    conn = sqlite3.connect("appointments.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO appointments (name, date, time, reason) VALUES (?, ?, ?, ?)",
                   (name, date, time, reason))
    conn.commit()
    conn.close()

# Function to schedule an appointment
def schedule_appointment():
    asyncio.run(speak("Hello! I'm Lilly, your friendly AI assistant. Let's get you an appointment!"))
    
    asyncio.run(speak("May I have your name, please?"))
    name = listen()
    if name.lower() == "stop":
        asyncio.run(speak("Okay, stopping now. Have a great day!"))
        return
    
    asyncio.run(speak(f"Got it, {name}! What date would you like to book?"))
    while True:
        date_input = listen()
        if date_input.lower() == "stop":
            asyncio.run(speak("Alright, stopping now! Take care."))
            return
        appointment_date = validate_date(date_input)
        if appointment_date:
            break
        asyncio.run(speak("That doesn't seem like a valid date. Please try again."))
    
    asyncio.run(speak(f"Awesome, {name}. What time works best for you?"))
    while True:
        time_input = listen()
        if time_input.lower() == "stop":
            asyncio.run(speak("Okay, stopping now. See you next time!"))
            return
        appointment_time = validate_time(time_input)
        if appointment_time:
            break
        asyncio.run(speak("Please pick a time between 10 AM and 6 PM."))
    
    asyncio.run(speak("Lastly, what's the reason for your visit?"))
    reason = listen()
    if reason.lower() == "stop":
        asyncio.run(speak("No problem! Stay safe and healthy!"))
        return
    save_appointment(name, appointment_date, appointment_time, reason)
    
    asyncio.run(speak(f"Your appointment is confirmed, {name}, for {appointment_date} at {appointment_time}."))

# API route to start voice appointment
@app.route("/start-appointment", methods=["POST"])
def start_appointment():
    threading.Thread(target=schedule_appointment).start()
    return jsonify({"message": "Voice appointment process started."})

if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8080)), debug=True)
