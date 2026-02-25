import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# This connects to the Gemini API
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    # 1. Get the text you sent from your phone
    user_message = request.form.get('Body')
    
    # 2. Tell Gemini to search the web and be brief (SMS is short!)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction="You are a helpful SMS assistant. Keep answers under 300 characters.",
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    
    # 3. Format the answer for Twilio
    twiml = MessagingResponse()
    twiml.message(response.text)
    return str(twiml)

if __name__ == "__main__":
    # Start the server
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
