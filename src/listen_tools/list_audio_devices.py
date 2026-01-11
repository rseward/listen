#!/usr/bin/env python3
"""
List Audio Devices - Utility to display available PyAudio devices.

This script lists all available audio devices with their properties including
device index, name, sample rate, channels, and host API.
"""

import sys
import os
import click
import pyaudio
from .logger import setup_logger

# Set up logger
logger = setup_logger(__name__)


def suppress_alsa_warnings(func):
    """Decorator to suppress ALSA warnings during PyAudio operations."""
    def wrapper(*args, **kwargs):
        # Temporarily redirect stderr to suppress ALSA warnings
        stderr_fd = sys.stderr.fileno()
        with open(os.devnull, 'w') as devnull:
            old_stderr = os.dup(stderr_fd)
            os.dup2(devnull.fileno(), stderr_fd)
            try:
                return func(*args, **kwargs)
            finally:
                os.dup2(old_stderr, stderr_fd)
                os.close(old_stderr)
    return wrapper


@suppress_alsa_warnings
def get_audio_devices():
    """Get information about all audio devices."""
    pa = pyaudio.PyAudio()
    devices = []
    
    try:
        default_input = pa.get_default_input_device_info()
        default_input_idx = default_input['index']
    except IOError:
        default_input_idx = None
    
    try:
        default_output = pa.get_default_output_device_info()
        default_output_idx = default_output['index']
    except IOError:
        default_output_idx = None
    
    for i in range(pa.get_device_count()):
        try:
            info = pa.get_device_info_by_index(i)
            host_api_info = pa.get_host_api_info_by_index(info['hostApi'])
            
            devices.append({
                'index': info['index'],
                'name': info['name'],
                'host_api': host_api_info['name'],
                'sample_rate': int(info['defaultSampleRate']),
                'max_input_channels': info['maxInputChannels'],
                'max_output_channels': info['maxOutputChannels'],
                'is_default_input': info['index'] == default_input_idx,
                'is_default_output': info['index'] == default_output_idx,
            })
        except Exception as e:
            logger.warning(f"Error getting info for device {i}: {e}")
    
    pa.terminate()
    return devices


def format_devices_table(devices, show_all=False):
    """Format devices as a table."""
    if not devices:
        return "No audio devices found."
    
    # Filter devices if not showing all
    if not show_all:
        devices = [d for d in devices if d['max_input_channels'] > 0 or d['max_output_channels'] > 0]
    
    if not devices:
        return "No input/output audio devices found."
    
    lines = []
    lines.append("=" * 100)
    lines.append(f"{'IDX':<4} {'NAME':<45} {'RATE':<8} {'IN':<4} {'OUT':<4} {'HOST API':<15} {'DEFAULT':<10}")
    lines.append("=" * 100)
    
    for device in devices:
        idx = f"{device['index']}"
        name = device['name'][:44]  # Truncate long names
        rate = f"{device['sample_rate']} Hz"
        in_ch = str(device['max_input_channels'])
        out_ch = str(device['max_output_channels'])
        host = device['host_api'][:14]
        
        default_marker = ""
        if device['is_default_input']:
            default_marker += "IN "
        if device['is_default_output']:
            default_marker += "OUT"
        
        lines.append(f"{idx:<4} {name:<45} {rate:<8} {in_ch:<4} {out_ch:<4} {host:<15} {default_marker:<10}")
    
    lines.append("=" * 100)
    lines.append("")
    lines.append("Legend:")
    lines.append("  IDX      - Device index (use this for AUDIO_DEVICE_INDEX in .env)")
    lines.append("  NAME     - Device name")
    lines.append("  RATE     - Default sample rate in Hz")
    lines.append("  IN       - Maximum input channels (0 = no input)")
    lines.append("  OUT      - Maximum output channels (0 = no output)")
    lines.append("  HOST API - Audio host API")
    lines.append("  DEFAULT  - System default device (IN = input, OUT = output)")
    
    return "\n".join(lines)


def format_devices_detailed(devices, show_all=False):
    """Format devices with detailed information."""
    if not devices:
        return "No audio devices found."
    
    # Filter devices if not showing all
    if not show_all:
        devices = [d for d in devices if d['max_input_channels'] > 0 or d['max_output_channels'] > 0]
    
    if not devices:
        return "No input/output audio devices found."
    
    lines = []
    for device in devices:
        lines.append("=" * 80)
        lines.append(f"Device {device['index']}: {device['name']}")
        lines.append("-" * 80)
        lines.append(f"  Host API:          {device['host_api']}")
        lines.append(f"  Default Sample Rate: {device['sample_rate']} Hz")
        lines.append(f"  Input Channels:    {device['max_input_channels']}")
        lines.append(f"  Output Channels:   {device['max_output_channels']}")
        
        default_info = []
        if device['is_default_input']:
            default_info.append("Default Input")
        if device['is_default_output']:
            default_info.append("Default Output")
        if default_info:
            lines.append(f"  Default:           {', '.join(default_info)}")
        
        lines.append("")
    
    lines.append("=" * 80)
    return "\n".join(lines)


@click.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "detailed"], case_sensitive=False),
    default="table",
    help="Output format (default: table)",
)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    help="Show all devices including those with no input/output",
)
@click.option(
    "--input-only",
    "-i",
    is_flag=True,
    help="Show only input devices",
)
@click.option(
    "--output-only",
    "-o",
    is_flag=True,
    help="Show only output devices",
)
@click.version_option(version="0.1.0", prog_name="list-audio-devices")
def main(format, all, input_only, output_only):
    """
    List available audio devices with their properties.
    
    This utility displays all PyAudio devices with information about their
    index, name, sample rate, channels, and host API. Use this to find the
    correct device index for the AUDIO_DEVICE_INDEX setting in .env.
    
    Examples:
    
        \b
        # List all input/output devices in table format
        list-audio-devices
        
        \b
        # Show detailed information
        list-audio-devices --format detailed
        
        \b
        # Show only input devices
        list-audio-devices --input-only
        
        \b
        # Show all devices including those with no input/output
        list-audio-devices --all
    """
    try:
        devices = get_audio_devices()
        
        # Filter by input/output if requested
        if input_only:
            devices = [d for d in devices if d['max_input_channels'] > 0]
        elif output_only:
            devices = [d for d in devices if d['max_output_channels'] > 0]
        
        # Format and display
        if format == "table":
            output = format_devices_table(devices, show_all=all)
        else:  # detailed
            output = format_devices_detailed(devices, show_all=all)
        
        print(output)
        
    except Exception as e:
        logger.error(f"Error listing audio devices: {e}", exc_info=True)
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
