import { useEffect, useRef, useState } from 'react';

interface VoiceButtonProps {
    location: { latitude: number; longitude: number } | null;
    onResourcesReceived?: (resources: any[]) => void;
    onSOSTriggered?: (alert: any) => void;
}

const JITTER_BUFFER_MS = 200;

function VoiceButton({ location, onResourcesReceived, onSOSTriggered }: VoiceButtonProps) {
    const [isActive, setIsActive] = useState(false);
    const [status, setStatus] = useState('Click to speak');
    const [transcript, setTranscript] = useState('');
    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const playbackContextRef = useRef<AudioContext | null>(null);
    const audioQueueRef = useRef<AudioBufferSourceNode[]>([]);
    const nextPlayTimeRef = useRef<number>(0);
    const jitterStartedRef = useRef(false);
    const jitterTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pendingChunksRef = useRef<Float32Array[]>([]);

    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (audioContextRef.current) {
                audioContextRef.current.close();
            }
            if (playbackContextRef.current) {
                playbackContextRef.current.close();
            }
            if (jitterTimerRef.current) {
                clearTimeout(jitterTimerRef.current);
            }
        };
    }, []);

    const startVoice = async () => {
        try {
            const ws = new WebSocket('ws://localhost:8000/voice/stream');
            wsRef.current = ws;

            ws.onopen = async () => {
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

                const audioContext = new AudioContext({ sampleRate: 16000 });
                audioContextRef.current = audioContext;

                const playbackContext = new AudioContext({ sampleRate: 24000 });
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
        }
    };

    const stopVoice = () => {
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
        audioQueueRef.current = [];
        pendingChunksRef.current = [];
        jitterStartedRef.current = false;
        nextPlayTimeRef.current = 0;
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

            if (!jitterStartedRef.current) {
                jitterStartedRef.current = true;
                jitterTimerRef.current = setTimeout(() => {
                    if (!playbackContextRef.current) return;
                    nextPlayTimeRef.current = playbackContextRef.current.currentTime;
                    for (const chunk of pendingChunksRef.current) {
                        scheduleChunk(chunk);
                    }
                    pendingChunksRef.current = [];
                }, JITTER_BUFFER_MS);
            } else if (nextPlayTimeRef.current > 0) {
                scheduleChunk(float32);
            }
        } catch (error) {
            console.error('Audio playback error:', error);
        }
    };

    const toggleVoice = () => {
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
