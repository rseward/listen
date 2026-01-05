# Logging Best Practices

This document describes the logging levels used throughout the application and when each level is appropriate.

## Log Levels

### DEBUG
Used for detailed diagnostic information useful during development and troubleshooting.

**Examples:**
- Function entry/exit with parameters
- Detailed configuration values
- Loop iterations
- API request/response details

**In the codebase:**
- Model initialization parameters
- Audio stream configuration details
- Text input sources
- API base URL configuration
- Text processing details (input/output lengths)

### INFO
Used for general informational messages that highlight the progress of the application.

**Examples:**
- Successful initialization
- Model/service selection
- Major state transitions
- Successful operations

**In the codebase:**
- Model loaded successfully
- Audio stream opened successfully
- Recording started
- Text improvement completed
- AI service selection (Gemini/Ollama)

### WARNING
Used for potentially harmful situations that don't prevent the application from functioning.

**Examples:**
- Recoverable errors
- Fallback behavior
- Degraded functionality
- API returned unexpected results

**In the codebase:**
- Audio read errors (recoverable)
- API returned None response
- No AI service available (fallback to passthrough)
- Service initialization failures (non-critical)

### ERROR
Used for error events that might still allow the application to continue running.

**Examples:**
- Failed operations
- Unrecoverable errors in a subsystem
- User-facing errors

**In the codebase:**
- Model initialization failed
- Recording error
- Transcription error
- Text improvement failed
- No text provided (user error)

### CRITICAL
Used for severe error events that will likely cause the application to abort.

**Examples:**
- Application cannot start
- Fatal system errors
- Complete service failure

**Not currently used in the codebase** (errors are recoverable or handled gracefully)

## Configuration

Set the log level via environment variable:

```bash
# In .env file
LOG_LEVEL=INFO

# Or as environment variable
export LOG_LEVEL=DEBUG
```

Default level: **INFO**

## Best Practices

1. **Use DEBUG for development details** - Information that's only useful when debugging
2. **Use INFO for normal operations** - Key events in the application lifecycle
3. **Use WARNING for recoverable issues** - Problems that don't stop execution
4. **Use ERROR for failures** - Operations that failed but app can continue
5. **Use CRITICAL sparingly** - Only for fatal errors

## Examples from the Codebase

### Good DEBUG Usage
```python
logger.debug(f"Initializing Whisper model: size={model_size}, device={device}")
logger.debug(f"Opening audio stream: format={self.FORMAT}, channels={self.CHANNELS}")
```

### Good INFO Usage
```python
logger.info("Whisper model loaded successfully")
logger.info(f"Using Gemini model: {self.model}")
logger.info("Text improvement completed successfully")
```

### Good WARNING Usage
```python
logger.warning(f"Audio read error: {e}")  # Recoverable
logger.warning("No AI service available - will pass through text unchanged")
```

### Good ERROR Usage
```python
logger.error(f"Model initialization failed: {e}", exc_info=True)
logger.error(f"Recording error: {e}", exc_info=True)
```

## Viewing Logs

```bash
# View all logs at INFO level and above
tail -f logs/listen_app.log

# View only errors
grep ERROR logs/*.log

# View with DEBUG level
LOG_LEVEL=DEBUG listen
```

## Log Files

Each component has its own log file:
- `logs/listen_app.log` - GUI application
- `logs/improve.log` - Text improvement CLI
- `logs/text_improver.log` - AI backend

See [logs/README.md](logs/README.md) for more details.
