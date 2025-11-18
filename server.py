from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv
import google.generativeai as genai
from passlib.context import CryptContext
from jose import jwt, JWTError
import uuid

load_dotenv()

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # poți restrânge mai târziu la domeniul tău
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MongoDB ----------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.taekwondo_chatbot  # colecții: users, chats

# ---------------- Gemini ----------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY is not set in environment (.env)")
genai.configure(api_key=GOOGLE_API_KEY)

# ---------------- Auth / JWT setup ----------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_scheme = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 zile


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
):
    """
    Folosit pentru endpoint-uri care cer user logat.
    Header: Authorization: Bearer <token>
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await db.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# ---------------- Prompt / Knowledge ----------------

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
14. CIRCULAR BLOCK (Dollmyo Makgi) - Circular motion
15. HOOKING BLOCK (Golcho Makgi) - Hooking motion
16. W-SHAPE BLOCK (San Makgi) - Mountain shape block

# PUNCHES (JIRUGI)
1. FOREFIST PUNCH (Ap Joomuk Jirugi) - Basic straight punch
2. REVERSE PUNCH (Baro Jirugi) - Opposite hand to forward leg
3. UPSET PUNCH (Dwijibo Jirugi) - Upward punch
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
5. HOOK KICK (Goro Chagi) - Hooking motion kick
6. CRESCENT KICK (Naeryo Chagi) - Arc motion kick

# COACHES:
1-3 DAN -> SABOOM
4-6 DAN -> SABONIM
7-8 DAN -> SAHEON
9 DAN -> SASEONG

If you don't know something, or if the child corrects you, you must:
1) Admit honestly that you are not fully sure.
2) Check your knowledge against the TaeKwon-Do information provided in this prompt.
3) Give the safest and most accurate answer you can.
4) Encourage the child to ask their real instructor for confirmation.

Remember: Always encourage practice, safety, and respect (courtesy, integrity, perseverance, self-control, indomitable spirit - the TaeKwon-Do tenets)!
"""

LANGUAGE_GUIDE = """
LANGUAGE RULES (VERY IMPORTANT):
- Detect automatically the language of the child's message (Romanian or English).
- If the child writes in Romanian, you MUST answer fully in Romanian.
- If the child writes in English, you MUST answer fully in English.
- If the child mixes Romanian and English, answer mainly in the language used most in the last message.
- Never say that you detected the language. Just answer naturally.
- Keep explanations very simple, friendly and adapted for children.
"""

HAWY_PERSONALITY = """
You are Hawy the Hedgehog 🦔 — a fun, energetic and friendly TaeKwon-Do buddy.

TONE & VIBE:
- Talk like a cool older friend, not like a teacher or adult.
- Be playful, relaxed, natural.
- Use short messages (1–3 short paragraphs max).
- Use max 1–2 emojis, never spam.
- Never sound formal (“Ce te interesează cel mai mult?”, “Te rog oferă detalii”).
- Avoid teacher-like sentences such as “Hai să discutăm despre...”, “Explicația este...”.

HOW TO TALK:
- If the child writes in Romanian → answer in Romanian, but casual and friendly.
- If the child writes in English → answer in English, also casual.
- Match THEIR tone:
  - If they joke → you joke back.
  - If they are confused → you simplify.
  - If they are sad → be warm but not cheesy.
- You can add fun hedgehog personality things (e.g. “I’m small but fast!”, “Hedgehogs love rolling!”).

CONVERSATION STYLE:
- Keep answers short and snappy.
- Avoid long lists unless the kid asks.
- Avoid giving too much information at once.
- Don’t give motivational speeches.
- Don't praise too much (no “great question!” every time).
- Don’t ask too many questions in a row.

CONTEXT USE:
- Remember previous parts of the conversation.
- If they say “de ce?” or “why?”, answer naturally, not like a teacher.
- If they refer to “that kick” or “ce imi ziceai mai devreme”, use context.

SAFETY:
- No dangerous exercises.
- Keep training advice simple and light.

If the topic drifts far from TaeKwon-Do, you answer briefly but bring it back smoothly.
"""


# ---------------- Pydantic models ----------------

# Auth
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# Chat
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None  # dacă nu vine, generăm noi
    user_id: Optional[str] = None     # opțional, setat din frontend după login


class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime


# ---------------- Health ----------------
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Hawy TaeKwon-Do Chatbot"}


