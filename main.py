import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=['GET'])
def health_check():
    """Critical for Render's health check to pass"""
    return "Gemini 2.5 SMS Bot is Online!", 200

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    user_message = request.form.get('Body')
    print(f"Incoming SMS: {user_message}")

    try:
        # Switching to Gemini 2.5 Flash as requested
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction="You are a concise SMS assistant. Use Google Search for real-time info. Keep answers under 300 characters."
            )
        )
        reply_text = response.text
    except Exception as e:
        print(f"REAL ERROR: {e}") 
        reply_text = "I'm online, but Gemini 2.5 had an issue. Checking logs!"

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    # Render provides the PORT environment variable dynamically
    # We MUST use it to stop the 'No open HTTP ports' loop
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
