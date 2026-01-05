# Double Initialization Bug Fix

## Problem

After adding comprehensive error logging, the GUI application failed to render properly. The Record button would not become clickable, causing the application to be unusable.

### Root Cause

The logging modifications exposed a critical bug: **two separate initialization threads** were running simultaneously:

1. **Thread 1**: Started in `ListenApp.__init__()` line 72-73
   ```python
   init_thread = threading.Thread(target=self._initialize_model_wrapper, daemon=True)
   init_thread.start()
   ```

2. **Thread 2**: Started in `main()` line 444
   ```python
   threading.Thread(target=custom_init_wrapper, daemon=True).start()
   ```

### Symptoms

Looking at the logs:
```
2026-01-05 09:29:00 - INFO - Custom Whisper model loaded successfully
2026-01-05 09:29:00 - INFO - Whisper model loaded successfully
```

Both threads loaded the model, competed for resources, and neither properly completed the initialization sequence. The Record button never became enabled because `model_loaded()` was called by both threads in an unpredictable order.

## Solution

Unified the initialization to use a **single initialization path**:

### Changes Made

1. **Modified `ListenApp.__init__()` to accept parameters**:
   ```python
   def __init__(self, model_size="base", cuda=False):
       # Store configuration
       self.model_size = model_size
       self.cuda = cuda
       # ... rest of init ...
       # Do NOT start initialization thread here
   ```

2. **Updated `initialize_model()` to use stored configuration**:
   ```python
   def initialize_model(self):
       device = "cuda" if self.cuda else "cpu"
       compute_type = "float16" if self.cuda else "int8"
       
       logger.debug(f"Initializing Whisper model: size={self.model_size}, ...")
       self.model = WhisperModel(self.model_size, device=device, ...)
   ```

3. **Simplified `main()` to use single initialization**:
   ```python
   # Create app with configuration
   app = ListenApp(model_size=model_size, cuda=cuda)
   
   # Start single initialization thread
   init_thread = threading.Thread(target=app._initialize_model_wrapper, daemon=True)
   init_thread.start()
   ```

4. **Removed duplicate custom_init code**: Eliminated the redundant `custom_init()` and `custom_init_wrapper()` functions entirely.

## Verification

### Expected Log Sequence (Fixed)

```
DEBUG - Initializing ListenApp GUI
DEBUG - GUI widgets created successfully
DEBUG - Initializing Whisper model: size=base, device=cpu, compute_type=int8
DEBUG - Starting GUI main loop
INFO  - Whisper model loaded successfully
DEBUG - Initializing PyAudio interface
INFO  - PyAudio interface initialized successfully
INFO  - Application ready - user can now record
```

### Test Script

Run `test_initialization.py` to verify:

```bash
python3 test_initialization.py
```

Expected output:
```
✓ PASS: Single initialization path working correctly!

Expected log sequence found:
  1. GUI initialization
  2. Model loaded (once)
  3. PyAudio initialized (once)
  4. Application ready
```

## Benefits

1. **Deterministic initialization**: Single code path, predictable behavior
2. **Proper completion**: Record button enables reliably
3. **Cleaner logs**: No duplicate/confusing messages
4. **Better error handling**: Errors from one clear source
5. **Faster startup**: Only loading model once

## Lessons Learned

- **Thread safety**: Multiple threads competing for initialization is dangerous
- **Code duplication**: Having two initialization paths was a design flaw
- **Logging value**: The error logging helped identify this bug
- **Test importance**: The test script quickly verifies the fix

## Files Modified

- `src/listen_tools/listen_app.py`:
  - `__init__()` - Added parameters, removed thread start
  - `initialize_model()` - Uses stored configuration
  - `main()` - Simplified to single initialization path
  - Removed `custom_init()` and `custom_init_wrapper()`

## Files Created

- `test_initialization.py` - Verifies single initialization path
- `docs/DOUBLE_INIT_FIX.md` - This document
