-- Set working directory
set scriptPath to (path to me as text)
set scriptPath to POSIX path of scriptPath -- Convert to Unix path
set scriptDir to do shell script "dirname " & quoted form of scriptPath

-- Set python path
set python to "/Users/patrick/.pyenv/shims/python"

-- Set the port number
set portNumber to "15080"

-- Start the Python server in the background (no terminal window)
do shell script "cd " & quoted form of scriptDir & ";nohup " & python & " server.py >/dev/null 2>&1 & echo $!"

-- Wait a moment to ensure the server starts
delay 1 -- seconds

-- Open the default web browser to access the site
do shell script "open http://localhost:" & portNumber
