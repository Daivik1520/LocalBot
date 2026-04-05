import os
import logging
import requests
import time
import tempfile
import edge_tts
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY")

# TTS Configuration - Microsoft Edge Neural Voices
# These are the most human-sounding free voices available
# Change TTS_VOICE to any voice from: edge-tts --list-voices
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AndrewMultilingualNeural")  # Deep, natural male voice
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"

SYSTEM_PROMPT = (
    "You are a smart, helpful, and capable AI assistant running locally. "
    "You provide clear, concise, and accurate answers. "
    "You can help with answering questions, writing code, and creative writing. "
    "Keep responses conversational and natural since they will be spoken aloud via TTS. "
    "Avoid excessive markdown formatting, bullet points, or code blocks unless specifically asked. "
    "Use short, clear sentences."
)

def get_ngrok_url():
    """Automatically fetch the public ngrok URL from the local ngrok API."""
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = response.json()
        return data['tunnels'][0]['public_url']
    except Exception:
        return None

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

history = {}

async def text_to_speech(text: str, output_path: str) -> bool:
    """Convert text to speech using edge-tts and save to file."""
    try:
        # Clean text for better TTS output
        clean_text = text.replace("*", "").replace("#", "").replace("`", "")
        clean_text = clean_text.replace("**", "").replace("__", "")
        
        communicate = edge_tts.Communicate(clean_text, TTS_VOICE)
        await communicate.save(output_path)
        return True
    except Exception as e:
        logging.error(f"TTS error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    welcome = "Namaste! Your local Gemma 2 bot is online with voice support. How can I help you today?"
    await update.message.reply_text(welcome)
    
    # Send welcome as voice too
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
    """Toggle TTS on/off with /voice command."""
    global TTS_ENABLED
    TTS_ENABLED = not TTS_ENABLED
    status = "🔊 Voice replies ON" if TTS_ENABLED else "🔇 Voice replies OFF"
    await update.message.reply_text(status)

async def set_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change TTS voice with /setvoice <voice_name> command."""
    global TTS_VOICE
    if context.args:
        TTS_VOICE = context.args[0]
        await update.message.reply_text(f"🎙️ Voice changed to: {TTS_VOICE}")
    else:
        voices_info = (
            "🎙️ **Popular voices:**\n\n"
            "**Male (Natural):**\n"
            "• `en-US-AndrewMultilingualNeural` (current default)\n"
            "• `en-US-GuyNeural`\n"
            "• `en-US-ChristopherNeural`\n"
            "• `en-IN-PrabhatNeural` (Indian English)\n\n"
            "**Female (Natural):**\n"
            "• `en-US-AriaNeural`\n"
            "• `en-US-JennyNeural`\n"
            "• `en-IN-NeerjaExpressiveNeural` (Indian English)\n\n"
            "Usage: `/setvoice en-US-AriaNeural`"
        )
        await update.message.reply_text(voices_info, parse_mode="Markdown")

from telegram.error import NetworkError, TimedOut

def error_handler(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except NetworkError as e:
            logging.error(f"Network error: {e}")
            await update.message.reply_text("⚠️ Network issue - retrying...")
            time.sleep(2)
            return await func(update, context)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            await update.message.reply_text("🚨 Sorry, I encountered an error. Please try again.")
    return wrapper

@error_handler
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        await update.message.reply_text("❌ Error: ngrok tunnel is not running! Please start ngrok first.")
        return

    client = AsyncOpenAI(base_url=f"{ngrok_url}/v1", api_key=LLAMA_API_KEY)

    if chat_id not in history:
        history[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    history[chat_id].append({"role": "user", "content": user_text})
    
    if len(history[chat_id]) > 11:
        history[chat_id] = [history[chat_id][0]] + history[chat_id][-10:]

    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = await client.chat.completions.create(
            model="gemma-2-2b-it",
            messages=history[chat_id],
            max_tokens=1024,
            temperature=0.7
        )
        
        bot_response = response.choices[0].message.content
        history[chat_id].append({"role": "assistant", "content": bot_response})
        
        # Send text reply
        await update.message.reply_text(bot_response)
        
        # Send voice reply if TTS is enabled
        if TTS_ENABLED:
            await context.bot.send_chat_action(chat_id=chat_id, action="record_voice")
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            
            try:
                if await text_to_speech(bot_response, tmp_path):
                    with open(tmp_path, "rb") as audio:
                        await update.message.reply_voice(voice=audio)
                else:
                    logging.warning("TTS failed, text reply was still sent.")
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("I couldn't reach the local AI server. Make sure start_server.sh is running!")

if __name__ == '__main__':
    print("Setting ngrok authtoken...")
    os.system(f"ngrok config add-authtoken {os.getenv('NGROK_AUTHTOKEN')}")
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("voice", toggle_voice))
    app.add_handler(CommandHandler("setvoice", set_voice))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))
    
    print(f"Bot is ready with TTS enabled! Voice: {TTS_VOICE}")
    print("Commands: /start, /voice (toggle TTS), /setvoice (change voice)")
    print("Please ensure ngrok and llama-server are running!")
    app.run_polling()
