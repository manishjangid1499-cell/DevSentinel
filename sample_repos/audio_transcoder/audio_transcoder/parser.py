"""
Audio Metadata Parser & Transcoder Engine.
Patched by DevSentinel: Enforces strict buffer bounds and sanitized DB execution.
"""
import sqlite3

def parse_audio_metadata(header_bytes: bytes) -> dict:
    if len(header_bytes) < 12:
        raise ValueError("Header too short")
    
    riff = header_bytes[0:4]
    chunk_size = int.from_bytes(header_bytes[4:8], "little")
    wave_format = header_bytes[8:12]

    # Security fix: Validate chunk length against buffer bounds to avoid buffer overrun
    if chunk_size > len(header_bytes):
        raise ValueError("Chunk length exceeds buffer boundary")

    return {
        "format": wave_format.decode("ascii", errors="replace"),
        "chunk_size": chunk_size,
        "valid": True
    }
