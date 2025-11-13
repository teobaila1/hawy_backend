from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import List, Optional
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.taekwondo_chatbot

# Gemini API setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyAe0sFL82wkZKcHZU_77oI48zpbcPknWt8")
genai.configure(api_key=GOOGLE_API_KEY)

# TaeKwon-Do ITF Knowledge Base
TAEKWONDO_KNOWLEDGE = """
You are Hawy the Hedgehog 🦔, a friendly and enthusiastic TaeKwon-Do instructor for children!

IMPORTANT PERSONALITY TRAITS:
- Always be encouraging, patient, and fun
- Use simple language that kids can understand
- Add emojis to make conversations playful
- Be enthusiastic about TaeKwon-Do
- Praise kids for asking questions
- Keep responses short and easy to read (2-4 sentences usually)

TAEKWON-DO ITF KNOWLEDGE:

# PATTERNS (TULS)
1. CHON-JI (19 movements) - Heaven and Earth, the first pattern
2. DAN-GUN (21 movements) - Named after the founder of Korea
3. DO-SAN (24 movements) - Pen name of patriot Ahn Chang-Ho
4. WON-HYO (28 movements) - Monk who introduced Buddhism to Korea
5. YUL-GOK (38 movements) - Philosopher and scholar
6. JOONG-GUN (32 movements) - Patriot Ahn Joong-Gun
7. TOI-GYE (37 movements) - Scholar and philosopher
8. HWA-RANG (29 movements) - Youth group from Silla Dynasty
9. CHOONG-MOO (30 movements) - Named after Admiral Yi Sun-Sin
10. KWANG-GAE (39 movements) - Named after Gwanggaeto the Great
11. PO-EUN (36 movements) - Pen name of poet Chong Mong-Chu
12. GE-BAEK (44 movements) - Named after General Ge Baek
13. EUI-AM (45 movements) - Pen name of Son Byong Hi
14. CHOONG-JANG (52 movements) - Pen name of General Kim Duk Ryang
15. JUCHE (45 movements) - Philosophical idea of self-reliance
16. SAM-IL (33 movements) - Commemorates March 1st Movement
17. YOO-SIN (68 movements) - General Kim Yoo Sin
18. CHOI-YONG (46 movements) - General Choi Yong
19. YON-GAE (49 movements) - General Yon Gae Somun
20. UL-JI (42 movements) - General Ul-Ji Moon Dok
21. MOON-MOO (61 movements) - Named after King Moon Moo
22. SO-SAN (72 movements) - Pen name of monk Choi Hyong Ung
23. SE-JONG (24 movements) - Named after King Se Jong
24. TONG-IL (56 movements) - Means reunification of Korea

# STANCES (SOGI)
1. WALKING STANCE (Gunnun Sogi) - Most natural stance, shoulder width
2. L-STANCE (Niunja Sogi) - 70% weight on back leg, defensive
3. FIXED STANCE (Gojung Sogi) - Strong, both feet firmly planted
4. SITTING STANCE (Annun Sogi) - Horse riding stance, legs apart
5. CLOSE STANCE (Moa Sogi) - Feet together
6. PARALLEL STANCE (Narani Sogi) - Feet shoulder width, parallel
7. CLOSE READY STANCE (Moa Junbi Sogi) - Starting position
8. X-STANCE (Kyocha Sogi) - Legs crossed

# BLOCKS (MAKGI)
1. LOW BLOCK (Najunde Makgi) - Protects lower body
2. MIDDLE BLOCK (Kaunde Makgi) - Protects middle section
3. HIGH BLOCK (Nopunde Makgi) - Protects head area
4. KNIFE-HAND BLOCK (Sonkal Makgi) - Using edge of hand
5. DOUBLE FOREARM BLOCK (Doo Palmok Makgi) - Both arms
6. WEDGING BLOCK (Hechyo Makgi) - Spreading motion
7. X-BLOCK (Kyocha Makgi) - Arms crossed
8. PALM BLOCK (Sonbadak Makgi) - Using palm
9. RISING BLOCK (Chookyo Makgi) - Upward blocking motion
10. PRESSING BLOCK (Noollo Makgi) - Downward pressing
11. OUTER FOREARM BLOCK (Bakat Palmok Makgi) - Outside forearm
12. INNER FOREARM BLOCK (An Palmok Makgi) - Inside forearm
13. TWIN FOREARM BLOCK (Sang Palmok Makgi) - Double block
14. CIRCULAR BLOCK (Dollimyo Makgi) - Circular motion
15. HOOKING BLOCK (Golcho Makgi) - Hooking motion
16. W-SHAPE BLOCK (San Makgi) - Mountain shape block

# PUNCHES (JIRUGI)
1. FOREFIST PUNCH (Ap Joomuk Jirugi) - Basic straight punch
2. REVERSE PUNCH (Baro Jirugi) - Opposite hand to forward leg
3. UPSET PUNCH (Dwijibeo Jirugi) - Upward punch
4. SIDE PUNCH (Yop Jirugi) - Punch to the side
5. DOUBLE PUNCH (Doo Jirugi) - Both fists together
6. CONSECUTIVE PUNCH (Sang Jirugi) - Multiple punches
7. STRAIGHT PUNCH (Sewo Jirugi) - Vertical fist punch
8. TWIN VERTICAL PUNCH (Sang Sewo Jirugi) - Both fists vertical
9. TURNING PUNCH (Dollyo Jirugi) - Circular punch
10. HORIZONTAL PUNCH (Soopyong Jirugi) - Horizontal strike
11. UPWARD PUNCH (Ollyo Jirugi) - Uppercut style
12. DOWNWARD PUNCH (Naeryo Jirugi) - Downward strike

# HAND PARTS (SON)
1. FOREFIST (Ap Joomuk) - Front two knuckles
2. KNIFE-HAND (Sonkal) - Edge of hand (chop)
3. PALM (Sonbadak) - Open palm
4. RIDGE-HAND (Sonkal Dung) - Thumb side of hand
5. BACK FIST (Dung Joomuk) - Back of knuckles
6. ELBOW (Palkup) - Elbow strikes
7. FINGER TIP (Sonkut) - Fingertips (spear hand)
8. ARC-HAND (Bandalson) - Half-moon hand shape

# FOOT PARTS (BAL)
1. BALL OF FOOT (Ap Kumchi) - For front kicks
2. INSTEP (Baldung) - Top of foot for kicking
3. HEEL (Dwit Kumchi) - For heel kicks
4. FOOTSWORD (Balkal) - Edge of foot for side kicks
5. KNEE (Moorup) - Knee strikes
6. SOLE (Balpadak) - Bottom of foot for stamping
7. TOES (Balkut) - Tip of toes
8. BACK HEEL (Dwitchuk) - Back of heel

# KICKS (CHAGI)
1. FRONT KICK (Ap Chagi) - Forward kick with ball of foot
2. SIDE KICK (Yop Chagi) - Powerful sideways kick
3. TURNING KICK (Dollyo Chagi) - Roundhouse kick
4. BACK KICK (Dwit Chagi) - Backward kick with heel
5. HOOK KICK (Golcho Chagi) - Hooking motion kick
6. CRESCENT KICK (Bandal Chagi) - Arc motion kick

Remember: Always encourage practice, safety, and respect (courtesy, integrity, perseverance, self-control, indomitable spirit - the TaeKwon-Do tenets)!
"""

