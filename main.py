import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

# Database Configuration
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Model for Memory
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(30), nullable=False)
    message = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(10), nullable=False)

with app.app_context():
    db.create_all()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=['GET'])
def health_check():
    return "Friendly Gemini 3 Bot is Online!", 200

@app.route("/sms", methods=['POST'])
def reply_to_sms():
    user_phone = request.form.get('From')
    user_text = request.form.get('Body')

    try:
        # Retrieve recent history for context
        past_chats = ChatHistory.query.filter_by(phone_number=user_phone).order_by(ChatHistory.id.desc()).limit(4).all()
        history_context = "\n".join([f"{c.role}: {c.message}" for c in reversed(past_chats)])

        # Generate response with friendly instructions
        response = client.models.generate_content(
            model="models/gemini-3-flash",
            contents=f"History:\n{history_context}\nUser: {user_text}",
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "You are a warm and friendly personal assistant. "
                    "You are based in Australia, so always use Celsius for temperature and metric units (km, kg) for measurements. "
                    "Use the provided conversation history to remember the user's details and name. "
                    "Be helpful, kind, and keep your responses concise (under 300 characters)."
                )
            )
        )
        reply_text = response.text

        # Save to Database
        db.session.add(ChatHistory(phone_number=user_phone, message=user_text, role='user'))
        db.session.add(ChatHistory(phone_number=user_phone, message=reply_text, role='model'))
        db.session.commit()

    except Exception as e:
        print(f"Error: {e}")
        reply_text = "I'm so sorry, I'm having a little trouble connecting right now. Could you try again in a moment?"

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return str(twiml)

if __name__ == "__main__":
    # Render provides the port in the environment; 
    # we use 5000 as a fallback only for local testing.
    port = int(os.environ.get("PORT", 5000))
    # host MUST be 0.0.0.0 to be visible to Render's network
    app.run(host='0.0.0.0', port=port)
