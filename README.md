# MonkeyType Bot — Advanced Undetectable Edition

[![made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)

The most advanced typing bot for [MonkeyType](https://monkeytype.com/). Uses an anatomical hand model, ex-Gaussian timing distributions, kogasa consistency engine, and comprehensive browser stealth to produce typing patterns indistinguishable from a real human.

**Cross-platform** — Works on Windows, macOS, and Linux with zero OS-specific configuration.

## Features

### Core
- **CDP Keystroke Engine** — Types via Chrome DevTools Protocol, no OS-level keyboard simulation needed
- **Cross-platform** — Works on any OS, any display server (Wayland, X11, Windows, macOS)
- **Fully autonomous** — Auto-detects tests, auto-types, auto-waits for results, auto-repeats
- **Single dependency** — Only requires `selenium`
- **CDP overhead calibration** — Measures Chrome DevTools Protocol latency at startup and compensates for it in timing calculations

### Anti-Detection Systems

#### 1. Selenium Stealth (12 fingerprint defenses)
Comprehensive browser fingerprint patching injected before page load:
- `navigator.webdriver` removed
- `window.chrome` full object spoofed (runtime, loadTimes, csi, app)
- `navigator.permissions.query` overridden
- `navigator.plugins` spoofed (5 realistic plugins with MimeType arrays)
- `navigator.languages` set to `['en-US', 'en']`
- Canvas fingerprint noise injection (random RGBA pixel perturbation)
- AudioContext fingerprint noise (channelCount override)
- WebRTC leak prevention (RTCPeerConnection blocked)
- WebGL vendor/renderer spoofed (platform-matched: Intel on Linux, Apple on macOS, ANGLE on Windows)
- iframe `contentWindow` patched
- `Function.prototype.toString` overridden to hide all modifications
- Platform-aware User-Agent consistency

#### 2. Anatomical Hand Model
Every keystroke is timed based on physical finger mechanics:
- **9 fingers** mapped to every key (L-pinky through R-pinky + thumb for space)
- **Per-finger speed multipliers** — pinkies 1.35x slower, index fingers 0.90x, thumb 0.75x
- **Row distance penalties** — reaching from home row adds delay scaled by distance
- **Same-finger bigrams** — typing two consecutive keys with the same finger adds delay (precomputed set)
- **Hand alternation bonus** — alternating hands is faster than same-hand sequences
- **47 fast bigrams** (th, er, in, etc.) and **38 slow bigrams** (zx, qw, etc.) with per-profile randomized speed multipliers
- **Motor chunks** — common letter sequences (tion, ing, ment, etc.) typed at burst speed
- **Mutually exclusive penalty system** — same-key repeat, same-finger-bigram, and generic same-finger penalties don't stack (most specific wins)

#### 3. Kogasa Consistency Engine
Targets MonkeyType's exact consistency metric:
- Reimplements MonkeyType's `kogasa()` formula: `100 * (1 - tanh(cov + cov^3/3 + cov^5/5))`
- Inverse kogasa via binary search to target specific consistency percentages
- Profile-based targets: casual 50-65%, good 60-75%, pro 68-82%, elite 72-85%
- Monitors achieved key consistency in real-time and reports after each test

#### 4. Keystroke Dynamics Engine
Full statistical simulation for every inter-key interval:
- **Ex-Gaussian distribution** — Gaussian core + exponential tail for cognitive pauses (replaces simple Gaussian mixture)
- **AR(1) autocorrelation** — each delay is influenced by the previous one (momentum)
- **Warm-up ramp** — starts slower, reaches cruising speed over first 2-5 words
- **Fatigue curve** — gradually slows down after 40-70 words
- **Burst typing** — short common words typed in rapid bursts (muscle memory)
- **Motor chunking** — known letter sequences (tion, ing, etc.) get extra speed boost
- **Sigmoid speed curve** — accelerates to peak mid-test, decelerates toward end
- **Rhythmic periodicity** — subtle sinusoidal timing variation (~4-6 Hz)
- **Word boundary timing** — variable pauses at word starts and between spaces
- **Word difficulty scaling** — uncommon/long words get additional cognitive pause
- **Proportional key hold** — hold duration scales with typing speed (40-55% of IKI)
- **Log-normal hold distribution** — realistic hold time distribution with spacing correlation
- **True key overlap/rollover** — simultaneous key holding via `OverlapState` class
- **Delay clamping** — extreme outlier delays capped at 2.0x base to protect consistency
- **Hold-inside-IKI model** — hold time budgeted within the inter-key interval, not added on top

#### 5. Context-Aware Error Engine
Realistic typo patterns that match human motor errors:
- **95+ common word typos** — "the" -> "teh"/"hte", "would" -> "woudl", etc.
- **Adjacent key errors** — pressing neighboring keys (precomputed adjacency map)
- **Motor confusion pairs** — 14 pairs: b/v, n/m, d/f, i/o, etc.
- **Transposition errors** — swapping consecutive characters
- **Double-tap errors** — accidentally pressing a key twice
- **Skip errors** — missing a character entirely
- **Profile-driven error weights** — distribution of error types varies with speed (faster typists make more transpositions/skips)
- **Reduced whole-word typos at high WPM** — common_typo rate scales down above 100 WPM
- **Position weighting** — near-zero errors on first char, peak at positions 3-5
- **Finger weighting** — more errors on pinkies (1.5x) and number row (1.8x)
- **Fatigue scaling** — error rate increases after 40+ words
- **Difficult transition detection** — same finger + different row = higher error rate
- **Delayed error detection** — 30% of errors noticed 1-3 chars late (type past, then backspace)
- **Over-backspace** — 12% chance of deleting one extra character when correcting
- **Correction behavior** — 85-92% of errors are corrected, rest left uncorrected
- **Speed-capped error rate** — error rate plateaus above 100 WPM (fast typists are skilled)

#### 6. Mouse Behavior Simulation
- Occasional micro-movements during typing (3% chance per word)
- CDP-based mouse clicks for focusing the typing area
- Randomized click positions within the words wrapper

#### 7. Smart Mode Detection
- Reads active mode/time/word-count from the DOM
- Warns when using time mode at high WPM (bot detection risk)
- Dynamically loads new words in time mode as they appear

#### 8. Fresh Profile Per Round
- Each test round generates a new `HumanProfile` with randomized parameters
- Bigram speed tables regenerated per profile
- Prevents consecutive tests from having identical statistical signatures

## Quick Start

### 1. Install Python 3.8+

- **Windows**: Download from [python.org](https://www.python.org/downloads/) (check "Add to PATH")
- **macOS**: `brew install python`
- **Linux**: Usually pre-installed. If not: `sudo apt install python3 python3-pip`

### 2. Install Chrome

Any Chromium-based browser works: Google Chrome, Chromium, Brave, or Microsoft Edge.

### 3. Run the Bot

```bash
git clone https://github.com/MusadiqPasha/MonkeyType-BOT.git
cd MonkeyType-BOT
pip install -r requirements.txt
python monkeytype.py
```

The bot will:
1. Launch a stealth Chrome browser and open MonkeyType
2. Calibrate CDP overhead (measures Chrome DevTools Protocol latency)
3. Give you 8 seconds to log in and configure your test
4. Auto-detect when a test is ready and start typing
5. Display results (WPM, accuracy, consistency) and repeat if configured

## CLI Usage

```
python monkeytype.py [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--wpm N` | Target WPM (default: 110) |
| `--delay SEC` | Raw inter-key delay in seconds |
| `--profile NAME` | Use a preset profile (see below) |
| `-n N`, `--count N` | Number of rounds (default: 1) |
| `--loop` | Run forever until Ctrl+C |
| `--verbose` | Show debug metrics (timing stats, consistency tracking) |

### Examples

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

### Profile Presets

Each profile randomizes WPM within its range each round:

| Profile | WPM Range | Best For |
|---------|-----------|----------|
| `casual` | 75-95 | Looks like a normal typist |
| `average` | 95-115 | Solid everyday typing |
| `fast` | 115-135 | Skilled typist |
| `pro` | 130-155 | Competitive typist |
| `godlike` | 155-190 | Use words mode only! |

## Anti-Detection Strategy Guide

### How MonkeyType Detects Bots

Based on analysis of [MonkeyType's source code](https://github.com/monkeytype/monkeytype):

1. **Bot check only triggers on time mode** when WPM > 130 and user is not verified
2. **Words, quote, custom, and zen modes skip the bot check entirely**
3. Analyzes `keySpacing` (inter-key intervals) and `keyDuration` (key hold times) — both mean and standard deviation
4. Uses `kogasa()` for consistency scoring — too-consistent = bot
5. Checks `keyOverlap` (rollover typing)
6. WPM caps: 350 general, 420 for words/10
7. Accuracy floor: 75%
8. Results > 250 WPM on 15s/60s time mode are flagged for manual review

### Recommended Settings

| Scenario | Mode | WPM | Profile |
|----------|------|-----|---------|
| Safest | words | < 130 | `casual` or `average` |
| Normal | words | 100-150 | `fast` or `pro` |
| High speed | words | 150-190 | `godlike` |
| Time mode (risky) | time | < 125 | `casual` or `average` |

**Key rules:**
- Use **words mode** instead of time mode whenever possible
- Stay under **130 WPM** in time mode if unverified
- Use **60s or longer** time tests rather than 15s
- Don't run back-to-back tests at identical speeds (use `--profile` for variation)

## How It Works (Technical)

```
                    +------------------+
                    |   CLI / Argparse |
                    |   (--verbose)    |
                    +--------+---------+
                             |
                    +--------v---------+
                    | Stealth Browser   |
                    | (12 FP defenses) |
                    +--------+---------+
                             |
                    +--------v---------+
                    | CDP Calibration   |
                    | (overhead meas.) |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v---+  +-------v------+ +----v---------+
    | Hand Model  |  | Kogasa Engine| | Error Engine  |
    | (per-finger |  | (consistency | | (profile-     |
    |  timing,    |  |  targeting,  | |  weighted     |
    |  bigrams,   |  |  CoV target) | |  error types, |
    |  chunks)    |  +--------------+ |  delayed det.)|
    +------+------+                   +------+--------+
           |                                 |
           +--------+-------+--------+-------+
                    |                |
           +--------v--------+  +---v-----------+
           | Keystroke        |  | Mouse          |
           | Dynamics Engine  |  | Simulation     |
           | (ex-Gaussian,   |  | (micro-moves,  |
           |  AR(1), sigmoid, |  |  CDP clicks)   |
           |  motor chunks,  |  +----------------+
           |  overlap/roll-  |
           |  over, fatigue) |
           +--------+--------+
                    |
           +--------v---------+
           | CDP Key Events   |
           | (keyDown/keyUp   |
           |  with calibrated |
           |  hold timing)    |
           +------------------+
```

1. **Browser Launch** — Selenium launches Chrome with 12 stealth patches injected via `Page.addScriptToEvaluateOnNewDocument`
2. **CDP Calibration** — Measures median CDP call latency over 20 benign calls, subtracts from timing
3. **Test Detection** — Polls the DOM for `.word.active` elements to detect test readiness
4. **Word Reading** — Reads all words at once from `.word > letter` elements; dynamically loads new words in time mode
5. **Typing Loop** — For each character:
   - Hand model computes finger/row/bigram/chunk timing (mutually exclusive penalties)
   - Dynamics engine applies ex-Gaussian noise, AR(1) autocorrelation, warm-up, fatigue, burst, sigmoid curve, rhythm
   - Error engine may inject a typo (with possible delayed detection and over-backspace)
   - Previous key's hold time is subtracted from the IKI budget (hold-inside-IKI model)
   - CDP overhead is subtracted from sleep times
   - CDP sends `keyDown` event, waits for computed hold duration, sends `keyUp`
6. **Results** — Reads WPM, accuracy, and consistency from the result DOM elements

## Project Structure

```
MonkeyType-BOT/
  monkeytype.py      # The entire bot (~2300 lines)
  requirements.txt   # Just: selenium
  README.md          # This file
```

## Disclaimer

This bot is intended for educational purposes only. The authors are not responsible for any misuse or consequences. Use responsibly and at your own risk.
