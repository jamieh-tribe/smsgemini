import os
import threading
from flask import Flask, request
from twilio.rest import Client as TwilioClient
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize Clients
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
twilio_client = TwilioClient(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))

def ask_gemini_and_send_sms(user_message, to_number):
    try:
        # 1. Get answer from Gemini
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction="Concise SMS assistant. Use Google Search. Max 300 chars.",
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        
        # 2. Send the response as a NEW text message
        twilio_client.messages.create(
            body=response.text,
            from_=os.environ.get("TWILIO_NUMBER"),
            to=to_number
        )
    except Exception as e:
        print(f"Error in background task: {e}")

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    user_message = request.form.get('Body')
    from_number = request.form.get('From')

    # Start the background 'brain' so we can finish this request immediately
    thread = threading.Thread(target=ask_gemini_and_send_sms, args=(user_message, from_number))
    thread.start()

    # Tell Twilio "I've got it!" so it stops the 15-second timer
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
