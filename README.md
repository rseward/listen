# Listen - Audio Transcription with AI-Powered Text Improvement

A desktop application for recording audio and transcribing it using faster-whisper, with optional AI-powered text improvement using Gemini or Ollama.

## Features

- **Simple GUI**: Clean interface with a record button and real-time transcription display
- **Automatic Transcription**: Uses faster-whisper for high-quality speech-to-text
- **AI Text Improvement**: Optional post-processing with Gemini or Ollama to fix grammar and punctuation
- **Smart Auto-Close**: Window closes after 15 seconds of silence or when Stop is pressed
- **Stdout Output**: Final transcription printed to standard output for easy piping

## Example Usage:

```bash
# Record audio and transcribe with AI improvement
# Run this command pipeline after sourcing the python virtual environment

listen | improve

# Just transcribe (no AI improvement)
listen
```

## Installation

### Option 1: Using uv sync (Recommended)

This uses the `uv.lock` file to create a reproducible environment with exact dependency versions:

```bash
# Create virtual environment and install dependencies from lock file
uv sync

# This creates .venv and installs the package in editable mode
```

### Option 2: Using make

```bash
# Install using make
make install

# Or install directly with uv pip
uv pip install -e .
```

Both methods will install four commands:
- `listen` - The GUI transcription application
- `improve` - Text improvement CLI tool
- `list-models` - List available AI models from configured providers
- `list-audio-devices` - List available audio devices with their properties

## Usage

### Listen (Transcription)

Start the GUI application:

```bash
# Using make
make run

# Or directly
uv run listen
```

The application will:
1. Open a GUI window
2. Click "Record" to start recording
3. Speak into your microphone
4. See real-time transcription
5. Click "Stop" or wait 15 seconds of silence
6. Final transcription is printed to stdout

### Improve (Text Enhancement)

Improve transcribed text using AI:

```bash
# From stdin
echo "this needs improvement" | uv run improve

# From command line argument
uv run improve "um this is like a test you know"

# Pipe from listen
uv run listen | uv run improve
```

### List Models (Discovery)

List available AI models from configured providers:

```bash
# List all available models
uv run list-models

# List only Gemini models
uv run list-models --provider gemini

# List only Ollama models
uv run list-models --provider ollama

# Show only any-llm-sdk format strings
uv run list-models --any-llm-only

# JSON output
uv run list-models --format json
```

### List Audio Devices (Discovery)

List available audio devices to find the correct device index for configuration:

```bash
# List all input/output devices in table format
list-audio-devices

# Show detailed information
list-audio-devices --format detailed

# Show only input devices (for recording)
list-audio-devices --input-only

# Show only output devices (for playback)
list-audio-devices --output-only

# Show all devices including those with no input/output
list-audio-devices --all
```

The table format displays:
- **IDX**: Device index (use this for `AUDIO_DEVICE_INDEX` in `.env`)
- **NAME**: Device name
- **RATE**: Default sample rate in Hz
- **IN**: Maximum input channels (0 = no input)
- **OUT**: Maximum output channels (0 = no output)
- **HOST API**: Audio host API (ALSA, JACK, etc.)
- **DEFAULT**: System default device markers (IN/OUT)

### Configuration

Copy `.env.example` to `.env` and configure as needed:

```bash
cp .env.example .env
```

#### Logging

Set the log level in your `.env` file:

```bash
# Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

Logs are written to separate files in the `logs/` directory:
- `logs/listen_app.log` - GUI application logs
- `logs/improve.log` - Text improvement CLI logs
- `logs/text_improver.log` - AI backend logs

See [logs/README.md](logs/README.md) for detailed logging documentation.

#### Audio Configuration

Configure audio device and sample rate in your `.env` file:

```bash
# Audio device index (optional, defaults to system default)
# List available devices with: list-audio-devices
AUDIO_DEVICE_INDEX=4

