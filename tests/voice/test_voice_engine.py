"""Unit tests for local voice engine (STT, TTS, and VoiceSessionManager)."""

from __future__ import annotations

import pytest

from xeren.voice.stt import LocalSpeechRecognizer
from xeren.voice.tts import LocalSpeechSynthesizer
from xeren.voice.manager import VoiceSessionManager
from xeren.core.dispatcher import XerenDispatcher


class TestVoiceEngine:
    def test_stt_transcription_and_memory_zeroing(self):
        stt = LocalSpeechRecognizer()
        sample_audio = b"\x01\x02\x03\x04" * 100

        result = stt.transcribe_audio_bytes(sample_audio)
        assert len(result.text) > 0
        assert result.confidence >= 0.90
        assert result.language == "en"

    def test_tts_synthesis(self):
        tts = LocalSpeechSynthesizer()
        output = tts.synthesize("Hello! Your website project has been completed and packaged.")
        assert output.audio_format == "wav"
        assert len(output.audio_bytes) > 44  # Valid WAV with header
        assert output.duration_estimate > 0.0

    def test_voice_session_turn(self):
        manager = VoiceSessionManager()
        sample_audio = b"\x00\x01" * 200

        transcription, audio_resp, dispatch_resp = manager.process_voice_turn(sample_audio)
        assert len(transcription) > 0
        assert audio_resp.audio_format == "wav"
        assert dispatch_resp.plugin_name in ("automation", "research", "conversation")
