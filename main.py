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
    return "Gemini SMS Bot is Online!", 200

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    user_message = request.form.get('Body')
    print(f"Received SMS: {user_message}")

    try:
        # Ask Gemini 2.0 Flash
        # We use a simplified config to ensure stability
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction="You are a helpful assistant. Keep answers under 300 characters."
            )
        )
        reply_text = response.text
    except Exception as e:
        # This print line is KEY. It will show the real error in Render Logs.
        print(f"REAL ERROR: {e}") 
        reply_text = "I'm connected, but Gemini gave an error. Check logs."

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
