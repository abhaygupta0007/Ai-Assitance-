import os
import threading
import webbrowser
import requests
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from customtkinter import CTkImage
import speech_recognition as sr
import pyttsx3
from openai import OpenAI
import ctypes
import sqlite3
from tkinter import messagebox
from datetime import datetime


OPENAI_API_KEY = " "
NEWS_API_KEY = "your_news_api_key_here"

client = OpenAI(api_key=OPENAI_API_KEY)
recognizer = sr.Recognizer()
engine = pyttsx3.init()

command_mode = False
listening_enabled = True

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_user_count():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def speak(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Speech Error: {e}")

def change_volume(delta):
    for _ in range(5):
        if delta > 0:
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
        else:
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)

def aiProcess(command):
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are Alpha, a helpful assistant like Alexa. Respond briefly."},
                {"role": "user", "content": command}
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI Error: {e}"

def processCommand(c):
    cl = c.lower()

    if "open google" in cl:
        speak("Opening Google.")
        webbrowser.open("https://google.com")
        return "Opening Google."
    elif "open youtube" in cl:
        speak("Opening YouTube.")
        webbrowser.open("https://youtube.com")
        return "Opening YouTube."
    elif "play" in cl:
        song = cl.replace("play", "").strip()
        if song:
            webbrowser.open(f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}")
            speak(f"Searching and playing {song} on YouTube")
            return f"Playing {song} on YouTube"
    elif "news" in cl:
        try:
            r = requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}")
            if r.status_code == 200:
                articles = r.json().get('articles', [])
                titles = [a['title'] for a in articles[:5]]
                for t in titles:
                    speak(t)
                return "\n".join(titles)
            else:
                speak("Couldn't fetch news right now.")
                return "Couldn't fetch news right now."
        except Exception as e:
            speak("Error fetching news.")
            return f"Error fetching news: {e}"
    elif "shutdown pc" in cl:
        speak("Shutting down your computer.")
        os.system("shutdown /s /t 1")
        return "Shutting down PC."
    elif "restart pc" in cl:
        speak("Restarting your computer.")
        os.system("shutdown /r /t 1")
        return "Restarting PC."
    elif "open chrome" in cl:
        chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
        if os.path.exists(chrome_path):
            os.startfile(chrome_path)
            speak("Opening Chrome.")
            return "Opening Chrome."
        else:
            speak("Chrome not found.")
            return "Chrome not found."
    elif "increase volume" in cl:
        change_volume(+10)
        speak("Volume increased.")
        return "Volume increased."
    elif "decrease volume" in cl:
        change_volume(-10)
        speak("Volume decreased.")
        return "Volume decreased."
    else:
        output = aiProcess(c)
        speak(output)
        return output

def listen(log_func):
    global command_mode, listening_enabled
    if not listening_enabled:
        return
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            if not command_mode:
                log_func("Listening for wake word 'Alpha'...")
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=4)
                word = recognizer.recognize_google(audio).lower()
                if "alpha" in word:
                    speak("Yes, I'm here.")
                    log_func("Wake word detected: Alpha")
                    command_mode = True
            else:
                log_func("Listening for command...")
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=8)
                command = recognizer.recognize_google(audio).lower()
                log_func(f"You said: {command}")

                if command in ["stop", "exit", "quit"]:
                    command_mode = False
                    speak("Okay, going to sleep.")
                    log_func("Assistant paused.")
                else:
                    output = processCommand(command)
                    if output:
                        log_func(f"Assistant: {output}")
    except Exception as e:
        log_func(f"Error: {e}")

def threaded_listen(log_func):
    def loop_listen():
        while True:
            if listening_enabled:
                listen(log_func)
            threading.Event().wait(0.5)
    threading.Thread(target=loop_listen, daemon=True).start()

