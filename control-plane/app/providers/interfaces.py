import enum


class TelephonyProvider(str, enum.Enum):
    exotel = "exotel"
    plivo = "plivo"
    twilio = "twilio"
    telnyx = "telnyx"


class STTProvider(str, enum.Enum):
    sarvam = "sarvam"
    deepgram = "deepgram"


class TTSProvider(str, enum.Enum):
    sarvam = "sarvam"
    elevenlabs = "elevenlabs"
    cartesia = "cartesia"


class LLMProvider(str, enum.Enum):
    gemini = "gemini"
    openai = "openai"
