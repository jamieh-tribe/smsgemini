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
    print(f"Received: {user_message}") # This will show in Render Logs

    try:
        # Ask Gemini 2.0 Flash with Google Search
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction="You are a concise SMS assistant. Use Google Search for real-time info. Keep answers under 300 characters.",
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        reply_text = response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        reply_text = "Sorry, I'm having trouble thinking right now. Try again?"

    # Send the response back to Twilio
    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    # Starter tier uses port 10000 by default
    app.run(host='0.0.0.0', port=10000)
