from fastapi import FastAPI
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, messaging
from datetime import datetime
import threading
import time
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 INIT FIREBASE ADMIN
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

reminders = []

class Reminder(BaseModel):
    token: str
    text: str
    dueTime: str

# 🔔 SEND PUSH (UPDATED)
def send_push(token, text):
    try:
        message = messaging.Message(
    notification=messaging.Notification(
        title="Jarvis Reminder",
        body=text
    ),
    data={
        "speak": text  # 🔥 IMPORTANT
    },
    webpush=messaging.WebpushConfig(
        notification=messaging.WebpushNotification(
            title="Jarvis Reminder",
            body=text,
            icon="/icons/icon-192.png"
        )
    ),
    token=token,
)

        response = messaging.send(message)
        print("✅ PUSH SENT:", response)

    except Exception as e:
        print("❌ PUSH ERROR:", e)

# ⏱️ SCHEDULER (UPDATED WITH LOGS)
def scheduler():
    while True:
        now = datetime.now()

        for r in reminders[:]:
            try:
                due = datetime.fromisoformat(r["dueTime"])
                print("⏳ Checking:", r["text"], "| Due:", due)

                if now >= due:
                    print("🔥 TRIGGERING:", r["text"])
                    send_push(r["token"], r["text"])
                    reminders.remove(r)

            except Exception as e:
                print("❌ ERROR:", e)

        time.sleep(5)

# START BACKGROUND THREAD
threading.Thread(target=scheduler, daemon=True).start()

@app.post("/set-reminder")
def set_reminder(reminder: Reminder):
    print("📥 RECEIVED:", reminder)
    reminders.append(reminder.dict())
    return {"status": "scheduled"}