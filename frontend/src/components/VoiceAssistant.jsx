import React, { useState, useRef, useEffect, useCallback } from "react";
import { Mic, MicOff, X, Volume2, Loader2, MessageCircle } from "lucide-react";

const CHAT_ENDPOINT = "http://localhost:8000/chat";
const AI_CHAT_ENDPOINT = "http://localhost:8000/ai/chat";
const TRANSCRIBE_ENDPOINT = "http://localhost:8000/ai/transcribe";
const SPEAK_ENDPOINT = "http://localhost:8000/ai/speak";

const FOREST      = "#2C5F2D";
const FOREST_DARK = "#1F4620";
const MOSS        = "#97BC62";
const GOLD        = "#E8A33D";
const CREAM       = "#F7F8F5";
const INK         = "#1A2E1B";
const MUTED       = "#5C6F5E";

// Web Speech API language tags — Indian locales for best recognition/voice match
const SPEECH_LANG = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

const VOICE_TEXT = {
  en: {
    title: "Voice Assistant", tapToSpeak: "Tap the mic and ask your question",
    listening: "Listening…", thinking: "Thinking…", speaking: "Speaking…",
    tapToStop: "Tap to stop", unsupported: "Voice input isn't supported in this browser. Try Chrome on Android/desktop.",
    micDenied: "Microphone access was denied. Please allow microphone permission.",
    noServer: "Cannot reach the server. Please make sure the backend is running.",
    switchToText: "Switch to text chat", listenAgain: "Tap mic to ask another question",
  },
  hi: {
    title: "वॉइस सहायक", tapToSpeak: "माइक पर टैप करें और अपना प्रश्न पूछें",
    listening: "सुन रहा हूं…", thinking: "सोच रहा हूं…", speaking: "बोल रहा हूं…",
    tapToStop: "रोकने के लिए टैप करें", unsupported: "इस ब्राउज़र में वॉइस इनपुट समर्थित नहीं है। Chrome आज़माएं।",
    micDenied: "माइक्रोफ़ोन एक्सेस अस्वीकार कर दिया गया। कृपया अनुमति दें।",
    noServer: "सर्वर से कनेक्ट नहीं हो सका। बैकएंड चालू करें।",
    switchToText: "टेक्स्ट चैट पर जाएं", listenAgain: "अगला प्रश्न पूछने के लिए माइक पर टैप करें",
  },
  mr: {
    title: "व्हॉइस सहाय्यक", tapToSpeak: "माइकवर टॅप करा आणि तुमचा प्रश्न विचारा",
    listening: "ऐकत आहे…", thinking: "विचार करतो आहे…", speaking: "बोलत आहे…",
    tapToStop: "थांबवण्यासाठी टॅप करा", unsupported: "या ब्राउझरमध्ये व्हॉइस इनपुट समर्थित नाही. Chrome वापरून पहा.",
    micDenied: "मायक्रोफोन परवानगी नाकारली गेली. कृपया परवानगी द्या.",
    noServer: "सर्व्हरशी कनेक्ट होता आले नाही. बॅकएंड सुरू करा.",
    switchToText: "टेक्स्ट चॅटवर जा", listenAgain: "पुढचा प्रश्न विचारण्यासाठी माइकवर टॅप करा",
  },
};

// Picks the closest-matching installed system voice for a given language
function pickVoice(langCode) {
  const voices = window.speechSynthesis?.getVoices() || [];
  if (!voices.length) return null;
  const exact = voices.find((v) => v.lang?.toLowerCase() === langCode.toLowerCase());
  if (exact) return exact;
  const prefix = langCode.split("-")[0];
  return voices.find((v) => v.lang?.toLowerCase().startsWith(prefix)) || null;
}

/**
 * Full-screen, call-style voice assistant.
 * Hands-free loop: listen -> send to /chat -> speak reply -> listen again.
 *
 * Props:
 *  - lang, setLang: shared language state with the rest of the app
 *  - profile: farmer profile object, forwarded to /chat for personalization
 *  - useAI: boolean to toggle sending queries to /ai/chat vs /chat
 *  - onClose: called to dismiss the overlay
 *  - onExchange: optional callback(userText, chatResponse) so the parent
 *                chat screen can log the voice turn into its own message list
 */
