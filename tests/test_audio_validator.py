import pytest
from backend.services.audio_validator import AudioValidator, AudioValidationError

def test_valid_audio_files():
    is_valid, msg = AudioValidator.validate_file("meeting.mp3", 1024 * 1024, "audio/mpeg")
    assert is_valid is True

    is_valid, msg = AudioValidator.validate_file("call.wav", 200000, "audio/wav")
    assert is_valid is True

    # Test file between 15MB and 40MB triggers chunking notification
    is_valid, msg = AudioValidator.validate_file("large_meeting.mp3", 25 * 1024 * 1024, "audio/mpeg")
    assert is_valid is True
    assert "automatically split into chunked parts" in msg


def test_invalid_extension():
    with pytest.raises(AudioValidationError) as excinfo:
        AudioValidator.validate_file("document.pdf", 5000)
    assert "Unsupported file extension" in str(excinfo.value)


def test_empty_file():
    with pytest.raises(AudioValidationError) as excinfo:
        AudioValidator.validate_file("audio.mp3", 0)
    assert "empty (0 bytes)" in str(excinfo.value)


def test_oversized_file():
    max_bytes = 41 * 1024 * 1024  # 41MB > 40MB limit
    with pytest.raises(AudioValidationError) as excinfo:
        AudioValidator.validate_file("extra_large.mp3", max_bytes)
    assert "exceeds maximum allowed limit of 40 MB" in str(excinfo.value)
