import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Initialize the Gemini Client using your API Key from Render's Environment Variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    # 1. Get the text message sent to the Twilio number
    user_message = request.form.get('Body')
    
    try:
        # 2. Ask Gemini 2.0 Flash to respond using Google Search
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction="You are a concise SMS assistant. Use Google Search for real-time info. Keep answers under 320 characters.",
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        reply_text = response.text

    except Exception as e:
        # If something goes wrong (like a temporary API hiccup)
        print(f"Error: {e}")
        reply_text = "Sorry, I encountered an error. Please try again in a moment."

    # 3. Format and send the SMS back via Twilio
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    # Render provides the PORT environment variable automatically
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