export default function VoiceAssistant({ lang, setLang, profile = {}, useAI = false, onClose, onExchange }) {
  const t = VOICE_TEXT[lang] || VOICE_TEXT.en;

  // "idle" | "listening" | "thinking" | "speaking" | "error"
  const [status, setStatus]   = useState("idle");
  const [liveTranscript, setLiveTranscript] = useState("");
  const [lastUserText, setLastUserText]     = useState("");
  const [lastReplyText, setLastReplyText]   = useState("");
  const [errorMsg, setErrorMsg]             = useState("");
  const [autoListen, setAutoListen]         = useState(true); // hands-free loop toggle

  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioRef = useRef(null);
  const statusRef = useRef(status);
  statusRef.current = status;

  const SpeechRecognitionCtor =
    typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const nativeSttSupported = !!SpeechRecognitionCtor;
  const nativeTtsSupported = typeof window !== "undefined" && !!window.speechSynthesis;

  // Warm up voice list (some browsers load it asynchronously)
  useEffect(() => {
    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    }
  }, []);

  const stopEverything = useCallback(() => {
    try { recognitionRef.current?.stop(); } catch { /* noop */ }
    try { 
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop(); 
      }
    } catch { /* noop */ }
    if (nativeTtsSupported) window.speechSynthesis?.cancel();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setStatus("idle");
  }, [nativeTtsSupported]);

  useEffect(() => stopEverything, [stopEverything]); // cleanup on unmount

  const speak = useCallback(async (text) => {
    if (!text) {
      setStatus("idle");
      return;
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (nativeTtsSupported) window.speechSynthesis.cancel();

    const targetLang = SPEECH_LANG[lang] || "en-IN";
    const voice = pickVoice(targetLang);

    // Use backend TTS if native is unsupported, OR if we couldn't find a matching native voice
    // OR if language is Marathi (browser TTS is unreliable for Marathi).
    if (!nativeTtsSupported || !voice || lang === "mr") {
      setStatus("speaking");
      try {
        const res = await fetch(SPEAK_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, language: lang })
        });
        if (!res.ok) throw new Error("TTS failed");
        const blob = await res.blob();
        const audio = new Audio(URL.createObjectURL(blob));
        audio.onended = () => {
          setStatus("idle");
          if (autoListen) setTimeout(() => startListening(), 400);
        };
        audio.play();
        audioRef.current = audio;
      } catch (err) {
        setErrorMsg(t.noServer);
        setStatus("error");
      }
      return;
    }
    
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = targetLang;
    utter.voice = voice;
    utter.rate = 0.98;
    utter.pitch = 1.0;

    utter.onstart = () => setStatus("speaking");
    utter.onend = () => {
      setStatus("idle");
      // Hands-free loop: automatically start listening again for the follow-up question
      if (autoListen) setTimeout(() => startListening(), 400);
    };
    utter.onerror = () => setStatus("idle");

    window.speechSynthesis.speak(utter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, autoListen]);

  const sendToBackend = useCallback(async (text) => {
    setStatus("thinking");
    try {
      let data;
      if (useAI) {
        const aiRes = await fetch(AI_CHAT_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, language: lang, profile }),
        });
        if (aiRes.ok) {
          data = await aiRes.json();
          // Map AI response to ChatResponse shape for onExchange
          data.found = true;
          data.message = data.answer;
          data.speech_text = data.speech_text || data.answer;
        }
      }
      
      if (!data) {
        const res = await fetch(CHAT_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: text, lang, profile }),
        });
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        data = await res.json();
      }

      const speechText = data.speech_text || data.message || "";
      setLastReplyText(speechText);
      onExchange && onExchange(text, data);
      speak(speechText);
    } catch {
      setErrorMsg(t.noServer);
      setStatus("error");
      speak(t.noServer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, profile, speak, onExchange]);

  const startListening = useCallback(async () => {
    if (nativeTtsSupported) window.speechSynthesis?.cancel();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setErrorMsg("");
    setLiveTranscript("");

    // Fallback to backend STT using MediaRecorder if native STT is unsupported
    if (!nativeSttSupported) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        const chunks = [];
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach(t => t.stop());
          const blob = new Blob(chunks, { type: "audio/webm" });
          const fd = new FormData();
          fd.append("file", blob, "recording.webm");
          setStatus("thinking");
          try {
            const res = await fetch(TRANSCRIBE_ENDPOINT, { method: "POST", body: fd });
            if (!res.ok) throw new Error();
            const json = await res.json();
            setLastUserText(json.text);
            sendToBackend(json.text);
          } catch (err) {
            setErrorMsg(t.noServer);
            setStatus("error");
          }
        };
        mediaRecorderRef.current = mediaRecorder;
        mediaRecorder.start();
        setStatus("listening");
      } catch (err) {
        setErrorMsg(t.micDenied);
        setStatus("error");
      }
      return;
    }

    // Native STT
    const recognition = new SpeechRecognitionCtor();
    recognition.lang = SPEECH_LANG[lang] || "en-IN";
    recognition.continuous = false;   // one utterance per turn — cleaner for Q&A
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setStatus("listening");

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const chunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += chunk;
        else interim += chunk;
      }
      setLiveTranscript(interim || final);
      if (final.trim()) {
        setLastUserText(final.trim());
        recognition.stop();
        sendToBackend(final.trim());
      }
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setErrorMsg(t.micDenied);
      }
      setStatus((s) => (s === "listening" ? "idle" : s));
    };

    recognition.onend = () => {
      // If it ended without producing a final result, just go back to idle
      setStatus((s) => (s === "listening" ? "idle" : s));
    };

    recognitionRef.current = recognition;
    recognition.start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, sendToBackend, nativeSttSupported, nativeTtsSupported]);

  const handleMicTap = () => {
    if (status === "listening") {
      if (!nativeSttSupported) {
        mediaRecorderRef.current?.stop();
      } else {
        recognitionRef.current?.stop();
      }
      // Note: we don't set status="idle" here for backend STT because mediaRecorder.onstop will transition to "thinking"
      if (nativeSttSupported) setStatus("idle");
    } else if (status === "speaking") {
      if (nativeTtsSupported) window.speechSynthesis.cancel();
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
      setStatus("idle");
    } else {
      startListening();
    }
  };

  const orbState = status; // idle | listening | thinking | speaking | error
  const orbColor =
    orbState === "listening" ? GOLD :
    orbState === "thinking"  ? MOSS :
    orbState === "speaking"  ? FOREST :
    orbState === "error"     ? "#C0524A" : FOREST_DARK;

  const statusLabel =
    orbState === "listening" ? t.listening :
    orbState === "thinking"  ? t.thinking :
    orbState === "speaking"  ? t.speaking :
    orbState === "error"     ? errorMsg : t.tapToSpeak;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      style={{ backgroundColor: FOREST_DARK, fontFamily: "Georgia, 'Noto Serif Devanagari', serif" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2 text-white">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: MOSS }} />
          <span className="text-sm font-semibold opacity-90">{t.title}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-full overflow-hidden border" style={{ borderColor: MOSS }}>
            {["en", "hi", "mr"].map((code) => (
              <button
                key={code}
                onClick={() => { stopEverything(); setLang(code); }}
                className="px-2.5 py-1 text-xs font-semibold"
                style={{ backgroundColor: lang === code ? GOLD : "transparent", color: lang === code ? FOREST_DARK : "#fff" }}
              >
                {code === "en" ? "EN" : code === "hi" ? "हिं" : "मर"}
              </button>
            ))}
          </div>
          <button
            onClick={() => { stopEverything(); onClose && onClose(); }}
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ backgroundColor: "rgba(255,255,255,0.1)" }}
            aria-label={t.switchToText}
          >
            <X size={16} color="#fff" />
          </button>
        </div>
      </div>

      {/* Center: transcript + orb */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 gap-8">
        {/* Conversation snippet */}
        <div className="w-full max-w-md space-y-3 text-center min-h-[80px]">
          {lastUserText && (
            <p className="text-sm px-3" style={{ color: MOSS }}>
              “{lastUserText}”
            </p>
          )}
          {(liveTranscript && status === "listening") && (
            <p className="text-base font-semibold px-3" style={{ color: "#fff" }}>
              {liveTranscript}
            </p>
          )}
          {lastReplyText && status !== "listening" && (
            <p className="text-sm px-3 leading-relaxed" style={{ color: "#EDF1E8" }}>
              {lastReplyText}
            </p>
          )}
        </div>

        {/* Animated orb / mic button */}
        <button
          onClick={handleMicTap}
          disabled={status === "thinking"}
          className="relative w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300"
          style={{
            backgroundColor: orbColor,
            boxShadow: orbState === "listening" ? `0 0 0 14px rgba(232,163,61,0.18)` :
                       orbState === "speaking"  ? `0 0 0 14px rgba(44,95,45,0.25)` :
                       `0 0 0 6px rgba(255,255,255,0.05)`,
            cursor: status === "thinking" ? "not-allowed" : "pointer",
          }}
        >
          {orbState === "thinking" ? (
            <Loader2 size={34} color="#fff" className="animate-spin" />
          ) : orbState === "speaking" ? (
            <Volume2 size={34} color="#fff" />
          ) : orbState === "error" ? (
            <MicOff size={34} color="#fff" />
          ) : (
            <Mic size={34} color="#fff" />
          )}
        </button>

        <p className="text-sm font-medium" style={{ color: orbState === "error" ? "#E8998F" : "#C9D6C6" }}>
          {statusLabel}
        </p>

        {!nativeSttSupported && !navigator.mediaDevices && (
          <p className="text-xs text-center max-w-xs" style={{ color: "#E8998F" }}>
            {t.unsupported}
          </p>
        )}
      </div>

      {/* Footer controls */}
      <div className="px-6 pb-8 flex flex-col items-center gap-3">
        <label className="flex items-center gap-2 text-xs" style={{ color: "#C9D6C6" }}>
          <input
            type="checkbox"
            checked={autoListen}
            onChange={(e) => setAutoListen(e.target.checked)}
          />
          {t.listenAgain}
        </label>
        <button
          onClick={() => { stopEverything(); onClose && onClose(); }}
          className="flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-full"
          style={{ backgroundColor: "rgba(255,255,255,0.1)", color: "#fff" }}
        >
          <MessageCircle size={14} />
          {t.switchToText}
        </button>
      </div>
    </div>
  );
}
