Set WshShell = CreateObject("WScript.Shell")

' Path to python
python_path = "python"

' Path to gittool
gittool_path = "."

' Set the port number
port = "15080"

' Start the Python server script in a hidden window
WshShell.Run "cmd /c start /b " & python_path & " """ & gittool_path & "\server.py""", 0, False

' Wait for a moment to ensure the server starts
WScript.Sleep 500 ' milliseconds

' Open the default web browser to access the site
WshShell.Run "http://localhost:" & port, 1, False
