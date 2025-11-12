# SkillSync/utils/speech_to_text.py

import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
import io

# --- Model Loading ---
# We load the model and processor once when the server starts.
# This prevents reloading them on every request, which is very slow.
# Using .en model for English-only, which is faster.
MODEL_NAME = "openai/whisper-base.en" 
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading Whisper model: {MODEL_NAME} on device: {DEVICE}")
try:
    processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)
    print("Whisper model loaded successfully.")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    # In a real app, you might want to stop the server if the model fails to load
    processor = None
    model = None

# --- Transcription Function ---

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribes the given audio file using the pre-loaded Whisper model.
    
    Args:
        audio_file_path: The path to the saved audio file (e.g., .wav, .mp3).

    Returns:
        The transcribed text as a string.
    """
    if model is None or processor is None:
        print("Error: Whisper model is not loaded.")
        return "[Transcription Error: Model not loaded]"

    try:
        # --- 1. Load and Resample Audio ---
        # Whisper models require audio to be at 16,000 Hz sample rate.
        # `librosa.load` handles conversion from various formats and resampling.
        speech_array, sampling_rate = librosa.load(audio_file_path, sr=16000)

        # --- 2. Process Audio ---
        # The processor converts the audio array into the format the model expects.
        input_features = processor(
            speech_array, 
            sampling_rate=16000, 
            return_tensors="pt"
        ).input_features

        # Move tensors to the correct device (CPU or GPU)
        input_features = input_features.to(DEVICE)

        # --- 3. Generate Transcription ---
        # Generate token IDs
        predicted_ids = model.generate(input_features)

        # --- 4. Decode Tokens to Text ---
        # Decode the token IDs into a human-readable string
        transcription = processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )

        # The result is a list, so we take the first element
        return transcription[0].strip()

    except Exception as e:
        print(f"Error during transcription: {e}")
        return f"[Transcription Error: {e}]"