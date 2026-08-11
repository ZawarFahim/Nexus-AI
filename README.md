# Nexus: Your Desktop AI Companion

Nexus is an intelligent, lightning-fast assistant that lives in your Windows system tray. Designed for seamless interaction, Nexus responds out loud in seconds to your voice commands, or silently to your typed text commands. 

Equipped with screen vision and automation tools, Nexus can see what you see and seamlessly drive your desktop and web browser on your behalf.

---

## ✨ Core Capabilities

### 🎙️ Voice & Text Interface
- **Push-to-Talk Voice:** Hold `Alt+Space`, speak your request, and release. Nexus replies audibly with low-latency streaming TTS.
- **Native Text Commands:** Press `Alt+Shift+Space` to instantly open a floating, native desktop window. Type your commands for a silent, text-only conversation that bypasses speech processing.
- **Hands-Free Mode:** Press `Ctrl+Alt+Space` to toggle an always-listening mode that automatically detects when you stop talking.
- **Instant Interruptions:** Press the hotkey again at any time to instantly silence a long response.

### 👁️ Screen Vision
Nexus can "see" your active screen to answer context-specific questions. Ask *"What does this error say?"* or *"Where am I on this map?"*, and Nexus takes a temporary screenshot to analyze and respond intelligently.

### ⚙️ Computer, Browser & File Automation
- **Smart File Assistant:** Nexus can find, open, create, move, and organize your files using natural language. Try saying *"Find my latest PDF"*, *"Create a folder called Research"*, or *"Move these screenshots into Documents"*.
- **Desktop Control:** Nexus can locate applications, open software, type text, and manipulate windows. Try saying: *"Open Spotify and play Blinding Lights"* or *"Open VS Code"*. High-risk actions will prompt for your explicit approval first.
- **Browser Automation:** Say *"Open YouTube"* or *"Search for a recipe"*. Nexus directly commands your existing, authenticated browser sessions rather than launching isolated environments.

### 🛡️ Privacy & Resilience
- **Zero Idle Recording:** Nexus only listens when you explicitly engage a hotkey.
- **On-Device Speech:** Voice recognition is handled entirely on your local hardware using `faster-whisper`.
- **API Fallbacks:** Configure multiple LLM providers (Groq, Cerebras, Gemini). If one hits a rate limit, Nexus seamlessly falls back to the next available API key.

---

## 🚀 Installation

**Requirements:** Windows 10/11, Python 3.12+

```bash
# 1. Clone the repository and navigate to the folder
git clone https://github.com/your-username/nexus.git
cd nexus

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download local voice models (approx 200MB)
python -m scripts.setup
```

### Configuration
Nexus handles listening and speaking locally, but delegates "thinking" to cloud LLMs. 
1. Copy `.env.example` to `.env`.
2. Generate an API Key (e.g., from [Groq](https://console.groq.com/keys) or [Gemini](https://aistudio.google.com/apikey)).
3. Paste the key into your `.env` file and set your preferred provider.

### Running Nexus
```bash
python -m nexus
```
Nexus will launch into your system tray! *(Note: Windows 11 may hide new icons. Check the `^` arrow next to your clock).*

---

## 🎮 Cheat Sheet

| Action | Shortcut |
|---|---|
| **Voice Command** | Hold `Alt+Space` |
| **Push-to-Talk** | Hold `Alt+Space`, speak, and release |
| **Text Command** | Press `Alt+Shift+Space` to open the text interface |
| **Hands-Free Mode** | Press `Ctrl+Alt+Space` to toggle |
| **Interrupt Nexus** | Press `Alt+Space` while it is speaking |
| **Settings / Quit** | Right-click the system tray icon |

### Example Prompts
- *"What error message is on my screen right now?"*
- *"Find my latest PDF."*
- *"Create a folder called Research in Documents."*
- *"Move these screenshots into Nexus Screenshots."*
- *"Find the largest files in Downloads."*
- *"Open Spotify and play some music."*
- *"Open a new tab and search for Python tutorials."*
- *"Minimize Chrome and focus Notepad."*

---

## ⚙️ Technology Stack

- **Speech Recognition:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (Local)
- **Text-to-Speech:** [Piper](https://github.com/rhasspy/piper) (Local)
- **Voice Activity Detection:** [Silero VAD](https://github.com/snakers4/silero-vad) (Local)
- **Native UI:** `tkinter` & `pystray`
- **Automation:** `pywinauto` (Desktop) & `playwright` (Browser)
- **AI Backend:** Modulable protocol supporting Groq, Cerebras, and Google Gemini.
