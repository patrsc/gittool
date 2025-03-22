#!/bin/bash

# Set the port number
PORT=15080

# Start the Python server in the background (hide output)
nohup python3 server.py >/dev/null 2>&1 &

# Wait a moment to ensure the server starts
sleep 0.5  # seconds

# Open the default web browser
xdg-open "http://localhost:$PORT"
