import React, { useState, useEffect, useRef } from "react";
import "./sms-demo.css";

export default function SmsDemoUI() {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [language, setLanguage] = useState(null);
  const messagesEndRef = useRef(null);

  const DEMO_PHONE = "+91-DEMO-USER";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await fetch(`http://localhost:8000/sms/history/${encodeURIComponent(DEMO_PHONE)}`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const loadedMessages = data.map(msg => ({
              id: msg.id,
              text: msg.message_text,
              isSender: msg.direction === 'incoming',
              time: new Date(msg.timestamp + 'Z').toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }));
            setMessages(loadedMessages);
          }
        }
      } catch (error) {
        console.error("Failed to load SMS history:", error);
      }
    };
    
    fetchHistory();
  }, []);

  const addMessage = (text, isSender) => {
    setMessages(prev => [...prev, {
      id: Date.now() + Math.random(),
      text,
      isSender,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
  };

  const sendMessage = async () => {
    if (!inputText.trim()) return;
    
    const userMsg = inputText.trim();
    addMessage(userMsg, true);
    setInputText("");

    try {
      const response = await fetch("http://localhost:8000/sms/simulator", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ from: DEMO_PHONE, message: userMsg })
      });
      
      const data = await response.json();
      if (data.success) {
        addMessage(data.message, false);
        if (data.language) {
          setLanguage(data.language);
        }
      } else {
        addMessage("Failed to get response from simulator.", false);
      }
    } catch (error) {
      addMessage("Network error connecting to simulator.", false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const langLabels = {
    en: "Language: English",
    hi: "Language: हिंदी",
    mr: "Language: मराठी"
  };

  const badgeText = language && langLabels[language] ? langLabels[language] : "SMS Simulator — Demo";

  return (
    <div className="sms-demo-container">
      <div className="sms-phone-mockup">
        <div className="sms-header">
          <div className="sms-header-info">
            <h2>Krushi Mitra</h2>
            <p>SMS Assistant</p>
          </div>
          <div className="sms-header-badge">{badgeText}</div>
        </div>
        
        <div className="sms-messages-area">
          {messages.length === 0 ? (
            <div className="sms-empty-state">
              <p>Send <strong>START</strong> to begin the simulator.</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`sms-message-wrapper ${msg.isSender ? 'sent' : 'received'}`}>
                <div className="sms-bubble">
                  {msg.text.split('\n').map((line, i) => (
                    <span key={i}>
                      {line}
                      <br />
                    </span>
                  ))}
                  <div className="sms-time">{msg.time}</div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <div className="sms-input-area">
          <input 
            type="text" 
            placeholder="Type a message..." 
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button onClick={sendMessage} disabled={!inputText.trim()} aria-label="Send message">
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}
