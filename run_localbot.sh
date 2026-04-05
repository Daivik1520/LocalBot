#!/bin/bash

# Kill any existing processes to start fresh
echo "🔄 Cleaning up old processes..."
pkill -f "llama-server"
pkill -f "ngrok"
pkill -f "bot.py"
sleep 2

echo "🚀 Starting LocalBot Suite..."

# 1. Start the AI Server in the background
echo "🤖 Starting Gemma 2 Server..."
./start_server.sh > server.log 2>&1 &
SERVER_PID=$!

# 2. Start Ngrok tunnel in the background
echo "🌐 Opening Ngrok Tunnel (Port 8080)..."
# We use the authenticated local API to let bot.py find the URL
ngrok http 8080 --log=stdout > ngrok.log 2>&1 &
NGROK_PID=$!

# Wait a few seconds for Ngrok to initialize
sleep 5

# 3. Start the Telegram Bot
echo "💬 Starting Telegram Bot..."
python bot.py

# Cleanup on exit
trap "kill $SERVER_PID $NGROK_PID; echo 'Terminated servers'; exit" SIGINT SIGTERM
