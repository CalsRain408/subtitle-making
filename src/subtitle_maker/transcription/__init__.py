"""Speech-to-text adapters."""


class TranscriptionError(RuntimeError):
    """Raised when an ASR backend cannot produce a usable transcription."""
