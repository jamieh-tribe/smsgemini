import os
import datetime
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types
from google.cloud import firestore
from googleapiclient.discovery import build # Required for Calendar API

app = Flask(__name__)

# Initialize Firestore
db = firestore.Client()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Initialize Calendar Service
calendar_service = build('calendar', 'v3')

def get_upcoming_events(calendar_id='jamie@tribefinancial.com.au'):
    """Helper to fetch the next 5 events from your shared calendar."""
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = calendar_service.events().list(
            calendarId=calendar_id, 
            timeMin=now,
            maxResults=5, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events found."
            
        summary = "Upcoming Calendar Events:\n"
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary += f"- {event['summary']} (Starts: {start})\n"
        return summary
    except Exception as e:
        print(f"Calendar Error: {e}")
        return "Could not access calendar. Ensure it is shared with the service account."

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    user_phone = request.form.get('From')
    user_text = request.form.get('Body')

    try:
        # 1. Get history from Firestore (FREE)
        history_ref = db.collection("chats").document(user_phone).collection("messages")
        docs = history_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(4).stream()
        
        history_context = ""
        for doc in reversed(list(docs)):
            msg = doc.to_dict()
            history_context += f"{msg['role']}: {msg['content']}\n"

        # 2. Check if user is asking about their schedule
        calendar_context = ""
        if any(word in user_text.lower() for word in ["calendar", "schedule", "today", "tomorrow", "busy"]):
            calendar_context = get_upcoming_events()

        # 3. Call Gemini 2.5 Flash
        # We inject the calendar_context directly into the prompt if relevant
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"History:\n{history_context}\n{calendar_context}\nUser: {user_text}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "You are a warm, friendly assistant. Use Celsius/metric."
                    "Only greet by name occasionally. You can use warm and friendly greetings such as 'Hey Jamie', but vary your greetings."
                    "When considering weather updates, prioritise weather from the https://www.bom.gov.au/"
                    "When considering surf conditions updates, prioritise data from Surfline and Swellnet."
                    "If calendar information is provided in the prompt, use it to answer questions about the user's schedule."
                )
            )
        )
        reply_text = response.text

        # 4. Save to Firestore
        history_ref.add({
            "role": "user", 
            "content": user_text, 
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        history_ref.add({
            "role": "model", 
            "content": reply_text, 
            "timestamp": firestore.SERVER_TIMESTAMP
        })

    except Exception as e:
        print(f"Error: {e}")
        reply_text = "Sorry, I had a little trouble with my memory. Try again?"

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
