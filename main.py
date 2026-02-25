import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the Gemini Client
# Uses the API Key you provided in Render's Environment Variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=['GET'])
def health_check():
    """Simple route to verify the server is reachable via browser"""
    return "Gemini 3 SMS Bot is Online!", 200

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    """Triggered when a text is sent to your Twilio number"""
    user_message = request.form.get('Body')
    print(f"Incoming SMS: {user_message}")

    try:
        # Using the flagship Gemini 3 Flash model
        # Previous 2.0 models were discontinued for new projects on Feb 17, 2026
        response = client.models.generate_content(
            model="models/gemini-3-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction="You are a concise SMS assistant. Use Google Search for real-time info. Keep answers under 300 characters."
            )
        )
        reply_text = response.text
    except Exception as e:
        # Logs the specific API or Logic error to Render Logs
        print(f"REAL ERROR: {e}") 
        reply_text = "I'm online, but Gemini had an issue with that request. Checking my logs!"

    # Wrap the response in TwiML for Twilio to deliver
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    # Dynamically binds to the port provided by Render
    # This prevents the 'No open HTTP ports detected' error
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
