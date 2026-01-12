#!/usr/bin/env python3
"""
Listen - Audio transcription application with GUI.

This application provides a simple GUI for recording audio and transcribing it
using faster-whisper. The transcription is displayed in real-time and output
to stdout when the recording is stopped.
"""

import os
# Suppress ALSA error messages
os.environ['ALSA_CARD'] = 'default'

import customtkinter as ctk
import pyaudio
import numpy as np
import time
import threading
from faster_whisper import WhisperModel
import sys
import click
import wave
from datetime import datetime
from dotenv import load_dotenv
from .logger import setup_logger
import subprocess

# Load environment variables
load_dotenv()

# Set up logger
logger = setup_logger(__name__)


class ListenApp(ctk.CTk):
    def __init__(self, model_size="base", cuda=False, debug=False):
        try:
            logger.debug("Initializing ListenApp GUI")
            super().__init__()

            # Store configuration
            self.model_size = model_size
            self.cuda = cuda
            self.debug = debug

            # Window configuration
            self.title("Listen")
            self.geometry("600x500")
            self.resizable(False, False)

            # Center the window
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
            self.geometry(f"{width}x{height}+{x}+{y}")

            # Set appearance
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("blue")

            # Recording state
            self.is_recording = False
            self.recording_thread = None
            self.transcription_text = []
            self.last_audio_time = None
            self.silence_threshold = 15  # seconds
            self.model = None
            self.audio_interface = None
            self.stream = None
            self.stream_lock = threading.Lock()  # Protect stream cleanup
            self.cleanup_done = False  # Prevent double cleanup
            self.ready_to_record = False  # Track if initialization completed

            # Audio settings
            self.CHUNK = 1024
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.RATE = None  # Will be set during initialization
            self.RECORD_SECONDS = 5
            self.device_index = None  # Will be set during initialization
            self.sample_width = None  # Cache sample width for debug mode

            # UI Components
            self.create_widgets()
            logger.debug("GUI widgets created successfully")

            # Set initial status - model initialization will be started by caller
            self.status_label.configure(text="Loading model...")
            self.update()
        except Exception as e:
            logger.error(f"Failed to initialize GUI: {e}", exc_info=True)
            raise

    def create_widgets(self):
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Status label
        self.status_label = ctk.CTkLabel(
            main_frame, text="Initializing...", font=("Arial", 14)
        )
        self.status_label.pack(pady=10)

        # Multi-line text box for transcription (editable)
        self.transcription_textbox = ctk.CTkTextbox(
            main_frame,
            width=560,
            height=300,
            font=("Arial", 12),
        )
        self.transcription_textbox.pack(pady=10, fill="both", expand=True)

        # Button frame for horizontal layout
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(pady=10)

        # Record button (left)
        self.record_button = ctk.CTkButton(
            button_frame,
            text="Record",
            command=self.toggle_recording,
            width=150,
            height=50,
            font=("Arial", 14, "bold"),
            state="disabled",
        )
        self.record_button.pack(side="left", padx=5)

        # Improve button (middle)
        self.improve_button = ctk.CTkButton(
            button_frame,
            text="Improve",
            command=self.improve_text,
            width=150,
            height=50,
            font=("Arial", 14, "bold"),
            state="disabled",
        )
        self.improve_button.pack(side="left", padx=5)

        # Finish button (right)
        self.finish_button = ctk.CTkButton(
            button_frame,
            text="Finish",
            command=self.finish_and_close,
            width=150,
            height=50,
            font=("Arial", 14, "bold"),
            state="disabled",
        )
        self.finish_button.pack(side="left", padx=5)

    def _initialize_model_wrapper(self):
        """Wrapper to catch any uncaught exceptions during model initialization"""
        try:
            self.initialize_model()
        except Exception as e:
            logger.error(
                f"Uncaught exception in model initialization thread: {e}", exc_info=True
            )
            self.after(
                0, lambda: self.show_error(f"Critical initialization error: {e}")
            )

    def initialize_model(self):
        """Initialize the Whisper model"""
        try:
            # Model configuration from stored settings
            device = "cuda" if self.cuda else "cpu"
            compute_type = "float16" if self.cuda else "int8"

            logger.debug(
                f"Initializing Whisper model: size={self.model_size}, device={device}, compute_type={compute_type}"
            )
            self.model = WhisperModel(
                self.model_size, device=device, compute_type=compute_type
            )
            logger.info("Whisper model loaded successfully")

            # Initialize audio interface (suppress ALSA warnings)
            logger.debug("Initializing PyAudio interface")
            # Temporarily redirect stderr to suppress ALSA warnings
            stderr_fd = sys.stderr.fileno()
            with open(os.devnull, 'w') as devnull:
                old_stderr = os.dup(stderr_fd)
                os.dup2(devnull.fileno(), stderr_fd)
                try:
                    self.audio_interface = pyaudio.PyAudio()
                finally:
                    os.dup2(old_stderr, stderr_fd)
                    os.close(old_stderr)
            logger.info("PyAudio interface initialized successfully")

            # Cache sample width for debug mode (to avoid race condition)
            self.sample_width = self.audio_interface.get_sample_size(self.FORMAT)

            # Auto-detect device and sample rate
            self.detect_audio_settings()
            logger.info(f"Audio configuration: device={self.device_index}, rate={self.RATE} Hz, channels={self.CHANNELS}")

            self.after(0, self.model_loaded)
        except Exception as e:
            logger.error(f"Model initialization failed: {e}", exc_info=True)
            self.after(0, lambda: self.show_error(f"Model initialization failed: {e}"))

    def detect_audio_settings(self):
        """Auto-detect audio device and optimal sample rate"""
        try:
            # Check for environment variable overrides
            env_device_index = os.getenv('AUDIO_DEVICE_INDEX')
            env_sample_rate = os.getenv('AUDIO_SAMPLE_RATE')

            # Get default input device
            default_info = self.audio_interface.get_default_input_device_info()
            default_device_index = default_info['index']
            default_rate = int(default_info['defaultSampleRate'])

            logger.debug(f"Default device: {default_info['name']}")
            logger.debug(f"Default sample rate: {default_rate} Hz")

            # Use environment variable for device index if set
            if env_device_index:
                try:
                    self.device_index = int(env_device_index)
                    device_info = self.audio_interface.get_device_info_by_index(self.device_index)
                    logger.info(f"Using device from .env: {self.device_index} ({device_info['name']})")
                except (ValueError, IOError) as e:
                    logger.warning(f"Invalid AUDIO_DEVICE_INDEX={env_device_index}: {e}. Using default.")
                    self.device_index = default_device_index
            else:
                self.device_index = default_device_index

            # Use environment variable for sample rate if set
            if env_sample_rate:
                try:
                    requested_rate = int(env_sample_rate)
                    if self.test_sample_rate(self.device_index, requested_rate):
                        self.RATE = requested_rate
                        logger.info(f"Using sample rate from .env: {self.RATE} Hz")
                        return
                    else:
                        logger.warning(f"AUDIO_SAMPLE_RATE={requested_rate} Hz not supported. Auto-detecting...")
                except ValueError as e:
                    logger.warning(f"Invalid AUDIO_SAMPLE_RATE={env_sample_rate}: {e}. Auto-detecting...")

            # Auto-detect sample rate if not set or invalid
            # Test common sample rates in order of preference
            # Whisper works best with 16000 Hz, but we'll use device default if possible
            preferred_rates = [16000, default_rate, 44100, 48000, 22050, 8000]

            for rate in preferred_rates:
                if self.test_sample_rate(self.device_index, rate):
                    self.RATE = rate
                    logger.info(f"Auto-detected sample rate: {rate} Hz")
                    return

            # Fallback to default if all tests fail
            self.RATE = default_rate
            logger.warning(f"Using untested default sample rate: {default_rate} Hz")

        except Exception as e:
            logger.error(f"Failed to detect audio settings: {e}", exc_info=True)
            # Fallback to conservative settings
            self.device_index = None
            self.RATE = 16000
            logger.warning(f"Using fallback settings: device=default, rate={self.RATE} Hz")

    def test_sample_rate(self, device_index, rate):
        """Test if a sample rate works with the device"""
        try:
            # Try to open stream with this rate
            test_stream = self.audio_interface.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK,
                start=False
            )
            test_stream.close()
            logger.debug(f"Sample rate {rate} Hz: OK")
            return True
        except Exception as e:
            logger.debug(f"Sample rate {rate} Hz: FAILED ({e})")
            return False

    def model_loaded(self):
        """Called when model is successfully loaded"""
        self.status_label.configure(text="Ready to record")
        self.record_button.configure(state="normal")
        self.improve_button.configure(state="normal")
        self.finish_button.configure(state="normal")
        self.ready_to_record = True
        logger.info("Application ready - user can now record")

    def show_error(self, message):
        """Display error message and schedule window close"""
        logger.error(f"Displaying error to user: {message}")
        self.status_label.configure(text=f"Error: {message}")
        # Close window after 5 seconds to allow user to read error
        logger.warning("GUI will close in 5 seconds due to initialization error")
        self.after(5000, self.on_closing)

    def toggle_recording(self):
        """Toggle recording on/off"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start audio recording and transcription"""
        # Log recording session configuration
        try:
            device_info = self.audio_interface.get_device_info_by_index(self.device_index)
            device_name = device_info['name']
        except:
            device_name = f"index {self.device_index}" if self.device_index is not None else "default"

        logger.info("="*60)
        logger.info("Starting new recording session")
        logger.info(f"  Audio Device: {device_name}")
        logger.info(f"  Sample Rate:  {self.RATE} Hz")
        logger.info(f"  Channels:     {self.CHANNELS}")
        logger.info(f"  Format:       {self.FORMAT} (16-bit PCM)")
        logger.info("="*60)

        self.is_recording = True
        self.transcription_text = []
        self.last_audio_time = time.time()

        self.record_button.configure(text="Stop")
        self.status_label.configure(text="Recording...")
        self.transcription_textbox.delete("1.0", "end")

        # Start recording thread
        self.recording_thread = threading.Thread(
            target=self.record_and_transcribe, daemon=True
        )
        self.recording_thread.start()

        # Start silence detection
        self.check_silence()

    def stop_recording(self):
        """Stop audio recording"""
        self.is_recording = False
        self.status_label.configure(text="Processing...")

        if self.recording_thread:
            self.recording_thread.join(timeout=2)

        # Update status to ready after stopping
        self.record_button.configure(text="Record")
        self.status_label.configure(text="Ready to record")

    def record_and_transcribe(self):
        """Main recording and transcription loop"""
        try:
            # Open audio stream
            logger.debug(
                f"Opening audio stream: format={self.FORMAT}, channels={self.CHANNELS}, rate={self.RATE}"
            )
            self.stream = self.audio_interface.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=self.device_index,
                start=True,
            )
            logger.info("Audio stream opened successfully")

            while self.is_recording:
                frames = []

                # Record audio chunk
                for _ in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
                    if not self.is_recording:
                        break
                    try:
                        data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                        frames.append(np.frombuffer(data, dtype=np.int16))
                    except IOError as e:
                        logger.warning(f"Audio read error: {e}")
                        print(f"Audio read error: {e}", file=sys.stderr)
                        time.sleep(0.1)
                        continue

                if not frames or not self.is_recording:
                    continue

                # Convert to float32 and normalize
                audio_data = np.concatenate(frames).astype(np.float32) / 32768.0

                # Debug: Save audio to WAV file
                if self.debug:
                    self.save_audio_debug(frames)

                # Check if audio has content (not silence)
                audio_level = np.abs(audio_data).mean()
                if audio_level > 0.01:  # Threshold for detecting speech
                    self.last_audio_time = time.time()

                # Transcribe the chunk
                # Check if we're still recording (on_closing might have been called)
                if not self.is_recording:
                    break

                try:
                    segments, info = self.model.transcribe(audio_data, beam_size=5)

                    for segment in segments:
                        text = segment.text.strip()
                        if text:
                            self.transcription_text.append(text)
                            self.update_transcription_display()
                            self.last_audio_time = time.time()
                except Exception as e:
                    logger.error(f"Transcription error: {e}", exc_info=True)
                    print(f"Transcription error: {e}", file=sys.stderr)

        except Exception as e:
            logger.error(f"Recording error: {e}", exc_info=True)
            print(f"Recording error: {e}", file=sys.stderr)
            # self.after(0, lambda: self.show_error(f"Recording failed: {e}"))
        finally:
            # Close stream with lock to prevent double cleanup
            with self.stream_lock:
                if self.stream:
                    try:
                        if self.stream.is_active():
                            self.stream.stop_stream()
                        self.stream.close()
                    except Exception as e:
                        logger.warning(f"Error closing stream in recording thread: {e}")
                    finally:
                        self.stream = None

    def save_audio_debug(self, frames):
        """Save recorded audio to WAV file for debugging"""
        try:
            # Create debug directory if it doesn't exist
            debug_dir = "debug_audio"
            os.makedirs(debug_dir, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(debug_dir, f"audio_{timestamp}.wav")

            # Convert frames to bytes
            audio_bytes = np.concatenate(frames).tobytes()

            # Write WAV file
            # Use cached sample_width to avoid race condition with audio_interface cleanup
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.sample_width if self.sample_width else 2)  # Default to 2 bytes (16-bit)
                wf.setframerate(self.RATE)
                wf.writeframes(audio_bytes)

            abs_path = os.path.abspath(filename)
            logger.info(f"Debug audio saved: {abs_path}")
            print(f"Debug audio saved: {abs_path}", file=sys.stderr)
        except Exception as e:
            logger.error(f"Failed to save debug audio: {e}", exc_info=True)

    def update_transcription_display(self):
        """Update the transcription text in the GUI"""
        # Only update if we're still recording (avoid race condition during cleanup)
        if not self.is_recording:
            return
        display_text = " ".join(self.transcription_text)
        try:
            def update_text():
                self.transcription_textbox.delete("1.0", "end")
                self.transcription_textbox.insert("1.0", display_text)
            self.after(0, update_text)
        except Exception as e:
            logger.debug(f"Could not update display (window may be closing): {e}")

    def check_silence(self):
        """Check for silence and auto-close window if needed"""
        if self.is_recording:
            if self.last_audio_time:
                silence_duration = time.time() - self.last_audio_time
                if silence_duration >= self.silence_threshold:
                    # Stop recording
                    self.stop_recording()
                    return

            # Check again in 1 second
            self.after(1000, self.check_silence)

    def improve_text(self):
        """Improve the text in the textbox using the improve command"""
        try:
            # Get current text from textbox
            current_text = self.transcription_textbox.get("1.0", "end").strip()

            if not current_text:
                logger.warning("No text to improve")
                self.status_label.configure(text="No text to improve")
                self.after(2000, lambda: self.status_label.configure(text="Ready to record"))
                return

            # Update status
            self.status_label.configure(text="Improving text...")
            logger.info(f"Improving text (length: {len(current_text)} chars)")

            # Run improve command in a separate thread
            def run_improve():
                try:
                    # Run the improve command with text as stdin
                    result = subprocess.run(
                        ["improve", "--raw"],
                        input=current_text,
                        capture_output=True,
                        text=True,
                        timeout=60  # 60 second timeout
                    )

                    if result.returncode == 0:
                        improved_text = result.stdout.strip()
                        logger.info(f"Text improved successfully (length: {len(improved_text)} chars)")

                        # Update textbox with improved text
                        def update_ui():
                            self.transcription_textbox.delete("1.0", "end")
                            self.transcription_textbox.insert("1.0", improved_text)
                            self.status_label.configure(text="Text improved")
                            self.after(2000, lambda: self.status_label.configure(text="Ready to record"))

                        self.after(0, update_ui)
                    else:
                        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                        logger.error(f"Improve command failed: {error_msg}")
                        self.after(0, lambda: self.status_label.configure(text="Improve failed"))
                        self.after(0, lambda: self.after(2000, lambda: self.status_label.configure(text="Ready to record")))

                except subprocess.TimeoutExpired:
                    logger.error("Improve command timed out")
                    self.after(0, lambda: self.status_label.configure(text="Improve timed out"))
                    self.after(0, lambda: self.after(2000, lambda: self.status_label.configure(text="Ready to record")))
                except Exception as e:
                    logger.error(f"Error running improve command: {e}", exc_info=True)
                    self.after(0, lambda: self.status_label.configure(text="Improve error"))
                    self.after(0, lambda: self.after(2000, lambda: self.status_label.configure(text="Ready to record")))

            improve_thread = threading.Thread(target=run_improve, daemon=True)
            improve_thread.start()

        except Exception as e:
            logger.error(f"Failed to improve text: {e}", exc_info=True)
            self.status_label.configure(text="Improve failed")
            self.after(2000, lambda: self.status_label.configure(text="Ready to record"))

    def finish_and_close(self):
        """Print the text from the textbox to stdout and close the UI"""
        try:
            # Get current text from textbox
            final_text = self.transcription_textbox.get("1.0", "end").strip()

            # Update transcription_text for on_closing to use
            self.transcription_text = [final_text] if final_text else []

            logger.info(f"Finishing with text (length: {len(final_text)} chars)")

            # Close the window using on_closing
            self.on_closing()
        except Exception as e:
            logger.error(f"Failed to finish: {e}", exc_info=True)
            # Still try to close
            self.on_closing()

    def on_closing(self):
        """Handle window closing"""
        # Prevent double cleanup
        if self.cleanup_done:
            return
        self.cleanup_done = True

        # Check if window closed before initialization completed
        if not self.ready_to_record:
            logger.error(
                "GUI closed before initialization completed - user was unable to click Record button"
            )
            logger.error("This indicates a critical startup failure")

        self.is_recording = False

        # Wait for recording thread to finish before cleanup
        # This is CRITICAL - we must wait for transcription to complete
        # before terminating PyAudio, otherwise we get segfaults
        if self.recording_thread and self.recording_thread.is_alive():
            logger.debug("Waiting for recording thread to complete...")
            self.recording_thread.join(timeout=10)  # Longer timeout for transcription
            if self.recording_thread.is_alive():
                logger.warning("Recording thread did not finish in time")

        try:
            # Close stream with lock to prevent race condition
            with self.stream_lock:
                if self.stream:
                    try:
                        if self.stream.is_active():
                            self.stream.stop_stream()
                        self.stream.close()
                    except Exception as e:
                        logger.warning(f"Error closing audio stream: {e}")
                    finally:
                        self.stream = None

            # Terminate audio interface ONLY after thread has finished
            if self.audio_interface:
                try:
                    self.audio_interface.terminate()
                    logger.debug("PyAudio interface terminated")
                except Exception as e:
                    logger.warning(f"Error terminating audio interface: {e}")
                finally:
                    self.audio_interface = None
        finally:
            # Output final transcription to stdout
            final_text = " ".join(self.transcription_text) if isinstance(self.transcription_text, list) else ""
            if final_text:
                logger.debug(
                    f"Outputting transcription on close: {len(final_text)} chars"
                )
            print(final_text)
            sys.stdout.flush()

        # Use quit() instead of destroy() to properly end the mainloop
        # This prevents segfaults that can occur when destroy() is called
        # while the event loop is still processing
        self.quit()


