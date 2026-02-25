import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the Gemini Client
# Ensure GEMINI_API_KEY is set in Render Environment Variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=['GET'])
def health_check():
    """Verify the server is online via browser"""
    return "Gemini 3 SMS Bot is Online!", 200

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    """Handles incoming SMS from Twilio"""
    user_message = request.form.get('Body')
    print(f"Received SMS: {user_message}")

    try:
        # Using Gemini 3 Flash for real-time web search
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
        # Prints specific error to Render logs for debugging
        print(f"REAL ERROR: {e}") 
        reply_text = "I'm connected, but Gemini had an issue. Checking logs!"

    # Create the Twilio Response
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    # Render Starter tier provides the PORT variable; we default to 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
