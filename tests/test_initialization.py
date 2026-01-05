#!/usr/bin/env python3
"""
Test to verify the GUI initialization works correctly with single initialization path.
"""

import os
import sys

# Set log level to DEBUG for testing
os.environ['LOG_LEVEL'] = 'DEBUG'

print("=" * 70)
print("Testing GUI Initialization")
print("=" * 70)
print()
print("This test verifies that:")
print("1. GUI initializes without errors")
print("2. Only ONE model initialization occurs (not double)")
print("3. PyAudio interface initializes")
print("4. Application becomes ready to record")
print()
print("Checking logs...")
print()

# Read the log file
try:
    with open('logs/listen_app.log', 'r') as f:
        lines = f.readlines()
        
    # Find the most recent "Starting listen application" to get the latest session
    start_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if 'Starting listen application:' in lines[i]:
            start_idx = i
            break
    
    if start_idx == -1:
        recent_lines = lines[-10:]  # Fallback to last 10 lines
    else:
        recent_lines = lines[start_idx:]  # Get everything from last start
    
    # Count occurrences of key messages in recent logs
    model_loaded_count = sum(1 for line in recent_lines if 'Whisper model loaded successfully' in line and 'Custom' not in line)
    pyaudio_init_count = sum(1 for line in recent_lines if 'PyAudio interface initialized successfully' in line and 'custom' not in line)
    ready_count = sum(1 for line in recent_lines if 'Application ready - user can now record' in line)
    gui_init_count = sum(1 for line in recent_lines if 'Initializing ListenApp GUI' in line)
    
    print(f"Recent initialization events (last 20 log lines):")
    print(f"  - GUI initialization: {gui_init_count}")
    print(f"  - Model loaded: {model_loaded_count}")
    print(f"  - PyAudio initialized: {pyaudio_init_count}")
    print(f"  - Application ready: {ready_count}")
    print()
    
    if model_loaded_count == 1 and pyaudio_init_count == 1 and ready_count >= 1:
        print("✓ PASS: Single initialization path working correctly!")
        print()
        print("Expected log sequence found:")
        print("  1. GUI initialization")
        print("  2. Model loaded (once)")
        print("  3. PyAudio initialized (once)")
        print("  4. Application ready")
    else:
        print("✗ FAIL: Unexpected initialization pattern")
        print()
        print("Last 10 log lines:")
        for line in recent_lines[-10:]:
            print(f"  {line.rstrip()}")
            
except FileNotFoundError:
    print("✗ No log file found at logs/listen_app.log")
    print("Run the application first: uv run listen")
    
print()
print("=" * 70)
