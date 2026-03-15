import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

interface ChatFrameProps {
  location: { latitude: number; longitude: number } | null;
  onResourceRequest?: () => void;
  onResourcesReceived?: (resources: any[]) => void;
  onSOSTriggered?: (alert: any) => void;
  onToolCall?: (toolCalls: any[]) => void;
  onToggleMap?: () => void;
  mapVisible?: boolean;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

function ChatFrame({ onResourcesReceived, onSOSTriggered, onToolCall, onToggleMap, mapVisible }: ChatFrameProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });

      const data = await response.json();
      console.log('API Response:', data);

      if (data.success) {
        let responseText = data.response || 'No response';

        // Backend should return a plain string, but handle edge cases
        if (typeof responseText !== 'string') {
          console.warn('Unexpected response format:', responseText);
          responseText = JSON.stringify(responseText, null, 2);
        }

        setMessages(prev => [...prev, {
          role: 'assistant',
          content: responseText
        }]);

        // Handle tool calls from the agent
        if (data.tool_calls && data.tool_calls.length > 0) {
          console.log('Tool calls detected:', data.tool_calls);
          onToolCall?.(data.tool_calls);
        }

        // Handle resources returned by the agent
        if (data.resources && data.resources.length > 0) {
          console.log('Resources received from agent:', data.resources);
          onResourcesReceived?.(data.resources);
        }

        // Handle SOS alert triggered by the agent
        if (data.sos_alert) {
          console.log('SOS alert triggered:', data.sos_alert);
          onSOSTriggered?.(data.sos_alert);
        }
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Error: ${data.error || 'Unknown error'}`
        }]);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Network error. Please try again.'
      }]);
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-section">
      <div className="chat-header">
        <h2>Chat</h2>
        {!mapVisible && onToggleMap && (
          <button className="map-toggle-btn" onClick={onToggleMap} title="Show Map">
            🗺️
          </button>
        )}
      </div>
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            {msg.role === 'assistant' ? (
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            ) : (
              <div>{msg.content}</div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-message assistant">Thinking...</div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-row">
        <input
          type="text"
          className="chat-input"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
        />
        <button
          className="chat-send"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatFrame;
