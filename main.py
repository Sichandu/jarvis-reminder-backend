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
    allow_origins=["*"],        # 🔒 In production, replace with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Firebase Admin Init ──────────────────────────────────────
# Place your Firebase service account JSON at: serviceAccountKey.json
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

reminders = []   # In-memory list; swap for a DB in production

# ── Models ───────────────────────────────────────────────────
class Reminder(BaseModel):
    token: str
    text: str
    dueTime: str   # ISO 8601 string, e.g. "2025-06-01T14:30:00"

class TokenRegistration(BaseModel):
    token: str

# ── Push Sender ───────────────────────────────────────────────
def send_push(token: str, text: str):
    """Send an FCM push notification with both notification + data fields."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title="JARVIS Reminder",
                body=text,
            ),
            data={
                "speak": text,   # Front-end reads this to trigger TTS
                "title": "JARVIS Reminder",
                "body": text,
            },
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title="JARVIS Reminder",
                    body=text,
                    icon="/icons/icon-192.png",
                    badge="/icons/icon-192.png",
                    vibrate=[200, 100, 200],
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link="/"   # URL to open on notification click
                ),
            ),
            token=token,
        )
        response = messaging.send(message)
        print(f"✅ Push sent: {response}")
    except Exception as e:
        print(f"❌ Push error: {e}")

# ── Background Scheduler ──────────────────────────────────────
def scheduler():
    """Polls every 5 seconds and fires any overdue reminders."""
    while True:
        now = datetime.now()
        for r in reminders[:]:
            try:
                due = datetime.fromisoformat(r["dueTime"])
                if now >= due:
                    print(f"🔥 Triggering: {r['text']} (due {due})")
                    send_push(r["token"], r["text"])
                    reminders.remove(r)
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                reminders.remove(r)   # Remove malformed entries
        time.sleep(5)

threading.Thread(target=scheduler, daemon=True).start()

# ── Routes ────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "pending_reminders": len(reminders)}

@app.post("/set-reminder")
def set_reminder(reminder: Reminder):
    print(f"📥 Reminder received: {reminder}")
    reminders.append(reminder.dict())
    return {"status": "scheduled", "dueTime": reminder.dueTime}

@app.post("/register-token")
def register_token(data: TokenRegistration):
    """Endpoint to store FCM token (extend to save in DB)."""
    print(f"📱 Token registered: {data.token[:20]}...")
    return {"status": "registered"}

@app.post("/test-push")
def test_push(data: Reminder):
    """Immediately send a test push — useful during development."""
    send_push(data.token, data.text)
    return {"status": "sent"}