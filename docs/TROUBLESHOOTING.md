# Troubleshooting Guide

This guide helps diagnose and fix common issues with the Listen application.

## GUI Closes Before Recording

### Symptom
The GUI window opens briefly but closes before you can click the Record button.

### Cause
This indicates a critical failure during the application initialization phase, typically:
- Whisper model failed to load
- PyAudio cannot initialize (no audio devices, permission issues)
- Missing dependencies
- System incompatibility

### How to Diagnose

1. **Check the error logs:**
   ```bash
   # View the most recent errors
   tail -50 logs/listen_app.log | grep ERROR
   
   # Or view the entire log
   cat logs/listen_app.log
   ```

2. **Look for specific error patterns:**

   **Model initialization failure:**
   ```
   ERROR - Model initialization failed: ...
   ERROR - Custom model initialization failed: ...
   ```
   Solution: Check that faster-whisper is installed correctly, sufficient disk space for model download

   **PyAudio initialization failure:**
   ```
   ERROR - PyAudio initialization failed: ...
   ERROR - Initializing PyAudio interface
   ```
   Solution: Check audio permissions, audio devices are connected/working

   **GUI initialization failure:**
   ```
   ERROR - Failed to initialize GUI: ...
   ERROR - Failed to create GUI application: ...
   ```
   Solution: Check display environment, tkinter installation

   **Premature closure detection:**
   ```
   ERROR - GUI closed before initialization completed - user was unable to click Record button
   ERROR - This indicates a critical startup failure
   ```
   This error confirms the window closed during initialization.

### Common Solutions

#### 1. Audio Device Issues
```bash
# Check available audio devices (Linux)
arecord -l

# Test audio recording
arecord -d 3 test.wav

# Check permissions
groups | grep audio
```

If not in audio group:
```bash
sudo usermod -a -G audio $USER
# Log out and back in
```

#### 2. Missing Dependencies
```bash
# Reinstall dependencies
uv sync

# Or
uv pip install -e .
```

#### 3. PyAudio Installation Issues (Linux)
```bash
# Install system dependencies
sudo dnf install portaudio-devel  # Fedora
sudo apt install portaudio19-dev  # Ubuntu/Debian

# Reinstall PyAudio
pip uninstall pyaudio
pip install pyaudio
```

#### 4. Model Download Issues
```bash
# Check internet connection
ping google.com

# Check disk space
df -h

# Try smaller model
listen --model-size tiny
```

#### 5. Display Issues (if running remotely)
```bash
# Set DISPLAY environment variable
export DISPLAY=:0

# Or use X11 forwarding
ssh -X user@host
```

## Debugging with Enhanced Logging

### Enable DEBUG logging
```bash
# In .env file
LOG_LEVEL=DEBUG

# Or as environment variable
export LOG_LEVEL=DEBUG
listen
```

### Watch logs in real-time
```bash
# In one terminal, start logging
tail -f logs/listen_app.log

# In another terminal, run the app
listen
```

### Log Files by Component
- `logs/listen_app.log` - GUI and recording errors
- `logs/improve.log` - Text improvement errors
- `logs/text_improver.log` - AI backend errors

## Error Log Indicators

### Critical Errors (Application Cannot Start)
```
ERROR - Failed to create GUI application: ...
ERROR - Application cannot start - GUI initialization failed
ERROR - GUI closed before initialization completed
```

### Recoverable Errors (Application Can Continue)
```
WARNING - Audio read error: ...
WARNING - API returned None response
ERROR - Transcription error: ...
```

### Expected Behavior
If initialization succeeds, you should see:
```
INFO - Whisper model loaded successfully
INFO - PyAudio interface initialized successfully
INFO - Application ready - user can now record
```

## Getting Help

When reporting issues, include:

1. **Error logs:**
   ```bash
   # Last 50 lines showing the error
   tail -50 logs/listen_app.log
   ```

2. **System information:**
   ```bash
   uname -a
   python3 --version
   ```

3. **Audio device information:**
   ```bash
   arecord -l  # Linux
   # or
   system_profiler SPAudioDataType  # macOS
   ```

4. **Steps to reproduce the issue**

## Testing Error Logging

Run the test script to verify error logging is working:
```bash
python3 test_error_logging.py
```

This simulates various failure scenarios and confirms they are logged correctly.