@click.command()
@click.option(
    "--model-size",
    "-m",
    default="base",
    type=click.Choice(
        ["tiny", "base", "small", "medium", "large-v3"], case_sensitive=False
    ),
    help="Whisper model size (default: base)",
)
@click.option(
    "--silence-threshold",
    "-s",
    default=15,
    type=int,
    help="Seconds of silence before auto-close (default: 15)",
)
@click.option(
    "--cuda/--no-cuda",
    default=False,
    help="Use CUDA GPU acceleration (requires NVIDIA GPU)",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Enable debug mode (saves audio chunks to WAV files)",
)
@click.version_option(version="0.1.0", prog_name="listen")
def main(model_size, silence_threshold, cuda, debug):
    logger.info(
        f"Starting listen application: model_size={model_size}, silence_threshold={silence_threshold}, cuda={cuda}, debug={debug}"
    )
    """
    Audio transcription tool with real-time GUI display.

    Records audio from your microphone and transcribes it using faster-whisper.
    The transcription is displayed in real-time in a GUI window and printed to
    stdout when recording stops.

    Features:

        \b
        - Real-time transcription display
        - Automatic silence detection
        - Clean GUI interface
        - Stdout output for easy piping

    Usage Examples:

        \b
        # Basic usage
        listen

        \b
        # Pipe to improve for AI enhancement
        listen | improve

        \b
        # Use larger model for better accuracy
        listen --model-size medium

        \b
        # Adjust silence threshold
        listen --silence-threshold 10

        \b
        # Use GPU acceleration
        listen --cuda

    How It Works:

        \b
        1. Opens a GUI window with a Record button
        2. Click Record to start capturing audio
        3. Speak into your microphone
        4. See transcription appear in real-time
        5. Click Stop or wait for silence (default: 15 seconds)
        6. Transcription is printed to stdout

    Tips:

        \b
        - Use a quiet environment for best results
        - Speak clearly and at a moderate pace
        - The 'base' model provides good accuracy/speed balance
        - Use 'medium' or 'large-v3' for better accuracy (slower)
        - Use 'tiny' for fastest processing (less accurate)
    """
    # Create and configure app with command-line options
    try:
        app = ListenApp(model_size=model_size, cuda=cuda, debug=debug)
    except Exception as e:
        logger.error(f"Failed to create GUI application: {e}", exc_info=True)
        logger.error("Application cannot start - GUI initialization failed")
        sys.exit(1)

    # Apply command-line options
    app.silence_threshold = silence_threshold

    if debug:
        logger.info("Debug mode enabled - audio chunks will be saved to debug_audio/")
        print("Debug mode enabled - audio chunks will be saved to debug_audio/", file=sys.stderr)

    # Start model initialization in background thread
    init_thread = threading.Thread(target=app._initialize_model_wrapper, daemon=True)
    init_thread.start()

    app.protocol("WM_DELETE_WINDOW", app.on_closing)

    try:
        logger.debug("Starting GUI main loop")
        app.mainloop()
        logger.debug("GUI main loop ended")
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Unexpected error during GUI execution: {e}", exc_info=True)
        logger.error("Application terminated due to error")
    finally:
        # Ensure cleanup happens even if on_closing wasn't called
        # This prevents segfault on exit when PyAudio hasn't been terminated
        if not app.cleanup_done:
            logger.debug("Cleanup not done, calling on_closing from finally block")
            try:
                app.on_closing()
            except Exception as e:
                logger.warning(f"Error during final cleanup: {e}")


if __name__ == "__main__":
    main()
