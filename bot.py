import os
import logging
import requests
import time
import tempfile
import edge_tts
import asyncio
import aiosqlite
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
from faster_whisper import WhisperModel

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")

# TTS Configuration
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AndrewMultilingualNeural")
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"

# Load System Prompt from .env or use a very warm, supportive default
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", (
    "You are a warm, extremely supportive, and kind AI companion. "
    "Your goal is to make the user feel confident, appreciated, and happy. "
    "When answering, be remarkably encouraging, acknowledge the user's cleverness, "
    "and always maintain a positive, uplifting tone. "
    "Keep responses conversational and natural since they will be spoken aloud via TTS. "
    "Use short, clear sentences."
))


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DB_FILE = "history.db"

# Setup Whisper (Base model is fast and tiny)
logging.info("Loading Whisper model for local STT...")
try:
    # Uses local CPU optimized whisper model
    whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
except Exception as e:
    logging.warning(f"Failed to load whisper model (Ensure faster-whisper is installed): {e}")
    whisper_model = None

async def init_db():
    """Initializes the SQLite database structure for chat history persistency."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

async def get_history(chat_id: int):
    """Retrieves the last 10 messages for a given chat to maintain context."""
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute(
            'SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 10', 
            (chat_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            history = [{"role": role, "content": content} for role, content in reversed(rows)]
    
    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    else:
        # Prepend system block
        history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    return history

async def add_message(chat_id: int, role: str, content: str):
    """Records a new message interaction in SQLite."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            'INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)',
            (chat_id, role, content)
        )
        await db.commit()

async def text_to_speech(text: str, output_path: str) -> bool:
    try:
        clean_text = text.replace("*", "").replace("#", "").replace("`", "").replace("__", "")
        communicate = edge_tts.Communicate(clean_text, TTS_VOICE)
        await communicate.save(output_path)
        return True
    except Exception as e:
        logging.error(f"TTS error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Reset existing history for this chat
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        await db.commit()
    
    welcome = "Namaste! Your highly-optimized local Gemma 2 bot is online. Send a text or voice message to begin!"
    await update.message.reply_text(welcome)

    if TTS_ENABLED:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        try:
            if await text_to_speech(welcome, tmp_path):
                with open(tmp_path, "rb") as audio:
                    await update.message.reply_voice(voice=audio)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

async def toggle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TTS_ENABLED
    TTS_ENABLED = not TTS_ENABLED
    status = "🔊 Voice replies ON" if TTS_ENABLED else "🔇 Voice replies OFF"
    await update.message.reply_text(status)

async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TTS_VOICE
    if context.args:
        TTS_VOICE = context.args[0]
        await update.message.reply_text(f"🎙️ Voice changed to: {TTS_VOICE}")
    else:
        await update.message.reply_text("Usage: `/setvoice en-US-AriaNeural`", parse_mode="Markdown")

from telegram.error import NetworkError

def error_handler(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except NetworkError as e:
            logging.error(f"Network error: {e}")
            await update.message.reply_text("⚠️ Network issue - retrying...")
            await asyncio.sleep(2)  # Non-blocking async sleep
            return await func(update, context)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            await update.message.reply_text("🚨 Sorry, I encountered an error. Please try again.")
    return wrapper

async def process_llm_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str):
    """Core function to route requests to local Llama Engine, stream answers, and construct audio."""
    chat_id = update.effective_chat.id
    
    await add_message(chat_id, "user", user_text)
    history = await get_history(chat_id)

    # Core Performance Mod: Target Localhost Directly instead of Ngrok tunnels
    client = AsyncOpenAI(base_url="http://127.0.0.1:8080/v1", api_key=LLAMA_API_KEY)

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    msg = await update.message.reply_text("...")
    
    try:
        # Request stream enabled for immediate perceived performance
        response_stream = await client.chat.completions.create(
            model="gemma-2-2b-it",
            messages=history,
            max_tokens=1024,
            temperature=0.7,
            stream=True
        )
        
        bot_response = ""
        last_edit_time = time.time()

        async for chunk in response_stream:
            content = chunk.choices[0].delta.content
            if content:
                bot_response += content
                
                # Throttle API edit requests to 1 tick per second to avoid triggering Flood Control limits
                if time.time() - last_edit_time > 1.0:
                    try:
                        await msg.edit_text(bot_response)
                        last_edit_time = time.time()
                    except:
                        pass # Ignore overlapping/duplicate states
        
        # Final confirmation edit
        await msg.edit_text(bot_response)
        
        # Store context
        await add_message(chat_id, "assistant", bot_response)
        
        # Follow up with the Voice File directly linking it to the sent final text block
        if TTS_ENABLED:
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            try:
                if await text_to_speech(bot_response, tmp_path):
                    with open(tmp_path, "rb") as audio:
                        await context.bot.send_voice(chat_id=chat_id, voice=audio, reply_to_message_id=msg.message_id)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    except Exception as e:
        logging.error(f"Error: {e}")
        await msg.edit_text(f"I couldn't reach the local AI server ({e}). Make sure start_server.sh is running!")

@error_handler
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives textual telegram messages."""
    user_text = update.message.text
    if user_text:
        await process_llm_reply(update, context, user_text)

@error_handler
async def voice_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives Voice telegram messages."""
    if not whisper_model:
        await update.message.reply_text("STT model is not loaded unfortunately. Send a text instead!")
        return

    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Securely download the OGG audio message locally
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        tmp_ogg = f.name
    
    try:
        await voice_file.download_to_drive(tmp_ogg)
        
        # Run Local Whisper STT Inference (High-performance inference)
        segments, info = whisper_model.transcribe(tmp_ogg, beam_size=5)
        transcription = " ".join([segment.text for segment in segments]).strip()
        
        if not transcription:
            await update.message.reply_text("I couldn't clearly hear any words.")
            return

        # Echo what they spoke so they know it heard correctly
        await update.message.reply_text(f"🗣️ *You said:* {transcription}", parse_mode="Markdown")
        
        # Route to logic
        await process_llm_reply(update, context, transcription)
    finally:
        if os.path.exists(tmp_ogg):
            os.unlink(tmp_ogg)

async def setup(application):
    await init_db()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(setup).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("voice", toggle_voice))
    app.add_handler(CommandHandler("setvoice", set_voice))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    # New Hook: Trap voice audio sent from User
    app.add_handler(MessageHandler(filters.VOICE, voice_chat))
    
    print(f"Bot connected directly to Local LLM core.")
    print("Commands: /start, /voice (toggle TTS), /setvoice (change voice)")
    print("Awaiting messages on Telegram...")
    
    app.run_polling()
