import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model for Chat History
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(10), nullable=False) # 'user' or 'model'

# Create the database tables
with app.app_context():
    db.create_all()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    user_phone = request.form.get('From')
    user_text = request.form.get('Body')

    # 1. Save user message to DB
    new_msg = ChatHistory(phone_number=user_phone, message=user_text, role='user')
    db.session.add(new_msg)
    db.session.commit()

    # 2. Retrieve last 5 messages for context
    past_chats = ChatHistory.query.filter_by(phone_number=user_phone).order_by(ChatHistory.id.desc()).limit(6).all()
    history_context = "\n".join([f"{c.role}: {c.message}" for c in reversed(past_chats)])

    try:
        response = client.models.generate_content(
            model="models/gemini-3-flash",
            contents=f"Conversation History:\n{history_context}\n\nUser: {user_text}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction="You are an Australian assistant. Use metric units (Celsius, km) and Aussie slang occasionally. Use the context to remember the user."
            )
        )
        reply_text = response.text
    except Exception as e:
        reply_text = "Crikey, I've had a bit of a glitch. Try again shortly!"

    # 3. Save model response to DB
    bot_msg = ChatHistory(phone_number=user_phone, message=reply_text, role='model')
    db.session.add(bot_msg)
    db.session.commit()

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