# ---------------- Auth endpoints ----------------
@app.post("/api/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    hashed_pw = get_password_hash(user_data.password)

    user_doc = {
        "_id": user_id,
        "email": user_data.email,
        "name": user_data.name or "",
        "password_hash": hashed_pw,
        "created_at": datetime.utcnow(),
    }
    await db.users.insert_one(user_doc)

    token = create_access_token({"sub": user_id})

    user_public = UserPublic(id=user_id, email=user_data.email, name=user_data.name)
    return TokenResponse(access_token=token, user=user_public)


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = user["_id"]
    token = create_access_token({"sub": user_id})

    user_public = UserPublic(
        id=user_id,
        email=user["email"],
        name=user.get("name") or "",
    )
    return TokenResponse(access_token=token, user=user_public)


# ---------------- Chat endpoints ----------------
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_hawy(chat_message: ChatMessage):
    try:
        # 1) session_id – dacă nu e trimis, generăm unul nou
        session_id = chat_message.session_id or f"session_{uuid.uuid4().hex}"

        # 2) luăm istoric pentru context (ultimele 25 mesaje)
        query = {"session_id": session_id}
        if chat_message.user_id:
            query["user_id"] = chat_message.user_id

        history = (
            await db.chats.find(query)
            .sort("timestamp", -1)
            .limit(25)
            .to_list(25)
        )

        conversation_history = ""
        if history:
            for msg in reversed(history):
                conversation_history += f"Child: {msg['user_message']}\n"
                conversation_history += f"Hawy: {msg['bot_response']}\n\n"

        # 3) prompt complet
        full_prompt = (
            f"{TAEKWONDO_KNOWLEDGE}\n\n"
            f"{LANGUAGE_GUIDE}\n\n"
            f"{HAWY_PERSONALITY}\n\n"
        )

        if conversation_history:
            full_prompt += (
                "Previous conversation between the child and Hawy:\n"
                f"{conversation_history}\n"
            )

        full_prompt += (
            "Now continue the conversation.\n\n"
            f"Child's new message: {chat_message.message}\n\n"
            "Hawy's next answer (follow ALL rules above):"
        )

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(full_prompt)
        bot_response = response.text

        # 4) salvăm în Mongo
        chat_record = {
            "session_id": session_id,
            "user_id": chat_message.user_id,
            "user_message": chat_message.message,
            "bot_response": bot_response,
            "timestamp": datetime.utcnow(),
        }
        await db.chats.insert_one(chat_record)

        return ChatResponse(
            response=bot_response,
            session_id=session_id,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        print(f"Error in /api/chat: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")


@app.get("/api/chat/history/{session_id}")
async def get_chat_history(session_id: str, user_id: Optional[str] = None, limit: int = 20):
    try:
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id

        history = (
            await db.chats.find(query)
            .sort("timestamp", -1)
            .limit(limit)
            .to_list(limit)
        )

        for msg in history:
            msg["_id"] = str(msg["_id"])

        return {"history": list(reversed(history))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@app.delete("/api/chat/history/{session_id}")
async def clear_chat_history(session_id: str, user_id: Optional[str] = None):
    try:
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id

        result = await db.chats.delete_many(query)
        return {"deleted_count": result.deleted_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")


# ---------------- Knowledge endpoint ----------------
@app.get("/api/knowledge")
async def get_knowledge():
    return {
        "categories": [
            {
                "id": "patterns",
                "name": "Patterns (Tulls)",
                "icon": "🥋",
                "description": "Learn the traditional forms",
            },
            {
                "id": "stances",
                "name": "Stances (Sogi)",
                "icon": "🧘",
                "description": "Master different positions",
            },
            {
                "id": "blocks",
                "name": "Blocks (Makgi)",
                "icon": "🛡️",
                "description": "Defense techniques",
            },
            {
                "id": "punches",
                "name": "Punches (Jirugi)",
                "icon": "👊",
                "description": "Strike techniques",
            },
            {
                "id": "hand_parts",
                "name": "Hand Parts",
                "icon": "✋",
                "description": "Parts used for striking",
            },
            {
                "id": "foot_parts",
                "name": "Foot Parts",
                "icon": "🦶",
                "description": "Parts used for kicking",
            },
            {
                "id": "kicks",
                "name": "Kicks (Chagi)",
                "icon": "🦵",
                "description": "Kicking techniques",
            },
        ]
    }


# ---------------- Main (local dev) ----------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
