"""
voice_assistant.py (FIXED)
Stable offline TTS + online STT assistant.
"""

import speech_recognition as sr
import pyttsx3
import webbrowser
import datetime
import wikipedia
import pywhatkit
import subprocess
import os
import sys
import threading

# --------- Configuration ----------
ASSISTANT_NAME = "jarvis"
USE_WAKE_WORD = False
RATE = 150
LANG = "en"
# ----------------------------------

# ---------- TTS Setup -----------
engine = pyttsx3.init()
engine.setProperty("rate", RATE)

# Lock to prevent multiple runAndWait() calls
speak_lock = threading.Lock()

def speak(text):
    """Speak text safely (threaded but locked)."""
    def _safe_speak():
        with speak_lock:
            engine.stop()         # Clear any previous queue
            engine.say(text)
            engine.runAndWait()

    t = threading.Thread(target=_safe_speak)
    t.daemon = True
    t.start()

# ---------- STT Setup -----------
recognizer = sr.Recognizer()
microphone = sr.Microphone()


def listen(timeout=None, phrase_time_limit=8):
    """Listen from mic safely and return recognized text."""
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.6)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return None

    try:
        text = recognizer.recognize_google(audio, language=LANG)
        return text.lower()
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None


# ---------- Features -----------
def tell_time():
    now = datetime.datetime.now().strftime("%I:%M %p")
    speak(f"The time is {now}")
    print("Time:", now)


def wiki_search(query, sentences=2):
    try:
        summary = wikipedia.summary(query, sentences=sentences, auto_suggest=True, redirect=True)
        speak(summary)
        print("Wikipedia:", summary)
    except Exception as e:
        speak("I couldn't find that on Wikipedia.")
        print("Wikipedia error:", e)


def play_youtube(query):
    speak(f"Playing {query} on YouTube")
    try:
        pywhatkit.playonyt(query)
    except Exception as e:
        speak("Failed to play on YouTube.")
        print("YouTube error:", e)


def open_website(url):
    if not url.startswith("http"):
        url = "https://" + url
    speak(f"Opening {url}")
    webbrowser.open(url)


def open_app(path_or_command):
    speak("Opening application")
    try:
        if sys.platform.startswith("win"):
            os.startfile(path_or_command)
        else:
            subprocess.Popen(path_or_command, shell=True)
    except Exception as e:
        speak("Couldn't open the application.")
        print("Open app error:", e)


def run_shell(cmd):
    speak("Running command")
    try:
        res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True, timeout=8)
        print("Command output:\n", res)
        speak("Command executed.")
    except Exception as e:
        speak("Error running the command.")
        print("Shell error:", e)


# ---------- Command Parsing ----------
def parse_and_execute(text):
    if not text:
        speak("I didn't catch that.")
        return

    print("Heard:", text)

    # Greeting
    if any(g in text for g in ["hello", "hi", "hey"]):
        speak("Hello! How can I help you?")
        return

    # Time
    if "time" in text:
        tell_time()
        return

    # Wikipedia
    if any(kw in text for kw in ["who is", "what is", "tell me about"]):
        q = (
            text.replace("who is", "")
                .replace("what is", "")
                .replace("tell me about", "")
                .strip()
        )
        if q:
            wiki_search(q)
        else:
            speak("What should I look up?")
        return

    # Play YouTube
    if text.startswith("play "):
        q = text.replace("play", "").replace("on youtube", "").strip()
        if q:
            play_youtube(q)
        else:
            speak("What should I play?")
        return

    # Open website
    if "open " in text:
        t = text.replace("open", "").strip()

        if "youtube" in t:
            open_website("youtube.com")
            return
        if "google" in t:
            open_website("google.com")
            return
        if ".com" in t:
            open_website(t)
            return

    # Open application
    if "open app" in text or "open application" in text or "open folder" in text:
        app_map = {
            "notepad": "notepad",
            "calculator": "calc",
            "vscode": "code"
        }
        for name, cmd in app_map.items():
            if name in text:
                open_app(cmd)
                return

        speak("Which application do you want to open?")
        return

    # Shell command
    if text.startswith("run ") or text.startswith("execute "):
        cmd = text.replace("run", "").replace("execute", "").strip()
        run_shell(cmd)
        return

    # Repeat
    if "say" in text:
        to_say = text.split("say", 1)[1].strip()
        if to_say:
            speak(to_say)
        return

    # Fallback: Google search
    speak("I can search that for you.")
    webbrowser.open("https://www.google.com/search?q=" + text.replace(" ", "+"))


# ---------- Main Loop ----------
def main_loop():
    speak("Jarvis is ready. Press Enter to speak.")

    try:
        while True:
            if USE_WAKE_WORD:
                print("Listening for wake word...")
                heard = listen(timeout=4, phrase_time_limit=3)
                if heard and ASSISTANT_NAME in heard:
                    speak("Yes?")
                    cmd = listen(timeout=5, phrase_time_limit=8)
                    parse_and_execute(cmd)
            else:
                input("Press Enter and speak (Ctrl+C to exit)... ")
                speak("Listening...")
                text = listen(timeout=5, phrase_time_limit=8)
                parse_and_execute(text)

    except KeyboardInterrupt:
        speak("Shutting down. Goodbye!")
        print("\nExiting...")


if __name__ == "__main__":
    main_loop()