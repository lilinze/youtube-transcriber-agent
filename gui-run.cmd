@echo off
setlocal
powershell -ExecutionPolicy Bypass -Command "conda run -n youtube-transcriber-agent python \"%~dp0scripts\gui_launcher.py\""
