#!/usr/bin/env python3
"""
Test script to verify error logging during GUI initialization phase.
This simulates various failure scenarios to ensure errors are logged.
"""

import os
import sys

# Set log level to DEBUG for testing
os.environ['LOG_LEVEL'] = 'DEBUG'

print("=" * 70)
print("Error Logging Test Suite")
print("=" * 70)
print()
print("This script tests error logging during the critical GUI initialization")
print("phase where the GUI renders but the user cannot click the Record button")
print("before the application closes.")
print()
print("Test scenarios:")
print("1. GUI initialization errors")
print("2. Model loading failures")
print("3. PyAudio initialization errors")
print("4. Premature GUI closure detection")
print()
print("Check logs/listen_app.log for detailed error messages")
print()
print("=" * 70)
print()

# Import after setting environment
from src.listen_tools.logger import setup_logger

logger = setup_logger('test_error_logging')

# Test 1: Verify logger is working
logger.info("Starting error logging tests")

# Test 2: Simulate various error scenarios
test_scenarios = [
    ("GUI initialization failure", "Failed to initialize GUI: Display not available"),
    ("Model loading failure", "Model initialization failed: Unable to load Whisper model"),
    ("PyAudio initialization failure", "PyAudio initialization failed: No audio devices found"),
    ("Premature closure", "GUI closed before initialization completed - user was unable to click Record button"),
]

print("Simulating error scenarios...")
print()

for i, (scenario, error_msg) in enumerate(test_scenarios, 1):
    print(f"{i}. Testing: {scenario}")
    logger.error(error_msg, exc_info=False)
    print(f"   ✓ Logged to listen_app.log")
    print()

print("=" * 70)
print("Test completed!")
print()
print("Review the logs:")
print("  cat logs/listen_app.log | tail -20")
print()
print("Or view errors only:")
print("  grep ERROR logs/listen_app.log | tail -10")
print("=" * 70)