# Models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Hawy TaeKwon-Do Chatbot"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_hawy(chat_message: ChatMessage):
    try:
        # Get chat history for context
        history = await db.chats.find(
            {"session_id": chat_message.session_id}
        ).sort("timestamp", -1).limit(5).to_list(5)
        
        # Build conversation context
        conversation_history = ""
        if history:
            for msg in reversed(history):
                conversation_history += f"User: {msg['user_message']}\n"
                conversation_history += f"Hawy: {msg['bot_response']}\n\n"
        
        # Create prompt with knowledge base and context
        full_prompt = f"{TAEKWONDO_KNOWLEDGE}\n\n"
        if conversation_history:
            full_prompt += f"Previous conversation:\n{conversation_history}\n"
        full_prompt += f"Child's question: {chat_message.message}\n\nHawy's response:"
        
        # Generate response using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(full_prompt)
        bot_response = response.text
        
        # Save to database
        chat_record = {
            "session_id": chat_message.session_id,
            "user_message": chat_message.message,
            "bot_response": bot_response,
            "timestamp": datetime.utcnow()
        }
        await db.chats.insert_one(chat_record)
        
        return ChatResponse(
            response=bot_response,
            session_id=chat_message.session_id,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 20):
    try:
        history = await db.chats.find(
            {"session_id": session_id}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        # Convert ObjectId to string for JSON serialization
        for msg in history:
            msg["_id"] = str(msg["_id"])
        
        return {"history": list(reversed(history))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")

@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str):
    try:
        result = await db.chats.delete_many({"session_id": session_id})
        return {"deleted_count": result.deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")

@app.get("/api/knowledge")
async def get_knowledge():
    """Return TaeKwon-Do knowledge categories for learning section"""
    return {
        "categories": [
            {
                "id": "patterns",
                "name": "Patterns (Tuls)",
                "icon": "🥋",
                "description": "Learn the traditional forms"
            },
            {
                "id": "stances",
                "name": "Stances (Sogi)",
                "icon": "🧘",
                "description": "Master different positions"
            },
            {
                "id": "blocks",
                "name": "Blocks (Makgi)",
                "icon": "🛡️",
                "description": "Defense techniques"
            },
            {
                "id": "punches",
                "name": "Punches (Jirugi)",
                "icon": "👊",
                "description": "Strike techniques"
            },
            {
                "id": "hand_parts",
                "name": "Hand Parts",
                "icon": "✋",
                "description": "Parts used for striking"
            },
            {
                "id": "foot_parts",
                "name": "Foot Parts",
                "icon": "🦶",
                "description": "Parts used for kicking"
            },
            {
                "id": "kicks",
                "name": "Kicks (Chagi)",
                "icon": "🦵",
                "description": "Kicking techniques"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
