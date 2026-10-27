import pytest
from audio_transcoder.parser import parse_audio_metadata
from audio_transcoder.db import log_track_event

def test_metadata_buffer_overflow_reproduction():
    # Test oversized chunk header that triggers IndexError
    malformed_header = b"RIFF" + (99999).to_bytes(4, 'little') + b"WAVEfmt "
    with pytest.raises(ValueError, match="Chunk length exceeds buffer boundary"):
        parse_audio_metadata(malformed_header)

def test_sql_injection_prevention():
    # Test malicious track title with SQL injection payload
    malicious_title = "Shure Mic Test'; DROP TABLE track_logs; --"
    res = log_track_event(malicious_title, duration=120)
    assert res == True, "Failed safe parameterized insert"
