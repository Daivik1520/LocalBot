# 🤖 LocalBot: Private AI Assistant

[![Local AI](https://img.shields.io/badge/Privacy-Local%20AI-blueviolet?style=for-the-badge&logo=privacy-ideas)](https://github.com/daivikreddy/LocalBot)
[![Gemma 2](https://img.shields.io/badge/Model-Gemma%202%202B-white?style=for-the-badge&logo=google-cloud&logoColor=blue)](https://huggingface.co/google/gemma-2-2b-it)
[![LLaMA.cpp](https://img.shields.io/badge/Engine-LLaMA.cpp-green?style=for-the-badge)](https://github.com/ggerganov/llama.cpp)
[![Edge-TTS](https://img.shields.io/badge/Voice-Edge--TTS-blue?style=for-the-badge)](https://github.com/rany2/edge-tts)

**LocalBot** is a high-performance, privacy-first AI chatbot designed to run entirely on your local hardware. Optimized for small but powerful models like **Gemma 2 2B**, it brings a professional-grade assistant to your Telegram with ultra-natural voice synthesis—no expensive cloud infrastructure or data sacrifices required.

---

## ⚡ Why LocalBot?

- **Zero Data Leakage**: Your conversations stay on your machine. Perfect for private workspaces and sensitive brainstorming.
- **Gemma 2 Optimization**: Specifically tuned for Google's Gemma 2 2B model, providing high-quality intelligence with minimal RAM footprints.
- **Human-Like Voice**: Integrated with `edge-tts` to provide smooth, natural-sounding audio replies.
- **Hardware Agnostic**: Runs beautifully on standard CPUs (macOS/Linux) thanks to `llama.cpp` optimizations.

---

## 📊 Performance & System Stats

| Metric | Spec / Value | Label |
| :--- | :--- | :--- |
| **Primary Model** | Gemma 2 2B Instruct (Q4_K_M) | `High-Quality Small Model` |
| **Model Size** | ~1.6 GB | `Low Storage Footprint` |
| **Memory usage** | ~2.2 GB RAM (Total) | `Laptop Ready` |
| **Inference Engine** | llama.cpp (CPU Optimized) | `Universal Compatibility` |
| **TTS latency** | < 0.5s response time | `Real-time Conversation` |
| **Privacy Tier** | 100% Local Processing | `Highest Security` |

---

## 🚀 Key Features

*   **💬 Persistent Chat History**: Remembers your conversation context for natural flow.
*   **🎙️ Multilingual Voice Support**: Choose from various human-sounding neural voices (Male/Female).
*   **🌐 Secure Remote Access**: Uses `ngrok` to securely expose your local bot to the Telegram API.
*   **🌍 Global Access**: Message your bot from **anywhere in the world** via Telegram while data processing stays local.
*   **🔨 Developer Friendly**: Start everything with a single script (`run_localbot.sh`).
*   **🧠 Intelligent Prompting**: Optimized instructions for clear, conversational responses.

---

## 📱 Global Connectivity

By leveraging the Telegram Bot API and a secure ngrok tunnel, you can interact with your private AI from your phone, tablet, or laptop while traveling.

**Find your bot on Telegram:**
[t.me/YourBotUsername](https://t.me/YourBotUsername) *(Replace with your specific bot handle)*

---

## 🛠️ Installation

### 1. Prerequisite
Ensure you have `python 3.10+` and `llama.cpp` installed in the project root.

### 2. Setup Environment
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Configure `.env`
Create a `.env` file with your credentials:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
NGROK_AUTHTOKEN=your_ngrok_authtoken
LLAMA_API_KEY=any_secure_key
TTS_VOICE=en-US-AndrewMultilingualNeural
```

### 4. Download Model
Place the `gemma-2-2b-it-Q4_K_M.gguf` model in the `/models` directory.

---

## 🏃 Running the Bot

Simply execute the main runner script:
```bash
./run_localbot.sh
```
This script handles starting the AI server, opening the ngrok tunnel, and launching the Telegram bot interface.

---

## 🗨️ Commands

- `/start`: Initialize the bot and receive a welcome message.
- `/voice`: Toggle between text-only and voice-plus-text replies.
- `/setvoice <voice_name>`: Switch the AI's personality with a different neural voice.

---

## 🛡️ Privacy Statement
LocalBot is built on the philosophy that **intelligence should not come at the cost of privacy.** By using local models like Gemma 2, we eliminate the need for third-party inference APIs (like OpenAI or Groq), ensuring your data is never used for training or stored on remote servers.

---
*Created by [Daivik Reddy](https://github.com/daivikreddy) for the local AI community.*
