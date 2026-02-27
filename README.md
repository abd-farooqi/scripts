# Scripts

A collection of automation scripts for various platforms.

## Contents

| Script | Platform | Description |
|--------|----------|-------------|
| [`monkeytype.py`](#monkeytype-bot--python) | [MonkeyType](https://monkeytype.com/) | Selenium bot with CDP keystrokes, anatomical hand model, stealth browser |
| [`monkeytype.js`](#monkeytype-bot--userscript) | [MonkeyType](https://monkeytype.com/) | Tampermonkey userscript version — runs in your own browser profile |
| [`discord.js`](#discord-quest-completer) | [Discord](https://discord.com/) | Auto-completes Discord Quests (video, game, stream, activity) |

---

## MonkeyType Bot — Python

**`monkeytype.py`** (~2300 lines)

A Selenium-based typing bot for MonkeyType. Launches a stealth Chrome browser and types via Chrome DevTools Protocol with human-realistic timing.

### Features

- **CDP keystroke engine** — types via Chrome DevTools Protocol, cross-platform (Windows/macOS/Linux, X11/Wayland)
- **12 browser stealth patches** — `navigator.webdriver` removal, `window.chrome` spoofing, canvas/audio/WebGL fingerprint noise, WebRTC leak prevention, plugin spoofing, `toString()` override
- **Anatomical hand model** — 9 fingers mapped to every key with per-finger speed multipliers, row distance penalties, same-finger bigrams, hand alternation bonus, 47 fast + 38 slow bigrams, motor chunks
- **Kogasa consistency engine** — reimplements MonkeyType's `kogasa()` formula, targets specific consistency percentages via binary search
- **Keystroke dynamics** — ex-Gaussian distribution, AR(1) autocorrelation, warm-up/fatigue curves, burst typing, sigmoid speed curve, rhythmic periodicity, key overlap/rollover, hold-inside-IKI model
- **Error engine** — 95+ common typos, adjacent key errors, transpositions, double-taps, skips, confusion pairs, delayed detection, over-backspace, position/finger weighting
- **CDP overhead calibration** — measures and compensates for Chrome DevTools Protocol latency
- **Fresh profile per round** — randomized timing parameters prevent statistical fingerprinting across tests

### Quick Start

```bash
git clone https://github.com/abd-farooqi/scripts.git
cd scripts
pip install -r requirements.txt
python monkeytype.py
```

### CLI Usage

```bash
python monkeytype.py                      # default ~110 WPM
python monkeytype.py --wpm 90             # target 90 WPM
python monkeytype.py --wpm 120 -n 5       # 5 rounds at 120 WPM
python monkeytype.py --loop               # infinite rounds
python monkeytype.py --profile casual     # casual preset (75-95 WPM)
python monkeytype.py --profile pro        # pro preset (130-155 WPM)
python monkeytype.py --profile godlike    # godlike (155-190 WPM)
python monkeytype.py --verbose            # show debug metrics
```

| Option | Description |
|--------|-------------|
| `--wpm N` | Target WPM (default: 110) |
| `--delay SEC` | Raw inter-key delay in seconds |
| `--profile NAME` | Preset: `casual`, `average`, `fast`, `pro`, `godlike` |
| `-n N`, `--count N` | Number of rounds (default: 1) |
| `--loop` | Run forever until Ctrl+C |
| `--verbose` | Show debug metrics |

### Anti-Detection Notes

Based on analysis of [MonkeyType's source code](https://github.com/monkeytype/monkeytype):

- Bot check only triggers on **time mode** when WPM > 130 and user is not verified
- **Words, quote, custom, and zen modes skip the bot check entirely**
- Server analyzes `keySpacing` and `keyDuration` statistics (mean + SD)
- Use **words mode** whenever possible, stay under **130 WPM** in time mode

---

## MonkeyType Bot — Userscript

**`monkeytype.js`** (~1530 lines)

A Tampermonkey userscript that runs directly in your existing browser profile — no separate Chrome window needed.

### Features

All the same human simulation as the Python bot, ported to JavaScript:

- **Anatomical hand model** with per-finger timing, bigram speeds, motor chunks
- **Keystroke dynamics engine** with 15 adjustment layers (ex-Gaussian, AR(1), warmup, fatigue, sigmoid, rhythm, etc.)
- **Error engine** with 5 error types, delayed detection, over-backspace, 90+ common typos
- **Key overlap/rollover** simulation
- **Trusted event dispatch** — uses `document.execCommand('insertText')` for `isTrusted: true` InputEvents
- **Fresh profile per session** — randomized parameters each time

### Installation

1. Install [Tampermonkey](https://www.tampermonkey.net/) in your browser
2. Create a new userscript and paste the contents of `monkeytype.js`
3. Go to [monkeytype.com](https://monkeytype.com/)

### Controls

| Key | Action |
|-----|--------|
| `F6` | Toggle bot on/off |
| `F7` | Set target WPM |

Status overlay appears in the top-right corner showing current state and WPM.

---

## Discord Quest Completer

**`discord.js`** (~260 lines)

Auto-completes Discord Quests (promotional tasks that reward cosmetics) without actually performing the tasks.

### Supported Quest Types

| Task | Method |
|------|--------|
| `WATCH_VIDEO` | Sends accelerated video-progress API calls (~7x real time, bounded by server's 10s future window) |
| `WATCH_VIDEO_ON_MOBILE` | Same as above |
| `PLAY_ON_DESKTOP` | Injects fake game process into Discord's RunningGameStore (desktop app only) |
| `STREAM_ON_DESKTOP` | Patches stream metadata to fake streaming the quest game (desktop app only) |
| `PLAY_ACTIVITY` | Sends heartbeat POSTs every 20s to simulate activity participation |

### Usage

1. Open Discord desktop app (not browser! It doesn't work for browser) (press `Ctrl+Shift+I` for DevTools)
2. Go to the **Console** tab
3. Paste the contents of `discord.js` and press Enter
4. The script will find all your uncompleted quests and process them sequentially

### Features

- **Safe module lookup** — clear error messages if Discord updates break module resolution
- **API retry with exponential backoff** — retries failed calls up to 3 times (1s, 2s, 4s delays)
- **Automatic cleanup** — monkey-patched functions are always restored via `try/finally`, even on errors
- **Handles both config versions** — works with v1 and v2 quest configurations
- **Null-safe channel selection** — gracefully handles missing DM/voice channels

### Timing

| Quest Type | Real Time Required |
|---|---|
| Video (15 min quest) | ~2 minutes |
| Play on Desktop (15 min quest) | ~15 minutes (server-controlled) |
| Stream on Desktop (15 min quest) | ~15 minutes (server-controlled) |
| Play Activity (15 min quest) | ~15 minutes (20s heartbeat interval) |

Video quests are the fastest because the client controls the progress timestamps. Play/Stream/Activity quests run at real time because the server controls the heartbeat schedule.

---

## Project Structure

```
scripts/
  monkeytype.py      # Python/Selenium typing bot
  monkeytype.js      # Tampermonkey userscript typing bot
  discord.js         # Discord quest completer
  requirements.txt   # Python dependencies (selenium)
  image.png          # MonkeyType screenshot
  modes.png          # MonkeyType modes reference
  LICENSE            # MIT
```

## Disclaimer

These scripts are for educational purposes only. The authors are not responsible for any misuse or consequences. Use at your own risk.
