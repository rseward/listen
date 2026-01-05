#!/usr/bin/env python3
"""
Listen - Audio transcription application with GUI.

This application provides a simple GUI for recording audio and transcribing it
using faster-whisper. The transcription is displayed in real-time and output
to stdout when the recording is stopped.
"""

import customtkinter as ctk
import pyaudio
import numpy as np
import time
import threading
from faster_whisper import WhisperModel
import sys
import click
from .logger import setup_logger

# Set up logger
logger = setup_logger(__name__)


class ListenApp(ctk.CTk):
    def __init__(self, model_size="base", cuda=False):
        try:
            logger.debug("Initializing ListenApp GUI")
            super().__init__()

            # Store configuration
            self.model_size = model_size
            self.cuda = cuda

            # Window configuration
            self.title("Listen")
            self.geometry("400x300")
            self.resizable(False, False)

            # Center the window
            self.update_idletasks()
            width = self.winfo_width()
            height = self.winfo_height()
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
            self.geometry(f'{width}x{height}+{x}+{y}')

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
            self.ready_to_record = False  # Track if initialization completed

            # Audio settings
            self.CHUNK = 1024
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.RATE = 16000
            self.RECORD_SECONDS = 5

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
            main_frame,
            text="Initializing...",
            font=("Arial", 14)
        )
        self.status_label.pack(pady=10)

        # Record button
        self.record_button = ctk.CTkButton(
            main_frame,
            text="🎤 Record",
            command=self.toggle_recording,
            width=200,
            height=60,
            font=("Arial", 18, "bold"),
            state="disabled"
        )
        self.record_button.pack(pady=20)

        # Transcription display
        self.transcription_frame = ctk.CTkScrollableFrame(
            main_frame,
            width=360,
            height=120
        )
        self.transcription_frame.pack(pady=10, fill="both", expand=True)

        self.transcription_label = ctk.CTkLabel(
            self.transcription_frame,
            text="",
            wraplength=340,
            justify="left",
            font=("Arial", 12)
        )
        self.transcription_label.pack(pady=5)

    def _initialize_model_wrapper(self):
        """Wrapper to catch any uncaught exceptions during model initialization"""
        try:
            self.initialize_model()
        except Exception as e:
            logger.error(f"Uncaught exception in model initialization thread: {e}", exc_info=True)
            self.after(0, lambda: self.show_error(f"Critical initialization error: {e}"))

    def initialize_model(self):
        """Initialize the Whisper model"""
        try:
            # Model configuration from stored settings
            device = "cuda" if self.cuda else "cpu"
            compute_type = "float16" if self.cuda else "int8"

            logger.debug(f"Initializing Whisper model: size={self.model_size}, device={device}, compute_type={compute_type}")
            self.model = WhisperModel(self.model_size, device=device, compute_type=compute_type)
            logger.info("Whisper model loaded successfully")

            # Initialize audio interface
            logger.debug("Initializing PyAudio interface")
            self.audio_interface = pyaudio.PyAudio()
            logger.info("PyAudio interface initialized successfully")

            self.after(0, self.model_loaded)
        except Exception as e:
            logger.error(f"Model initialization failed: {e}", exc_info=True)
            self.after(0, lambda: self.show_error(f"Model initialization failed: {e}"))

    def model_loaded(self):
        """Called when model is successfully loaded"""
        self.status_label.configure(text="Ready to record")
        self.record_button.configure(state="normal")
        self.ready_to_record = True
        logger.info("Application ready - user can now record")

    def show_error(self, message):
        """Display error message and schedule window close"""
        logger.error(f"Displaying error to user: {message}")
        self.status_label.configure(text=f"Error: {message}")
        # Close window after 5 seconds to allow user to read error
        logger.warning("GUI will close in 5 seconds due to initialization error")
        self.after(5000, self.quit)

    def toggle_recording(self):
        """Toggle recording on/off"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start audio recording and transcription"""
        logger.info("Starting audio recording")
        self.is_recording = True
        self.transcription_text = []
        self.last_audio_time = time.time()

        self.record_button.configure(text="Stop")
        self.status_label.configure(text="Recording...")
        self.transcription_label.configure(text="")

        # Start recording thread
        self.recording_thread = threading.Thread(target=self.record_and_transcribe, daemon=True)
        self.recording_thread.start()

        # Start silence detection
        self.check_silence()

    def stop_recording(self):
        """Stop audio recording"""
        self.is_recording = False
        self.status_label.configure(text="Processing...")

        if self.recording_thread:
            self.recording_thread.join(timeout=2)

        # Close the window after stopping
        self.after(100, self.quit)

    def record_and_transcribe(self):
        """Main recording and transcription loop"""
        try:
            # Open audio stream
            logger.debug(f"Opening audio stream: format={self.FORMAT}, channels={self.CHANNELS}, rate={self.RATE}")
            self.stream = self.audio_interface.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=None,
                start=True
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

                # Check if audio has content (not silence)
                audio_level = np.abs(audio_data).mean()
                if audio_level > 0.01:  # Threshold for detecting speech
                    self.last_audio_time = time.time()

                # Transcribe the chunk
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
            self.after(0, lambda: self.show_error(f"Recording failed: {e}"))
        finally:
            if self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass

    def update_transcription_display(self):
        """Update the transcription text in the GUI"""
        display_text = " ".join(self.transcription_text)
        self.after(0, lambda: self.transcription_label.configure(text=display_text))

    def check_silence(self):
        """Check for silence and auto-close window if needed"""
        if self.is_recording:
            if self.last_audio_time:
                silence_duration = time.time() - self.last_audio_time
                if silence_duration >= self.silence_threshold:
                    # Stop recording and close
                    self.stop_recording()
                    self.after(100, self.quit)
                    return

            # Check again in 1 second
            self.after(1000, self.check_silence)

    def on_closing(self):
        """Handle window closing"""
        # Check if window closed before initialization completed
        if not self.ready_to_record:
            logger.error("GUI closed before initialization completed - user was unable to click Record button")
            logger.error("This indicates a critical startup failure")

        self.is_recording = False

        try:
            if self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logger.warning(f"Error closing audio stream: {e}")

            if self.audio_interface:
                try:
                    self.audio_interface.terminate()
                except Exception as e:
                    logger.warning(f"Error terminating audio interface: {e}")
        finally:
            # Output final transcription to stdout
            final_text = " ".join(self.transcription_text)
            if final_text:
                logger.debug(f"Outputting transcription on close: {len(final_text)} chars")
            print(final_text)
            sys.stdout.flush()

        self.destroy()


@click.command()
@click.option('--model-size', '-m',
              default='base',
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large-v3'], case_sensitive=False),
              help='Whisper model size (default: base)')
@click.option('--silence-threshold', '-s',
              default=15,
              type=int,
              help='Seconds of silence before auto-close (default: 15)')
@click.option('--cuda/--no-cuda',
              default=False,
              help='Use CUDA GPU acceleration (requires NVIDIA GPU)')
@click.version_option(version='0.1.0', prog_name='listen')
def main(model_size, silence_threshold, cuda):
    logger.info(f"Starting listen application: model_size={model_size}, silence_threshold={silence_threshold}, cuda={cuda}")
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
        app = ListenApp(model_size=model_size, cuda=cuda)
    except Exception as e:
        logger.error(f"Failed to create GUI application: {e}", exc_info=True)
        logger.error("Application cannot start - GUI initialization failed")
        sys.exit(1)

    # Apply command-line options
    app.silence_threshold = silence_threshold

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
        final_text = " ".join(app.transcription_text)
        if final_text:
            logger.debug(f"Outputting final transcription ({len(final_text)} chars)")
        print(final_text)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
