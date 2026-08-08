# Nexus

A voice companion that sits in your Windows tray. Hold a key, talk, and it
answers out loud — in about two seconds.

It can also see your screen and drive your browser, but only when you ask.

```
You     Alt+Space   "what am I looking at?"
Nexus               "You've got the Kendrick Lamar halftime show on YouTube.
                     Looks like you're partway through it."

You                 "scroll down twice"
Nexus               "Done. What are you after?"
```

---

## What it can do

**Talk.** Hold `Alt+Space`, speak, let go. Nexus replies out loud, and starts
speaking its first sentence while it is still writing the rest — so the wait
does not grow with the length of the answer. Press `Ctrl+Alt+Space` for
hands-free mode, where it listens for you to stop talking instead.

**See your screen.** Ask "what does this error say", "what's playing", "where
am I", or anything that would only make sense to someone in the room with you,
and Nexus takes a screenshot and answers from it.

**Use your browser.** "Open YouTube." "Search for piper voices." "Scroll
down." "Go back." It drives the browser you already have open, with your tabs
and your logins — not a separate automated one.

**Interrupt it.** Press the key while it is talking and it stops.

**Keep working when it runs out.** Free AI allowances are a cliff: they last an
afternoon and then everything fails until tomorrow. Nexus can hold keys for
several services and moves to the next when one is spent.

---

## What it will not do

Nexus hears you **only while you hold the key**. There is no wake word, and
nothing is transmitted while you are not talking to it.

It looks at your screen **only when answering a question that needs it**. There
is no timer, no background capture, and no history of past screens. Every
capture is written to the log, so there is a record of exactly when it looked.

It does not read your files, your clipboard, or your email. It does not
remember conversations after you close it.

Speech recognition runs **on your computer** — your voice never leaves it. Only
the transcribed text, and screenshots when you ask for them, go to the AI
service.

Your API key is encrypted with your Windows account and stored on your machine.

---

## Install

**Requires Windows 10 or 11.** Nothing else — no Python, no setup.

