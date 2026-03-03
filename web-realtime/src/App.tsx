import { useState, useRef, useCallback, useEffect } from "react";
import "./App.css";

interface TranscriptionMessage {
  type: "transcription" | "ready" | "error" | "done";
  text?: string;
  final?: boolean;
  sample_rate?: number;
  message?: string;
}

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [transcription, setTranscription] = useState("");
  const [partialText, setPartialText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState("ws://localhost:8000/v1/realtime");

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setError(null);
    const ws = new WebSocket(serverUrl);

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data: TranscriptionMessage = JSON.parse(event.data);
      console.log("Received:", data);

      switch (data.type) {
        case "ready":
          console.log("Server ready, sample rate:", data.sample_rate);
          break;
        case "transcription":
          if (data.final) {
            setTranscription((prev) => (prev + " " + (data.text || "")).trim());
            setPartialText("");
          } else {
            setPartialText(data.text || "");
          }
          break;
        case "error":
          setError(data.message || "Unknown error");
          break;
        case "done":
          setIsRecording(false);
          break;
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error");
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    wsRef.current = ws;
  }, [serverUrl]);

  const disconnectWebSocket = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
  }, []);

  const startRecording = async () => {
    try {
      setError(null);
      setTranscription("");
      setPartialText("");

      connectWebSocket();

      // Wait for connection
      await new Promise<void>((resolve, reject) => {
        const checkInterval = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 100);

        setTimeout(() => {
          clearInterval(checkInterval);
          if (wsRef.current?.readyState !== WebSocket.OPEN) {
            reject(new Error("Failed to connect to WebSocket"));
          }
        }, 5000);
      });

      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN)
          return;

        const inputData = e.inputBuffer.getChannelData(0);
        const bytes = new Uint8Array(inputData.buffer);
        const base64 = btoa(String.fromCharCode(...bytes));

        wsRef.current.send(JSON.stringify({ type: "audio", data: base64 }));
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
    } catch (err) {
      console.error("Error starting recording:", err);
      setError(
        err instanceof Error ? err.message : "Failed to start recording",
      );
      disconnectWebSocket();
    }
  };

  const stopRecording = () => {
    // Stop and cleanup audio
    processorRef.current?.disconnect();
    processorRef.current = null;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    audioContextRef.current?.close();
    audioContextRef.current = null;

    // Send end signal
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end" }));
    }

    setIsRecording(false);
  };

  useEffect(() => {
    return () => {
      stopRecording();
      disconnectWebSocket();
    };
  }, []);

  return (
    <div className="app">
      <header className="header">
        <h1>Parakeet Real-time Speech-to-Text</h1>
        <div className="connection-status">
          <span className={`status-dot ${isConnected ? "connected" : ""}`} />
          {isConnected ? "Connected" : "Disconnected"}
        </div>
      </header>

      <main className="main">
        <div className="config-section">
          <label>
            WebSocket URL:
            <input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              disabled={isConnected}
              className="url-input"
            />
          </label>
        </div>

        {error && <div className="error">Error: {error}</div>}

        <div className="controls">
          {!isRecording ? (
            <button
              onClick={startRecording}
              className="btn btn-primary"
              disabled={!serverUrl}
            >
              Start Recording
            </button>
          ) : (
            <button onClick={stopRecording} className="btn btn-danger">
              Stop Recording
            </button>
          )}
        </div>

        <div className="transcription-container">
          <h2>Transcription</h2>
          <div className="transcription-box">
            <p className="final-text">{transcription}</p>
            {partialText && <p className="partial-text">{partialText}</p>}
            {!transcription && !partialText && (
              <p className="placeholder">Transcription will appear here...</p>
            )}
          </div>
        </div>

        <div className="instructions">
          <h3>Instructions:</h3>
          <ol>
            <li>Make sure the Parakeet server is running on port 8000</li>
            <li>Click &quot;Start Recording&quot; to begin</li>
            <li>Speak into your microphone</li>
            <li>Click &quot;Stop Recording&quot; when finished</li>
          </ol>
        </div>
      </main>
    </div>
  );
}

export default App;