def start_assistant(username):
    app = ctk.CTk()
    app.title(f"Alpha Voice Assistant - {username}")
    app.attributes("-fullscreen", True)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    try:
        avatar_img = Image.open("ai.jpg").resize((200, 200))
        avatar_ctk = CTkImage(light_image=avatar_img, size=(200, 200))
        avatar_label = ctk.CTkLabel(app, image=avatar_ctk, text="")
        avatar_label.place(x=20, y=20)
    except Exception as e:
        print("Avatar image not loaded:", e)

    title = ctk.CTkLabel(app, text="Alpha Voice Assistant", font=("Arial", 24))
    title.place(x=300, y=50)

    
    log_box = ctk.CTkTextbox(app, width=800, height=450)
    log_box.place(x=300, y=100)

    def log(message):
        timestamp = datetime.now().strftime("[%I:%M:%S %p]")
        log_box.insert(tk.END, f"{timestamp} {message}\n")
        log_box.see(tk.END)

    def activate_assistant():
        global listening_enabled
        listening_enabled = True
        log("Assistant activated.")
        speak("Assistant is now listening.")

    def hold_assistant():
        global listening_enabled
        listening_enabled = False
        log("Assistant paused.")
        speak("Assistant is now on hold.")

    ctk.CTkButton(app, text="Activate Assistant", command=activate_assistant, width=150).place(x=150, y=520)
    ctk.CTkButton(app, text="Hold Assistant", command=hold_assistant, width=150).place(x=320, y=520)
    ctk.CTkButton(app, text="Exit", command=app.quit, width=150).place(x=490, y=520)

    user_count = get_user_count()
    count_label = ctk.CTkLabel(app, text=f"Total Registered Users: {user_count}", font=("Arial", 14))
    count_label.place(x=20, y=650)

    log("Alpha Initialized...")
    threaded_listen(log)
    app.mainloop()

def show_login_window():
    login = ctk.CTk()
    login.title("Alpha Assistant - Login")
    login.geometry("400x400")
    ctk.set_appearance_mode("dark")

    ctk.CTkLabel(login, text="Login to Alpha", font=("Arial", 24)).pack(pady=20)
    username_entry = ctk.CTkEntry(login, placeholder_text="Username", width=250)
    username_entry.pack(pady=10)
    password_entry = ctk.CTkEntry(login, placeholder_text="Password", width=250, show="*")
    password_entry.pack(pady=10)

    def login_user():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if verify_user(username, password):
            messagebox.showinfo("Success", f"Welcome {username}!")
            login.destroy()
            start_assistant(username)
        else:
            messagebox.showerror("Error", "Invalid credentials!")

    def open_signup():
        login.destroy()
        show_signup_window()

    ctk.CTkButton(login, text="Login", command=login_user, width=150).pack(pady=10)
    ctk.CTkButton(login, text="Signup", command=open_signup, width=150).pack(pady=10)
    login.mainloop()

def show_signup_window():
    signup = ctk.CTk()
    signup.title("Alpha Assistant - Signup")
    signup.geometry("400x400")
    ctk.set_appearance_mode("dark")

    ctk.CTkLabel(signup, text="Create Account", font=("Arial", 24)).pack(pady=20)
    username_entry = ctk.CTkEntry(signup, placeholder_text="Username", width=250)
    username_entry.pack(pady=10)
    password_entry = ctk.CTkEntry(signup, placeholder_text="Password", width=250, show="*")
    password_entry.pack(pady=10)

    def signup_user():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if username and password:
            if add_user(username, password):
                messagebox.showinfo("Success", "Account created! Please login.")
                signup.destroy()
                show_login_window()
            else:
                messagebox.showerror("Error", "Username already exists!")
        else:
            messagebox.showwarning("Warning", "Please fill all fields!")

    ctk.CTkButton(signup, text="Signup", command=signup_user, width=150).pack(pady=10)
    ctk.CTkButton(signup, text="Back to Login", command=lambda: [signup.destroy(), show_login_window()], width=150).pack(pady=10)
    signup.mainloop()

if __name__ == "__main__":
    init_db()
    show_login_window()