1. Download `Nexus-windows.zip` from the
   [latest release](https://github.com/abdullah61305/Nexus/releases/latest).
2. Unzip it somewhere you will keep it — your Documents folder is fine.
3. Run **`Nexus.exe`**.

On first run Nexus asks for your name, asks for a free API key, and downloads
about 200 MB of speech and voice files. That happens once.

Then look for the icon in your system tray. **Windows 11 hides new tray icons** —
click the `^` arrow next to the clock, and drag Nexus's icon onto the bar to
keep it visible.

> **Windows may warn you.** Nexus is not code-signed; a certificate costs a few
> hundred dollars a year. Click **More info → Run anyway**. If you would rather
> not trust a stranger's binary, the whole project is here and you can build it
> yourself in about five minutes.

---

## Getting a free API key

Nexus listens and speaks on your machine, but the thinking happens at an AI
service. You need a key for at least one. It is free and takes about a minute.

Nexus asks on first run and walks you through it. To do it in advance:

### Groq — the one to start with

1. Go to **[console.groq.com/keys](https://console.groq.com/keys)**
2. Sign in with Google or GitHub. **No card required.**
3. Click **Create API Key**, give it any name, and copy it.
4. Paste it into Nexus when asked.

That is enough. Roughly **100,000 tokens a day** — a few hundred exchanges,
which is plenty unless you are hammering it.

### Adding more, for when one runs out

Every service has its own separate free allowance, so adding a second one
mostly means never thinking about limits again. Nexus tries them in order and
moves on when one is spent.

| Service | Free allowance | Sees your screen? |
|---|---|---|
| **[Groq](https://console.groq.com/keys)** | ~100k tokens/day, fastest | Yes |
| **[Cerebras](https://cloud.cerebras.ai)** | ~1M tokens/day | No |
| **[Google Gemini](https://aistudio.google.com/apikey)** | Small — tens of requests/day | Yes |

Right-click the tray icon → **Add more free usage**, pick one, paste the key.
Or from a terminal:

```
Nexus.exe --providers                 # see them all, and where to sign up
Nexus.exe --add-provider cerebras
```

> **Cerebras:** create the key on your **Personal** account. A key made under a
> Team organisation validates fine and then refuses every request with "payment
> required" — confusing enough that Nexus explains it for you if it happens.

---

## Using it

| | |
|---|---|
| `Alt+Space` | Hold to talk, release to send |
| `Ctrl+Alt+Space` | Hands-free mode on and off |
| `Alt+Space` while it talks | Interrupt |
| Tray icon | State, hands-free toggle, settings, quit |

The tray icon and the on-screen orb both follow what Nexus is doing: grey idle,
blue listening, amber thinking, green speaking.

### Things to try

- "What am I looking at?"
- "What does this error mean?"
- "Open YouTube" · "Search for how to make sourdough"
- "Scroll down three times" · "Go back" · "New tab"
- "What's playing?"
- Or just talk to it.

### Command line

```
Nexus.exe                       Start normally
Nexus.exe --console             Show a terminal with verbose logging
Nexus.exe --name Mickey         Change what it calls you
Nexus.exe --set-key             Replace the stored API key
Nexus.exe --providers           List AI services and which are set up
Nexus.exe --add-provider NAME   Add another service
Nexus.exe --forget              Delete the stored name and keys
```

Settings, keys and logs live in `%LOCALAPPDATA%\Nexus`.

---

## If something goes wrong

**Nothing happens when I press Alt+Space.** Check the tray icon is there and
grey. Applications running as administrator capture keystrokes before Nexus
sees them.

**It cannot hear me.** Check the input device in Windows sound settings. Nexus
logs which microphone it opened, in `%LOCALAPPDATA%\Nexus\logs\nexus.log`.

**It says it is out of free usage.** Add another service, as above, or wait for
the allowance to reset.

**It says it cannot see my screen.** Only some services accept images. If Nexus
has fallen through to a text-only one, screen questions have to wait until a
service that can see is available again.

**It will not start.** Run `Nexus.exe --console` from a terminal to see why.

---

## Building it yourself

Requires **Python 3.12** — the machine-learning packages lag newer versions.

```
git clone https://github.com/abdullah61305/Nexus
cd Nexus
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m scripts.setup          # fetch Piper, a voice, and the speech model
python -m nexus
```

Tests, and the packaged executable:

```
pip install -r requirements-dev.txt
python -m pytest

pip install pyinstaller
python -m scripts.build          # writes dist\Nexus
```

Every setting is documented in [`.env.example`](.env.example); copy it to
`.env` to change any of them.

### How it fits together

```
hotkey ──► microphone ──► Whisper ──► AI service ──► Piper ──► speakers
           always open     on your      tools:        streams
           with a          machine      screen,       sentence
           pre-roll                     browser       by sentence
```

Each stage is a protocol in `nexus/core/protocols.py`, so swapping the speech
recogniser, the AI service or the voice means adding a class and changing one
line in `nexus/app.py`. Adding a new capability — something Nexus can *do* —
means adding a tool in `nexus/tools/` and nothing else.

A few decisions worth knowing about, if you are reading the code: the
microphone stays open with a short circular buffer so the first syllable of a
sentence is never clipped; replies are spoken sentence by sentence as they are
generated, so time-to-first-word does not grow with the length of the answer;
and the executable is a console application that hides its own window, because
Windows Smart App Control blocks an unsigned *windowed* binary and allows the
identical console one. The commit history explains the rest.

---

## Built with

[faster-whisper](https://github.com/SYSTRAN/faster-whisper) for speech
recognition · [Piper](https://github.com/rhasspy/piper) for the voice ·
[Groq](https://groq.com), [Cerebras](https://cerebras.ai) and
[Google Gemini](https://ai.google.dev) for the thinking ·
[Silero VAD](https://github.com/snakers4/silero-vad) for knowing when you have
stopped talking.

The orb's shader is adapted from a community WebGL orb that circulated as a
React component; the original author is unknown to us. If you recognise it,
please [open an issue](https://github.com/abdullah61305/Nexus/issues) and we
will credit you — see [`docs/orb`](docs/orb).

## Licence

MIT — see [LICENSE](LICENSE).

Built by **Abdullah Farooq** ([@abdullah61305](https://github.com/abdullah61305)),
with Claude as pair programmer.
