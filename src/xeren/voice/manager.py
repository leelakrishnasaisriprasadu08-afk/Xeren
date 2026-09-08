"""VoiceSessionManager — Orchestrates two-way local speech conversation."""

from __future__ import annotations

import logging
from typing import Optional

from xeren.voice.stt import LocalSpeechRecognizer, TranscriptionResult
from xeren.voice.tts import LocalSpeechSynthesizer, AudioOutput
from xeren.core.dispatcher import XerenDispatcher, DispatchResponse

logger = logging.getLogger("xeren.voice.manager")


class VoiceSessionManager:
    """
    Manages interactive speech conversations with Xeren.
    Listens to user speech -> Transcribes via Whisper -> Dispatches intent -> Synthesizes voice answer.
    """

    def __init__(
        self,
        stt: Optional[LocalSpeechRecognizer] = None,
        tts: Optional[LocalSpeechSynthesizer] = None,
        dispatcher: Optional[XerenDispatcher] = None,
    ) -> None:
        self.stt = stt or LocalSpeechRecognizer()
        self.tts = tts or LocalSpeechSynthesizer()
        self.dispatcher = dispatcher or XerenDispatcher()
        self.is_listening: bool = False

    def process_voice_turn(self, audio_input: bytes) -> tuple[str, AudioOutput, DispatchResponse]:
        """
        End-to-end spoken turn:
        1. Transcribe audio to text.
        2. Automatically dispatch user intent.
        3. Synthesize speech for the response.
        """
        transcription = self.stt.transcribe_audio_bytes(audio_input)
        spoken_text = transcription.text

        # Route through intelligent dispatcher
        dispatch_resp = self.dispatcher.dispatch(spoken_text)

        reply_text = (
            f"Processed your request for {dispatch_resp.plugin_name}. Everything is up to date."
            if dispatch_resp.success
            else f"I encountered an issue: {dispatch_resp.error}"
        )

        audio_output = self.tts.synthesize(reply_text)
        return spoken_text, audio_output, dispatch_resp


__all__ = ["VoiceSessionManager"]
