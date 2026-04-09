#!/bin/bash

# Kill any existing processes to start fresh
echo "🔄 Cleaning up old processes..."
pkill -f "llama-server"
pkill -f "bot.py"
sleep 2

echo "🚀 Starting LocalBot Suite..."

# 1. Start the AI Server in the background
echo "🤖 Starting Gemma 2 Server..."
./start_server.sh > server.log 2>&1 &
SERVER_PID=$!

sleep 2

# 2. Start the Telegram Bot
echo "💬 Starting Telegram Bot..."
# Trap to ensure cleanup handles background servers when bot.py exits or receives signal
trap "kill $SERVER_PID; echo 'Terminated servers'; exit" SIGINT SIGTERM

python3 bot.py

