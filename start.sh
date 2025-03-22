#!/bin/bash

# Path to python
python_path="python3"

# Path to gittool
gittool_path="."

# Set the port number
PORT=15080

# Start the Python server in the background (hide output)
nohup "$python_path" "$gittool_path/server.py" >/dev/null 2>&1 &

# Wait a moment to ensure the server starts
sleep 0.5  # seconds

# Open the default web browser
xdg-open "http://localhost:$PORT"
