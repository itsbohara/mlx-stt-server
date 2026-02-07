# MLX STT Server

An OpenAI-compatible Speech-to-Text (STT) API server powered by Apple's MLX framework. This server provides a drop-in replacement for OpenAI's Whisper API, optimized for Apple Silicon.

> **Note:** Currently uses the Parakeet model. Designed to support any MLX-compatible speech model.

## Features

- **OpenAI API Compatible** - Drop-in replacement for `/v1/audio/transcriptions`
- **Real-time Transcription** - WebSocket endpoint for streaming audio
- **MLX Optimized** - Runs efficiently on Apple Silicon (M1/M2/M3/M4)
- **Local Processing** - No data leaves your machine
- **CORS Enabled** - Ready for browser-based applications

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.11+
- Parakeet model files (see Model Setup)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd parakeet-mlx
```

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Model Setup

Download the Parakeet model and place it at the configured path:

```bash
mkdir -p /Users/itsbohara/ai/models
cd /Users/itsbohara/ai/models
# Download parakeet-tdt-0.6b-v3 model files here
```

Or update `MODEL_PATH` in `openai_server.py` to point to your model location.

## Usage

Start the server:

```bash
python openai_server.py
```

The server will start on `http://localhost:8000`.

## API Endpoints

### Health Check
```bash
GET /health
```

### List Models
```bash
GET /v1/models
```

### Transcribe Audio (OpenAI Compatible)
```bash
POST /v1/audio/transcriptions
```

**Parameters:**
- `file` (required) - Audio file (wav, mp3, etc.)
- `model` (optional) - Model ID (default: "parakeet-tdt-0.6b-v3")
- `language` (optional) - Language code (e.g., "en")
- `response_format` (optional) - Response format (default: "json")
- `temperature` (optional) - Sampling temperature
- `timestamp_granularities` (optional) - Enable word timestamps

### Real-time Transcription (WebSocket)
```
ws://localhost:8000/v1/realtime
```

## Example Usage

### Using curl

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -H "Content-Type: multipart/form-data" \
  -F file=@/path/to/audio.wav \
  -F language=en
```

### Using Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000",
    api_key="not-needed"  # Local server doesn't require auth
)

with open("audio.wav", "rb") as f:
    result = client.audio.transcriptions.create(
        model="parakeet-tdt-0.6b-v3",
        file=f,
        language="en"
    )
    print(result.text)
```

### WebSocket Real-time Example

```javascript
const ws = new WebSocket('ws://localhost:8000/v1/realtime');

ws.onopen = () => {
  console.log('Connected for real-time transcription');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcription') {
    console.log('Transcription:', data.text);
  }
};

// Send audio as base64-encoded data
const audioBase64 = /* your base64 audio data */;
ws.send(JSON.stringify({
  type: 'audio',
  data: audioBase64
}));

// Signal end of audio
ws.send(JSON.stringify({ type: 'end' }));
```

## Configuration

Edit `openai_server.py` to customize:

| Setting | Description |
|---------|-------------|
| `MODEL_PATH` | Path to Parakeet model files |
| `host` | Server bind address (default: "0.0.0.0") |
| `port` | Server port (default: 8000) |

## Dependencies

- FastAPI - Web framework
- MLX - Apple's machine learning framework
- parakeet-mlx - Parakeet model implementation
- soundfile - Audio file handling
- uvicorn - ASGI server
- websockets - WebSocket support

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Troubleshooting

**Model not loading?**
- Verify `MODEL_PATH` points to valid Parakeet model files
- Check that all dependencies are installed
- Ensure you're on Apple Silicon (MLX requires it)

**Audio format issues?**
- The server accepts most common formats (wav, mp3, flac)
- Audio is automatically converted to the required format
