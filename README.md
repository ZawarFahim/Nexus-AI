# Nexus: Your Desktop Voice Companion

Nexus is a lightning-fast, intelligent voice assistant that lives right in your Windows system tray. Simply hold down a hotkey, speak your mind, and Nexus will respond out loud in mere seconds.

Unlike traditional text-based AI, Nexus is built for seamless audio interaction. It can even see your screen and control your web browser—but only when you explicitly ask it to.

```
You     Alt+Space   "What am I looking at right now?"
Nexus               "You've got the Kendrick Lamar halftime show open on YouTube.
                     Looks like you're about halfway through."

You                 "Scroll down a bit."
Nexus               "Done. What are you looking for?"
```

---

## 🌟 Core Features

**Instant Voice Responses.** Hold down `Alt+Space`, speak your request, and let go. Nexus will reply audibly. Thanks to its streaming architecture, it begins speaking its first sentence while still processing the rest, meaning you never have to wait for long answers to generate. For a completely hands-free experience, toggle `Ctrl+Alt+Space` and it will automatically detect when you stop talking.

**Screen Awareness.** Need help with something you're looking at? Ask "What does this error message mean?", "What video is this?", or "Where am I?". Nexus will securely take a temporary screenshot and analyze the context to give you a highly relevant answer.

**Browser Automation.** Nexus can navigate the web for you. Say "Open YouTube", "Search for a recipe", "Scroll down", or "Go back". It directly drives your existing browser—complete with your active tabs and logged-in sessions—rather than launching a detached, isolated browser window.

**Instant Interruptions.** If Nexus is giving a long answer and you already got what you needed, just press the hotkey again to instantly cut it off.

**Resilient API Fallbacks.** Free AI provider tiers often come with strict daily limits. Nexus solves this by allowing you to configure multiple API keys. If one provider hits a rate limit, Nexus seamlessly falls back to the next available service, ensuring you are never left without your assistant.

---

## 🛡️ Privacy & Security First

Nexus is designed to respect your privacy and run locally as much as possible:

- **No Always-Listening Wake Words.** Nexus only listens when you physically hold down the hotkey (or enable hands-free mode). Nothing is ever recorded or transmitted while idle.
- **On-Demand Vision.** Nexus only captures your screen when you specifically ask a question that requires visual context. There is no background recording or screen history. Every single capture is logged transparently.
- **Local Speech Recognition.** Your voice is processed locally on your machine using `faster-whisper`. Only the transcribed text (and authorized screenshots) are sent to the AI service.
- **Secure Credentials.** Your API keys are encrypted using your Windows account credentials and stored safely on your local device. Nexus does not have access to your personal files, clipboard, or emails.

---

## 🚀 Installation & Setup

**Requires Windows 10 or 11** and **Python 3.12**.

1. Clone or download this repository to your machine.
2. Open a terminal (like PowerShell) in the project folder.
3. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: If you have an NVIDIA GPU, you can also install `requirements-gpu.txt` for hardware-accelerated speech recognition.)*
5. Run the one-time setup script to download the voice models (about 200MB):
   ```bash
   python -m scripts.setup
   ```
6. Set up your API key by copying `.env.example` to `.env` and adding your key (e.g., Gemini, Groq, or Cerebras).
7. Start Nexus:
   ```bash
   python -m nexus
   ```

Look for the Nexus orb icon in your system tray! *(Note: Windows 11 often hides new tray icons. Click the `^` arrow next to your clock and drag the Nexus icon onto your taskbar to keep it visible.)*

---

## 🔑 AI Providers (Getting a Free API Key)

Nexus handles the listening and speaking locally, but the heavy "thinking" is delegated to cloud LLMs. You will need a free API key for at least one of the supported providers.

### Recommended: Groq
Groq provides blazing fast inference and supports screen vision.
1. Visit **[console.groq.com/keys](https://console.groq.com/keys)**
2. Sign in (no credit card required).
3. Generate a new API Key and paste it into your `.env` file under `GROQ_API_KEY`. Set `NEXUS_LLM_PROVIDER=groq`.

### Supported Alternatives
Add backup keys to ensure uninterrupted service!
| Service | Highlights | Vision Support |
|---|---|---|
| **[Groq](https://console.groq.com/keys)** | Extremely fast, generous free tier | Yes |
| **[Cerebras](https://cloud.cerebras.ai)** | Massive daily token limits | No (Text Only) |
| **[Google Gemini](https://aistudio.google.com/apikey)** | Excellent vision reasoning | Yes |

*Pro-tip for Cerebras:* Ensure you generate your API key using a **Personal** account. Team accounts often trigger "payment required" errors on the free tier.

---

## 🎮 How to Use Nexus

| Action | Shortcut / Method |
|---|---|
| **Push-to-Talk** | Hold `Alt+Space`, speak, and release |
| **Hands-Free Mode** | Press `Ctrl+Alt+Space` to toggle |
| **Interrupt Nexus** | Press `Alt+Space` while it is speaking |
| **Settings / Quit** | Right-click the system tray icon |

The system tray icon and the optional floating orb provide visual feedback on Nexus's state: 
- **Grey:** Idle
- **Blue:** Listening to you
- **Amber:** Processing / Thinking
- **Green:** Speaking

### Example Prompts
- *"What error message is on my screen right now?"*
- *"Open a new tab and search for Python tutorials."*
- *"Scroll down a bit."*
- *"What song is currently playing on Spotify?"*
- *"Summarize the text in this browser window."*

---

## 🛠️ Advanced Usage & Architecture

### Command Line Flags
You can run Nexus with various flags for debugging or configuration:
```bash
python -m nexus --console             # Show a terminal with verbose logging
python -m nexus --name Zawar          # Change what the assistant calls you
python -m nexus --providers           # List available AI services
```
Your configuration, logs, and encrypted keys are stored safely at `%LOCALAPPDATA%\Nexus`.

### How It Works Under the Hood
```text
Hotkey ──► Microphone ──► Local Whisper ──► AI Service ──► Local Piper ──► Speakers
            (Active        (Transcribes     (Reasoning &    (Streams TTS    (Plays
             Buffer)        Audio)           Tools)          by sentence)    Audio)
```
Nexus is designed around a modular protocol system (`nexus/core/protocols.py`). You can easily swap out the speech recognizer, AI backend, or TTS engine by modifying a single line in `nexus/app.py`. New features and capabilities can be added seamlessly by dropping new tools into the `nexus/tools/` directory.

---

## ⚙️ Technology Stack

- **Speech Recognition:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- **Text-to-Speech:** [Piper](https://github.com/rhasspy/piper)
- **Voice Activity Detection:** [Silero VAD](https://github.com/snakers4/silero-vad)
- **AI Brains:** [Groq](https://groq.com), [Cerebras](https://cerebras.ai), and [Google Gemini](https://ai.google.dev)