# Sample rate in Hz (optional, defaults to auto-detection)
# Common values: 16000, 44100, 48000
# Note: 16000 Hz is optimal for Whisper transcription
AUDIO_SAMPLE_RATE=44100
```

**To find your device index:**
```bash
list-audio-devices
```

**Auto-detection behavior:**
- If not configured, the app automatically detects your default audio device
- Sample rates are tested in order: 16000, device default, 44100, 48000, 22050, 8000 Hz
- The first working rate is selected

**Manual configuration:**
- Use `AUDIO_DEVICE_INDEX` to force a specific microphone/input device
- Use `AUDIO_SAMPLE_RATE` to force a specific sample rate
- Invalid values fall back to auto-detection with a warning

#### Gemini API (Recommended)

```bash
export GEMINI_API_KEY="your-api-key-here"
# Or add to .env file:
# GEMINI_API_KEY=your-api-key-here
```

Get an API key from: https://makersuite.google.com/app/apikey

#### Ollama (Local Alternative)

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull gemma3:latest

# Start Ollama (runs automatically as a service)
ollama serve

# Optional: Set custom URL
export OPENAI_BASE_URL="http://localhost:11434/api"
# Or add to .env file:
# OPENAI_BASE_URL=http://localhost:11434/api
```

The `improve` command will automatically use:
1. Gemini (if GEMINI_API_KEY is set)
2. Ollama (if running locally)
3. Pass-through (if no AI service is available)

## Development

### Running Tests

```bash
# Unit tests only (fast, no external dependencies)
make test
# or
make test-unit

# Integration tests (requires Gemini API or Ollama)
make test-integration

# All tests
make test-all
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### Project Structure

```
listen/
├── src/listen_tools/          # Main package
│   ├── __init__.py
│   ├── listen_app.py         # GUI application
│   ├── improve.py            # Text improvement CLI
│   └── text_improver.py      # AI text improvement logic
├── tests/                    # Test suite
│   ├── test_text_improver.py              # Unit tests
│   ├── test_text_improver_integration.py  # Integration tests
│   └── README.md                          # Testing documentation
├── pyproject.toml           # Package configuration
├── Makefile                 # Build commands
└── README.md               # This file
```

## Requirements

- Python >= 3.11
- PyAudio (for audio recording)
- customtkinter (for GUI)
- faster-whisper (for transcription)
- google-generativeai (optional, for Gemini)
- any-llm-sdk (for AI model integration)

## Troubleshooting

If the GUI closes before you can click Record, or you encounter other issues, see the [Troubleshooting Guide](TROUBLESHOOTING.md) for detailed diagnostic steps.

Quick checks:
```bash
# View error logs
tail -50 logs/listen_app.log | grep ERROR

# Enable debug logging
export LOG_LEVEL=DEBUG
listen

# Enable debug mode (saves audio chunks to WAV files)
listen --debug
```

### Debug Mode

If transcription isn't working, enable debug mode to save recorded audio chunks to WAV files:

```bash
listen --debug
```

Audio files will be saved to `debug_audio/audio_TIMESTAMP.wav`. The file path is printed to stderr after each chunk is saved. You can inspect these files to verify:
- Audio is being captured correctly
- Microphone input is working
- Audio quality is sufficient for transcription

### Audio Device Issues

The application automatically detects your audio device and selects an optimal sample rate. If you experience issues:

1. Check available audio devices:
```bash
python3 -c "import pyaudio; pa = pyaudio.PyAudio(); [print(f'{i}: {pa.get_device_info_by_index(i)[\"name\"]}') for i in range(pa.get_device_count())]; pa.terminate()"
```

2. Test your microphone:
```bash
# Record a test with debug mode
listen --debug
# Check the saved WAV files in debug_audio/
```

**Note for Fedora/PipeWire users**: If you're using Homebrew Python on Fedora with PipeWire, the system will automatically select a compatible audio device and sample rate.

## Technical Details

- **Cross-platform**: Works on Linux, macOS, and Windows
- **Minimal resources**: Efficient CPU-based transcription
- **Fast startup**: Background model loading
- **Real-time display**: Live transcription updates
- **Clean output**: Transcription to stdout for easy integration
- **Comprehensive logging**: Separate log files for each component with configurable levels

