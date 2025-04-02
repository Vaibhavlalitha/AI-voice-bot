import speech_recognition as sr
from gtts import gTTS
import sqlite3
import datetime
import tempfile
import os
import pygame  # Changed audio backend

# Initialize pygame mixer once
pygame.mixer.init()

def speak(text):
    try:
        with tempfile.NamedTemporaryFile(suffix='lillyvoice.mp3', delete=False) as fp:
            temp_file = fp.name

        tts = gTTS(text=text, lang='en', tld='com')
        tts.save(temp_file)

        # New audio playback using pygame
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    except Exception as e:
        print(f"Error in speech synthesis: {e}")
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
# Improved listen function with timeout
def listen():
    recognizer = sr.Recognizer()
    while True:
        with sr.Microphone() as source:
            try:
                print("Listening...")
                recognizer.adjust_for_ambient_noise(source)
                audio = recognizer.listen(source, timeout=8)
                text = recognizer.recognize_google(audio)
                print(f"Recognized: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                speak("I didn't hear anything. Please try again.")
            except sr.UnknownValueError:
                speak("Couldn't understand audio. Please repeat.")
            except sr.RequestError as e:
                speak("Could not request results; check your internet connection.")
                return None

# Date validation function
def validate_date(date_str):
    try:
        datetime.datetime.strptime(date_str, "%d %B %Y")
        return True
    except ValueError:
        return False

# Time validation function
def validate_time(time_str):
    try:
        datetime.datetime.strptime(time_str.upper(), "%I:%M %p")
        return True
    except ValueError:
        return False

def schedule_appointment():
    try:
        conn = sqlite3.connect('appointments.db')
        cursor = conn.cursor()
        
        speak("Hi there, I am Victor. How may I help you today?")

        # Get name
        while True:
            speak("Please say your full name.")
            name = listen()
            if name and len(name.split()) >= 2:
                break
            speak("Please provide both first and last name.")

        # Get date
        while True:
            speak("What date would you like to book? Example: 15 July 2023")
            date = listen()
            if date and validate_date(date):
                break
            speak("Invalid date format. Please try again.")

        # Get time
        while True:
            speak("What time would you like to book? Example: 2:30 PM")
            time = listen()
            if time and validate_time(time):
                break
            speak("Invalid time format. Please try again.")

        # Get reason
        while True:
            speak("Please describe the reason for your visit.")
            reason = listen()
            if reason and len(reason) > 5:
                break
            speak("Please provide a more detailed reason.")

        # Database operation
        cursor.execute('''INSERT INTO appointments 
                       (name, date, time, reason) 
                       VALUES (?, ?, ?, ?)''', 
                       (name, date, time, reason))
        conn.commit()

        confirmation = f"""
        Appointment confirmed for {name}:
        Date: {date}
        Time: {time}
        Reason: {reason}
        Thank you for using our service!
        """
        speak(confirmation)
        print(confirmation)

    except Exception as e:
        speak("An error occurred. Please try again later.")
        print(f"Error: {str(e)}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    schedule_appointment()