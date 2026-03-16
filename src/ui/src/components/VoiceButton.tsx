import { useEffect, useRef, useState } from 'react';
import { WS_BASE } from '../config';

interface VoiceButtonProps {
    location: { latitude: number; longitude: number } | null;
    onResourcesReceived?: (resources: any[]) => void;
    onSOSTriggered?: (alert: any) => void;
}

const JITTER_BUFFER_MS = 200;
const TOUCH_DEBOUNCE_MS = 400;

// Module-level session singleton to survive React StrictMode remounts
interface ActiveSession {
    ws: WebSocket | null;
    audioContext: AudioContext | null;
    playbackContext: AudioContext | null;
    mediaStream: MediaStream | null;
    jitterTimer: ReturnType<typeof setTimeout> | null;
    pendingChunks: Float32Array[];
    nextPlayTime: number;
    jitterStarted: boolean;
}

let activeSession: ActiveSession | null = null;
let lastToggleTimestamp = 0;

function VoiceButton({ location, onResourcesReceived, onSOSTriggered }: VoiceButtonProps) {
    const [isActive, setIsActive] = useState(false);
    const [status, setStatus] = useState('Click to speak');
    const [transcript, setTranscript] = useState('');

    // Local refs that sync with module-level session
    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const playbackContextRef = useRef<AudioContext | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    const jitterTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pendingChunksRef = useRef<Float32Array[]>([]);
    const nextPlayTimeRef = useRef<number>(0);
    const jitterStartedRef = useRef(false);

    // Sync local refs from existing session on mount (handles StrictMode remount)
    useEffect(() => {
        if (activeSession) {
            wsRef.current = activeSession.ws;
            audioContextRef.current = activeSession.audioContext;
            playbackContextRef.current = activeSession.playbackContext;
            mediaStreamRef.current = activeSession.mediaStream;
            jitterTimerRef.current = activeSession.jitterTimer;
            pendingChunksRef.current = activeSession.pendingChunks;
            nextPlayTimeRef.current = activeSession.nextPlayTime;
            jitterStartedRef.current = activeSession.jitterStarted;
            if (activeSession.ws && activeSession.ws.readyState === WebSocket.OPEN) {
                setIsActive(true);
                setStatus('Listening...');
            }
        }

        return () => {
            // Only cleanup if this is the last unmount (not StrictMode first cycle)
            // The actual cleanup happens in stopVoice when user stops
        };
    }, []);

    const startVoice = async () => {
        // Prevent duplicate sessions
        if (activeSession) {
            return;
        }

        try {
            const ws = new WebSocket(`${WS_BASE}/voice/stream`);
            wsRef.current = ws;

            ws.onopen = async () => {
                // Guard again — StrictMode remount could race here
                if (activeSession) {
                    ws.close();
                    return;
                }

                // Initialize session singleton only after WS is confirmed open
                activeSession = {
                    ws,
                    audioContext: null,
                    playbackContext: null,
                    mediaStream: null,
                    jitterTimer: null,
                    pendingChunks: [],
                    nextPlayTime: 0,
                    jitterStarted: false,
                };

                setIsActive(true);
                setStatus('Listening...');

                if (location) {
                    ws.send(JSON.stringify({
                        type: 'session.location',
                        latitude: location.latitude,
                        longitude: location.longitude
                    }));
                }

                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: 16000,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true
                    }
                });

                activeSession.mediaStream = stream;
                mediaStreamRef.current = stream;

                const audioContext = new AudioContext({ sampleRate: 16000 });
                activeSession.audioContext = audioContext;
                audioContextRef.current = audioContext;

                const playbackContext = new AudioContext({ sampleRate: 24000 });
                activeSession.playbackContext = playbackContext;
                activeSession.nextPlayTime = 0;
                playbackContextRef.current = playbackContext;
                nextPlayTimeRef.current = 0;

                const source = audioContext.createMediaStreamSource(stream);
                const processor = audioContext.createScriptProcessor(4096, 1, 1);

                processor.onaudioprocess = (e) => {
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcm16 = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        pcm16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                    }
                    const bytes = new Uint8Array(pcm16.buffer);
                    let binary = '';
                    for (let i = 0; i < bytes.length; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    const base64 = btoa(binary);
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({
                            type: 'input_audio_buffer.append',
                            audio: base64
                        }));
                    }
                };

                source.connect(processor);
                processor.connect(audioContext.destination);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                if (data.type === 'conversation.item.input_audio_transcription.completed') {
                    setTranscript(prev => prev + '\nYou: ' + data.transcript);
                } else if (data.type === 'response.output_audio_transcript.done') {
                    setTranscript(prev => prev + '\nAgent: ' + data.transcript);
                } else if (data.type === 'response.output_audio.delta') {
                    playAudio(data.delta);
                } else if (data.type === 'tool.resources') {
                    onResourcesReceived?.(data.resources);
                } else if (data.type === 'tool.sos_alert') {
                    onSOSTriggered?.(data.sos_alert);
                }
            };

            ws.onerror = () => {
                setStatus('Connection error');
                stopVoice();
            };

            ws.onclose = () => {
                stopVoice();
            };

        } catch (error) {
            console.error('Voice error:', error);
            setStatus('Microphone access denied');
            setIsActive(false);
            activeSession = null;
        }
    };

    const stopVoice = () => {
        // Stop all MediaStream tracks first to release microphone
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(track => track.stop());
            mediaStreamRef.current = null;
        }
        if (activeSession?.mediaStream) {
            activeSession.mediaStream.getTracks().forEach(track => track.stop());
        }

        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
        if (playbackContextRef.current) {
            playbackContextRef.current.close();
            playbackContextRef.current = null;
        }
        if (jitterTimerRef.current) {
            clearTimeout(jitterTimerRef.current);
            jitterTimerRef.current = null;
        }

        pendingChunksRef.current = [];
        jitterStartedRef.current = false;
        nextPlayTimeRef.current = 0;

        // Clear module-level session
        activeSession = null;

        setIsActive(false);
        setStatus('Click to speak');
    };

    const scheduleChunk = (float32: Float32Array) => {
        if (!playbackContextRef.current) return;

        const audioBuffer = playbackContextRef.current.createBuffer(1, float32.length, 24000);
        audioBuffer.getChannelData(0).set(float32);

        const source = playbackContextRef.current.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(playbackContextRef.current.destination);

        const currentTime = playbackContextRef.current.currentTime;
        const startTime = Math.max(currentTime, nextPlayTimeRef.current);
        source.start(startTime);
        nextPlayTimeRef.current = startTime + audioBuffer.duration;

        if (activeSession) {
            activeSession.nextPlayTime = nextPlayTimeRef.current;
        }
    };

    const playAudio = (base64Audio: string) => {
        try {
            if (!playbackContextRef.current) return;

            const binaryString = atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(pcm16.length);
            for (let i = 0; i < pcm16.length; i++) {
                float32[i] = pcm16[i] / 32768.0;
            }

            pendingChunksRef.current.push(float32);
            if (activeSession) {
                activeSession.pendingChunks = pendingChunksRef.current;
            }

            if (!jitterStartedRef.current) {
                jitterStartedRef.current = true;
                if (activeSession) {
                    activeSession.jitterStarted = true;
                }
                jitterTimerRef.current = setTimeout(() => {
                    if (!playbackContextRef.current) return;
                    nextPlayTimeRef.current = playbackContextRef.current.currentTime;
                    if (activeSession) {
                        activeSession.nextPlayTime = nextPlayTimeRef.current;
                    }
                    for (const chunk of pendingChunksRef.current) {
                        scheduleChunk(chunk);
                    }
                    pendingChunksRef.current = [];
                    if (activeSession) {
                        activeSession.pendingChunks = [];
                    }
                }, JITTER_BUFFER_MS);
                if (activeSession) {
                    activeSession.jitterTimer = jitterTimerRef.current;
                }
            } else if (nextPlayTimeRef.current > 0) {
                scheduleChunk(float32);
            }
        } catch (error) {
            console.error('Audio playback error:', error);
        }
    };

    const toggleVoice = () => {
        // iOS Safari fires touchend then synthetic click on single tap
        // Debounce to ignore the second event within 400ms
        const now = Date.now();
        if (now - lastToggleTimestamp < TOUCH_DEBOUNCE_MS) {
            return;
        }
        lastToggleTimestamp = now;

        if (isActive) {
            stopVoice();
        } else {
            startVoice();
        }
    };

    return (
        <div className="panel-section">
            <h2>Voice Agent</h2>
            <button
                className={`mic-button ${isActive ? 'active' : ''}`}
                onClick={toggleVoice}
            >
                🎤
            </button>
            <div className="voice-status">{status}</div>
            {transcript && (
                <div className="voice-transcript">{transcript}</div>
            )}
        </div>
    );
}

export default VoiceButton;
