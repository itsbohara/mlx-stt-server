"""
OpenAI-Compatible API Server for Parakeet STT
Uses FastAPI to serve Parakeet model with OpenAI-compatible endpoints
"""

import io
import json
import logging
import os
import tempfile

import mlx.core as mx
import numpy as np
import parakeet_mlx
import soundfile as sf
from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Parakeet STT Server",
    description="OpenAI-compatible Speech-to-Text API using Parakeet model",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the model
MODEL_PATH = "/Users/itsbohara/ai/models/parakeet-tdt-0.6b-v3"
logger.info(f"Loading Parakeet model from {MODEL_PATH}...")

try:
    # Load Parakeet model using parakeet_mlx
    stt_model = parakeet_mlx.from_pretrained(MODEL_PATH)
    logger.info("Model loaded successfully!")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    stt_model = None


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "parakeet-tdt-0.6b-v3",
                "object": "model",
                "created": 1700000000,
                "owned_by": "local",
            }
        ],
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model_loaded": stt_model is not None,
        "model_path": MODEL_PATH,
    }


@app.post("/v1/audio/transcriptions")
async def transcribe_audio(
    file: UploadFile = File(...),
    model: str = Form("parakeet-tdt-0.6b-v3"),
    language: str = Form(None),
    response_format: str = Form("json"),
    temperature: float = Form(0.0),
    timestamp_granularities: list = Form(None),
):
    """
    Transcribe audio file (OpenAI-compatible endpoint)

    Compatible with OpenAI's /v1/audio/transcriptions endpoint
    """
    if stt_model is None:
        logger.error("Model not loaded!")
        return JSONResponse(
            status_code=500,
            content={"error": {"message": "Model not loaded", "type": "server_error"}},
        )

    try:
        # Read and save uploaded file temporarily
        audio_data = await file.read()

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name

        logger.info(
            f"Transcribing audio file: {file.filename} (size: {len(audio_data)} bytes)"
        )

        # Transcribe using Parakeet
        options = {
            "language": language,
            "temperature": temperature if temperature > 0 else None,
            "word_timestamps": timestamp_granularities == ["word"]
            if timestamp_granularities
            else False,
        }

        # Remove None values
        options = {k: v for k, v in options.items() if v is not None}

        # Get audio duration
        import soundfile as sf

        audio_info = sf.info(temp_path)
        duration = audio_info.duration

        # Transcribe using Parakeet - use direct transcribe method for files
        transcription_result = stt_model.transcribe(temp_path)
        result = transcription_result.text.strip()

        # Clean up temp file
        os.unlink(temp_path)

        # Return OpenAI-compatible response
        response = {
            "text": result,
            "task": "transcribe",
            "language": language or "en",
            "duration": duration,
        }

        logger.info(f"Transcription complete: {len(response['text'])} characters")

        return response

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": {"message": str(e), "type": "transcription_error"}},
        )


@app.websocket("/v1/realtime")
async def realtime_transcription(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming transcription

    Accepts audio chunks and returns partial transcriptions.
    Message format: {"type": "audio", "data": "base64_encoded_audio"}
    Response format: {"type": "transcription", "text": "transcribed text"}
    """
    await websocket.accept()
    logger.info("WebSocket connection established for real-time transcription")

    if stt_model is None:
        await websocket.send_json({"type": "error", "message": "Model not loaded"})
        await websocket.close()
        return

    transcriber = None
    sample_rate = stt_model.preprocessor_config.sample_rate

    try:
        # Initialize streaming transcriber
        transcriber = stt_model.transcribe_stream(
            context_size=(256, 256), keep_original_attention=False
        )
        transcriber_context = transcriber.__enter__()

        await websocket.send_json(
            {
                "type": "ready",
                "sample_rate": sample_rate,
                "message": "Ready to receive audio. Send audio chunks as base64-encoded WAV data.",
            }
        )

        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)

                if data.get("type") == "audio":
                    import base64

                    # Decode base64 audio
                    audio_bytes = base64.b64decode(data["data"])

                    # Convert bytes to numpy array
                    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

                    # Convert to MLX array
                    audio_mx = mx.array(audio_np)

                    # Add audio to transcriber
                    transcriber_context.add_audio(audio_mx)

                    # Get result if available
                    if transcriber_context.result and transcriber_context.result.text:
                        text = transcriber_context.result.text.strip()
                        if text:
                            await websocket.send_json(
                                {"type": "transcription", "text": text, "final": False}
                            )

                elif data.get("type") == "end":
                    # Signal end of audio, get final transcription
                    if transcriber_context.result and transcriber_context.result.text:
                        text = transcriber_context.result.text.strip()
                        await websocket.send_json(
                            {"type": "transcription", "text": text, "final": True}
                        )
                    await websocket.send_json({"type": "done"})
                    break

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error processing audio chunk: {e}")
                await websocket.send_json({"type": "error", "message": str(e)})

    except Exception as e:
        logger.error(f"Real-time transcription error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})
    finally:
        if transcriber:
            try:
                transcriber.__exit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing transcriber: {e}")
        try:
            await websocket.close()
        except:
            pass


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Parakeet STT Server - OpenAI Compatible",
        "endpoints": {
            "health": "/health",
            "models": "/v1/models",
            "transcribe": "/v1/audio/transcriptions",
            "realtime": "ws://localhost:8000/v1/realtime (WebSocket)",
        },
        "usage": "POST /v1/audio/transcriptions with multipart/form-data containing 'file' field",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
