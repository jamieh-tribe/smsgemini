import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types
from google.cloud import firestore

app = Flask(__name__)

# Initialize Firestore
# It will automatically find the JSON file via GOOGLE_APPLICATION_CREDENTIALS
db = firestore.Client()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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

        # 2. Call Gemini 2.5 Flash
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"History:\n{history_context}\nUser: {user_text}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "You are a warm, friendly assistant. Use Celsius/metric."
                    "Only greet by name occasionally. You can use warm and friendly greetings such as 'Hey Jamie', but vary your greetings."
                    "When considering weather updates, prioritise weather from the https://www.bom.gov.au/"
                    "When considering surf conditions updates, prioritise data from Surfline and Swellnet." 
                )
            )
        )
        reply_text = response.text

        # 3. Save to Firestore
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
    # Use the port provided by Google, or default to 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
