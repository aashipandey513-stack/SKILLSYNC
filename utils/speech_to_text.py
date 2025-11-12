# SkillSync/utils/speech_to_text.py

import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
import io

# --- Model Loading ---
MODEL_NAME = "openai/whisper-base.en" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading Whisper model: {MODEL_NAME} on device: {DEVICE}")
try:
    processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)
    print("Whisper model loaded successfully.")
except Exception as e:
    print(f"CRITICAL: Error loading Whisper model: {e}")
    processor = None
    model = None

# --- Transcription Function ---

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribes the given audio file using the pre-loaded Whisper model.
    """
    if model is None or processor is None:
        print("Error: Whisper model is not loaded.")
        return "[Transcription Error: Model not loaded]"

    try:
        # 1. Load and Resample Audio
        speech_array, sampling_rate = librosa.load(audio_file_path, sr=16000)

        # 2. Process Audio
        input_features = processor(
            speech_array, 
            sampling_rate=16000, 
            return_tensors="pt"
        ).input_features

        input_features = input_features.to(DEVICE)

        # 3. Generate Transcription
        predicted_ids = model.generate(input_features)

        # 4. Decode Tokens to Text
        transcription = processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )

        return transcription[0].strip()

    except Exception as e:
        print(f"Error during transcription: {e}")
        return f"[Transcription Error: {e}]"