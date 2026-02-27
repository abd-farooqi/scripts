#!/usr/bin/env python3
"""
MonkeyType Bot — God-Level Undetectable Typing Automation.

    python monkeytype.py                      # default ~110 WPM, 1 round
    python monkeytype.py --wpm 120            # target 120 WPM
    python monkeytype.py --wpm 90 --loop      # infinite rounds at 90 WPM
    python monkeytype.py --wpm 130 -n 5       # 5 rounds at 130 WPM
    python monkeytype.py --profile casual     # preset: casual (75-95 WPM)
    python monkeytype.py --profile pro        # preset: pro (130-155 WPM)
    python monkeytype.py --profile godlike    # preset: godlike (155-190 WPM)
    python monkeytype.py --delay 0.08         # raw delay control
    python monkeytype.py --verbose            # show debug keystroke metrics

Anti-detection systems:
  1. Selenium stealth: full browser fingerprint patching (plugins, canvas, audio,
     WebGL, WebRTC, hardwareConcurrency, deviceMemory, platform, user-agent)
  2. Anatomical hand model: per-finger travel time, hand alternation, row distance
  3. Kogasa consistency targeting: generates keySpacing arrays that hit 50-80%
  4. Ex-Gaussian timing: matches empirical keystroke timing research distributions
  5. AR(1) serial autocorrelation: consecutive keystrokes have realistic momentum
  6. Correlated keySpacing/keyDuration: faster typing = shorter hold times
  7. Motor chunking: common short words typed as single motor units
  8. Word difficulty scoring: harder upcoming words cause longer pre-word pauses
  9. True key overlap/rollover: overlapping keyDown/keyUp CDP events
  10. Delayed error detection: sometimes types past an error before correcting
  11. Position-weighted errors: errors cluster at positions 3-5, not on first char
  12. Shift key simulation: proper Shift keyDown/keyUp for uppercase chars
  13. Rhythmic periodicity: subtle sinusoidal timing modulation (~4-6 Hz)
  14. Sigmoid speed curve: accelerate into flow, decelerate near end
  15. Per-round parameter regeneration: no two tests have identical signatures
  16. Dynamic word polling: handles time mode's lazy word loading
"""

# ---------------------------------------------------------------------------
#  Auto-install selenium if missing
# ---------------------------------------------------------------------------
import subprocess as _sp
import sys as _sys

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import (
        WebDriverException, NoSuchWindowException, InvalidSessionIdException)
except ImportError:
    print("Installing selenium...")
    try:
        _sp.check_call([_sys.executable, "-m", "pip", "install", "selenium"],
                        stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
    except _sp.CalledProcessError:
        print("ERROR: Failed to install selenium. Run: pip install selenium")
        _sys.exit(1)
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import (
        WebDriverException, NoSuchWindowException, InvalidSessionIdException)

import argparse
import logging
import math
import platform
import shutil
import signal
import random
import time
import os

# ===========================================================================
#  Logging  (Issue #21: proper logging framework with --verbose)
# ===========================================================================

log = logging.getLogger("monkeytype-bot")
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(logging.Formatter("  [%(levelname)s] %(message)s"))
log.addHandler(_log_handler)
log.setLevel(logging.WARNING)  # default; --verbose sets to DEBUG


# ===========================================================================
#  Constants
# ===========================================================================

MONKEYTYPE_URL = "https://monkeytype.com/"
POLL_INTERVAL = 0.8
INITIAL_WAIT = 8
REFERENCE_WPM = 110        # Issue #10: extracted constant
MAX_RETRY_PER_ROUND = 5    # Issue #19: prevent infinite retry loops

# Platform-aware minimum sleep (Issue #5 note: Windows timer res ~15ms)
MIN_SLEEP = 0.015 if platform.system() == "Windows" else 0.002


# ===========================================================================
#  Selenium Stealth — comprehensive browser fingerprint patching
#  Issues #1, #11, #12: full fingerprint defense suite
# ===========================================================================

def _build_stealth_js() -> str:
    """Build platform-aware stealth injection script.

    Issue #1:  Proper PluginArray with real plugin objects
    Issue #11: Canvas, AudioContext, WebRTC, hardwareConcurrency, deviceMemory
    Issue #12: Platform-matched WebGL vendor/renderer
    """
    # Issue #12: pick WebGL strings that match the current platform
    system = platform.system()
    if system == "Darwin":
        gl_vendor = "Apple"
        gl_renderer = "Apple M1 Pro"
    elif system == "Windows":
        gl_vendor = "Google Inc. (NVIDIA)"
        gl_renderer = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    else:  # Linux
        gl_vendor = "Google Inc. (Intel)"
        gl_renderer = "ANGLE (Intel, Mesa Intel(R) UHD Graphics 770 (ADL-S GT1), OpenGL 4.6)"

    return f"""
// --- 1. Remove navigator.webdriver ---
Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});

// --- 2. Spoof window.chrome (Issue #11: full chrome object) ---
window.chrome = {{
    runtime: {{
        onMessage: {{ addListener: function() {{}}, removeListener: function() {{}} }},
        onConnect: {{ addListener: function() {{}}, removeListener: function() {{}} }},
        sendMessage: function() {{}},
        connect: function() {{ return {{ onMessage: {{ addListener: function() {{}} }}, postMessage: function() {{}} }}; }},
        PlatformOs: {{MAC: 'mac', WIN: 'win', ANDROID: 'android', CROS: 'cros', LINUX: 'linux', OPENBSD: 'openbsd'}},
        PlatformArch: {{ARM: 'arm', X86_32: 'x86-32', X86_64: 'x86-64', MIPS: 'mips', MIPS64: 'mips64'}},
        requestUpdateCheck: function() {{}},
        getManifest: function() {{ return {{}}; }},
        id: undefined,
    }},
    loadTimes: function() {{ return {{}}; }},
    csi: function() {{ return {{}}; }},
    app: {{
        isInstalled: false,
        InstallState: {{INSTALLED: 'installed', DISABLED: 'disabled', NOT_INSTALLED: 'not_installed'}},
        RunningState: {{RUNNING: 'running', CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run'}},
        getDetails: function() {{}},
        getIsInstalled: function() {{}},
        runningState: function() {{ return 'cannot_run'; }},
    }},
}};

// --- 3. Override permissions query ---
const originalQuery = window.navigator.permissions.query.bind(window.navigator.permissions);
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({{ state: Notification.permission }})
        : originalQuery(parameters);

// --- 4. Spoof plugins (Issue #1: proper PluginArray objects) ---
(function() {{
    const pluginData = [
        {{name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'}},
        {{name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''}},
        {{name: 'Chromium PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'}},
        {{name: 'Chromium PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: ''}},
        {{name: 'Native Client', filename: 'internal-nacl-plugin', description: ''}},
    ];
    const fakePlugins = pluginData.map(p => {{
        const plugin = Object.create(Plugin.prototype);
        Object.defineProperties(plugin, {{
            name: {{ value: p.name, enumerable: true }},
            filename: {{ value: p.filename, enumerable: true }},
            description: {{ value: p.description, enumerable: true }},
            length: {{ value: 0, enumerable: true }},
        }});
        return plugin;
    }});
    const fakePluginArray = Object.create(PluginArray.prototype);
    for (let i = 0; i < fakePlugins.length; i++) {{
        Object.defineProperty(fakePluginArray, i, {{ value: fakePlugins[i], enumerable: true }});
    }}
    Object.defineProperty(fakePluginArray, 'length', {{ value: fakePlugins.length }});
    fakePluginArray.item = function(i) {{ return fakePlugins[i] || null; }};
    fakePluginArray.namedItem = function(name) {{ return fakePlugins.find(p => p.name === name) || null; }};
    fakePluginArray.refresh = function() {{}};
    Object.defineProperty(navigator, 'plugins', {{ get: () => fakePluginArray }});
}})();

// --- 5. Spoof languages ---
Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});

// --- 6. WebGL vendor/renderer (Issue #12: platform-matched) ---
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {{
    if (parameter === 37445) return '{gl_vendor}';
    if (parameter === 37446) return '{gl_renderer}';
    return getParameter.call(this, parameter);
}};
const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
WebGL2RenderingContext.prototype.getParameter = function(parameter) {{
    if (parameter === 37445) return '{gl_vendor}';
    if (parameter === 37446) return '{gl_renderer}';
    return getParameter2.call(this, parameter);
}};

// --- 7. Prevent iframe contentWindow detection ---
try {{
    const descriptor = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
    Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {{
        get: function() {{
            const win = descriptor.get.call(this);
            try {{ win.chrome = window.chrome; }} catch(e) {{}}
            return win;
        }}
    }});
}} catch(e) {{}}

// --- 8. Canvas fingerprint noise (Issue #11) ---
(function() {{
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type) {{
        if (this.width > 16 && this.height > 16) {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                const imageData = ctx.getImageData(0, 0, Math.min(this.width, 4), Math.min(this.height, 4));
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] = imageData.data[i] ^ (Math.random() * 2 | 0);
                }}
                ctx.putImageData(imageData, 0, 0);
            }}
        }}
        return origToDataURL.apply(this, arguments);
    }};
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {{
        if (this.width > 16 && this.height > 16) {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                const imageData = ctx.getImageData(0, 0, Math.min(this.width, 4), Math.min(this.height, 4));
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    imageData.data[i] = imageData.data[i] ^ (Math.random() * 2 | 0);
                }}
                ctx.putImageData(imageData, 0, 0);
            }}
        }}
        return origToBlob.apply(this, arguments);
    }};
}})();

// --- 9. AudioContext fingerprint noise (Issue #11) ---
(function() {{
    const origGetFloatFrequencyData = AnalyserNode.prototype.getFloatFrequencyData;
    AnalyserNode.prototype.getFloatFrequencyData = function(array) {{
        origGetFloatFrequencyData.call(this, array);
        for (let i = 0; i < array.length; i++) {{
            array[i] += (Math.random() - 0.5) * 0.1;
        }}
    }};
    const origCreateOscillator = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {{
        const osc = origCreateOscillator.call(this);
        const origConnect = osc.connect.bind(osc);
        // tiny detuning to change fingerprint
        osc.connect = function(dest) {{
            if (osc.detune) osc.detune.value += (Math.random() - 0.5) * 0.01;
            return origConnect(dest);
        }};
        return osc;
    }};
}})();

// --- 10. Hardware spoofing (Issue #11) ---
Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {random.choice([4, 8, 12, 16])} }});
Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {random.choice([4, 8, 16])} }});

// --- 11. WebRTC IP leak prevention (Issue #11) ---
(function() {{
    if (window.RTCPeerConnection) {{
        const origRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(config) {{
            if (config && config.iceServers) {{
                config.iceServers = [];
            }}
            const pc = new origRTC(config);
            const origCreateOffer = pc.createOffer.bind(pc);
            pc.createOffer = function(options) {{
                if (options) options.offerToReceiveAudio = false;
                return origCreateOffer(options);
            }};
            return pc;
        }};
        window.RTCPeerConnection.prototype = origRTC.prototype;
    }}
}})();

// --- 12. Override toString to hide ALL modifications (Issue #8 from analysis) ---
(function() {{
    const protoToString = Function.prototype.toString;
    const patchedFns = new WeakSet();
    const nativeStrings = new WeakMap();

    function markPatched(fn, nativeStr) {{
        patchedFns.add(fn);
        nativeStrings.set(fn, nativeStr);
    }}

    Function.prototype.toString = function() {{
        if (patchedFns.has(this)) {{
            return nativeStrings.get(this) || 'function () {{ [native code] }}';
        }}
        return protoToString.call(this);
    }};

    // Mark all our patches
    markPatched(navigator.permissions.query, 'function query() {{ [native code] }}');
    markPatched(WebGLRenderingContext.prototype.getParameter, 'function getParameter() {{ [native code] }}');
    markPatched(WebGL2RenderingContext.prototype.getParameter, 'function getParameter() {{ [native code] }}');
    markPatched(HTMLCanvasElement.prototype.toDataURL, 'function toDataURL() {{ [native code] }}');
    markPatched(HTMLCanvasElement.prototype.toBlob, 'function toBlob() {{ [native code] }}');
    markPatched(AnalyserNode.prototype.getFloatFrequencyData, 'function getFloatFrequencyData() {{ [native code] }}');
    markPatched(Function.prototype.toString, 'function toString() {{ [native code] }}');
}})();
"""


def apply_stealth(driver):
    """Inject stealth patches into the browser via CDP."""
    stealth_js = _build_stealth_js()
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": stealth_js
        })
    except Exception as exc:
        log.warning("Could not inject stealth JS: %s", exc)


# ===========================================================================
#  CDP Keystroke Engine  (Issue #2: Shift key support)
# ===========================================================================

PUNCT_MAP = {
    ",":  ("Comma",        188),  ".":  ("Period",       190),
    "/":  ("Slash",        191),  ";":  ("Semicolon",    186),
    "'":  ("Quote",        222),  "-":  ("Minus",        189),
    "=":  ("Equal",        187),  "[":  ("BracketLeft",  219),
    "]":  ("BracketRight", 221),  "\\": ("Backslash",    220),
    "`":  ("Backquote",    192),
}

SHIFT_PUNCT_MAP = {
    "!": ("!", "Digit1",       49),   "@": ("@", "Digit2",       50),
    "#": ("#", "Digit3",       51),   "$": ("$", "Digit4",       52),
    "%": ("%", "Digit5",       53),   "^": ("^", "Digit6",       54),
    "&": ("&", "Digit7",       55),   "*": ("*", "Digit8",       56),
    "(": ("(", "Digit9",       57),   ")": (")", "Digit0",       48),
    "_": ("_", "Minus",       189),   "+": ("+", "Equal",        187),
    "{": ("{", "BracketLeft", 219),   "}": ("}", "BracketRight", 221),
    "|": ("|", "Backslash",   220),   ":": (":", "Semicolon",    186),
    '"': ('"', "Quote",       222),   "<": ("<", "Comma",        188),
    ">": (">", "Period",      190),   "?": ("?", "Slash",        191),
    "~": ("~", "Backquote",   192),
}

# Issue #22: removed unused Enter/Escape entries
SPECIAL_KEYS = {
    "Backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8},
    "Tab":       {"key": "Tab",       "code": "Tab",       "keyCode": 9},
    "ShiftLeft": {"key": "Shift",     "code": "ShiftLeft",  "keyCode": 16},
}


def char_to_key_info(char: str) -> dict:
    """Map any character to CDP key event parameters.

    Issue #2: returns 'needs_shift' flag for uppercase and shift-punct chars.
    """
    if char.isalpha() and len(char) == 1:
        needs_shift = char.isupper()
        return {
            "key": char, "code": f"Key{char.upper()}",
            "keyCode": ord(char.upper()), "text": char,
            "needs_shift": needs_shift,
        }
    if char.isdigit():
        return {
            "key": char, "code": f"Digit{char}",
            "keyCode": ord(char), "text": char,
            "needs_shift": False,
        }
    if char == " ":
        return {"key": " ", "code": "Space", "keyCode": 32, "text": " ",
                "needs_shift": False}
    if char in PUNCT_MAP:
        code, vk = PUNCT_MAP[char]
        return {"key": char, "code": code, "keyCode": vk, "text": char,
                "needs_shift": False}
    if char in SHIFT_PUNCT_MAP:
        key, code, vk = SHIFT_PUNCT_MAP[char]
        return {"key": key, "code": code, "keyCode": vk, "text": char,
                "needs_shift": True}
    return {"key": char, "code": "", "keyCode": 0, "text": char,
            "needs_shift": False}


def _cdp_dispatch_key(driver, event_type: str, key_info: dict,
                      modifiers: int = 0):
    """Low-level CDP key event dispatch."""
    params = {
        "type": event_type,
        "key": key_info["key"],
        "code": key_info["code"],
        "windowsVirtualKeyCode": key_info["keyCode"],
        "nativeVirtualKeyCode": key_info["keyCode"],
        "modifiers": modifiers,
    }
    if event_type == "keyDown" and key_info.get("text"):
        params["text"] = key_info["text"]
        params["unmodifiedText"] = key_info["text"]
    driver.execute_cdp_cmd("Input.dispatchKeyEvent", params)


# Estimated round-trip overhead per CDP call (seconds).
# Measured once at startup; used to compensate sleep times.
CDP_OVERHEAD = 0.003  # conservative default, refined by calibration


def cdp_key_down(driver, key_info: dict, modifiers: int = 0):
    """Send keyDown event via CDP."""
    is_printable = bool(key_info.get("text"))
    evt_type = "keyDown" if is_printable else "rawKeyDown"
    _cdp_dispatch_key(driver, evt_type, key_info, modifiers)


def cdp_key_up(driver, key_info: dict, modifiers: int = 0):
    """Send keyUp event via CDP."""
    _cdp_dispatch_key(driver, "keyUp", key_info, modifiers)


def cdp_press_key(driver, key_info: dict, hold_duration: float = 0.0,
                  modifiers: int = 0):
    """Full key press: down, hold, up.

    Compensates hold_duration for the CDP overhead of the keyUp call,
    so the actual keyDown-to-keyUp wall time matches the requested hold.
    """
    cdp_key_down(driver, key_info, modifiers)
    if hold_duration > 0:
        # Subtract one CDP call overhead (for the upcoming keyUp)
        compensated = max(MIN_SLEEP, hold_duration - CDP_OVERHEAD)
        time.sleep(compensated)
    cdp_key_up(driver, key_info, modifiers)


def cdp_type_char(driver, char: str, hold_duration: float = 0.0):
    """Type a single character via CDP.

    Issue #2: dispatches Shift keyDown/keyUp around uppercase and shift-punct
    characters, with realistic Shift hold timing.

    Returns the estimated wall-clock overhead (CDP calls) beyond the requested
    hold_duration, so callers can subtract it from subsequent sleep.
    """
    info = char_to_key_info(char)
    if info["needs_shift"]:
        # Shift down (hold Shift while typing the char)
        shift_info = SPECIAL_KEYS["ShiftLeft"]
        cdp_key_down(driver, shift_info)
        time.sleep(random.uniform(0.012, 0.035))  # realistic pre-char Shift hold
        # Char with modifiers=8 (Shift modifier flag)
        cdp_press_key(driver, info, hold_duration, modifiers=8)
        time.sleep(random.uniform(0.008, 0.025))  # brief gap before Shift release
        cdp_key_up(driver, shift_info)
    else:
        cdp_press_key(driver, info, hold_duration)


def cdp_backspace(driver, hold_duration: float = 0.0):
    """Send a backspace keystroke via CDP."""
    cdp_press_key(driver, SPECIAL_KEYS["Backspace"], hold_duration)


def cdp_mouse_move(driver, x: float, y: float):
    """Move mouse to (x, y) via CDP."""
    try:
        driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": int(x), "y": int(y),
        })
    except Exception as exc:
        log.debug("Mouse move failed: %s", exc)


def cdp_mouse_click(driver, x: float, y: float):
    """Click at (x, y) via CDP."""
    try:
        driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": int(x), "y": int(y),
            "button": "left", "clickCount": 1,
        })
        time.sleep(random.uniform(0.05, 0.12))
        driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": int(x), "y": int(y),
            "button": "left", "clickCount": 1,
        })
    except Exception as exc:
        log.debug("Mouse click failed: %s", exc)


# ===========================================================================
#  True Key Overlap Engine  (Issue #18: real overlapping keyDown/keyUp)
# ===========================================================================

class OverlapState:
    """Tracks the currently held-down key for true rollover simulation.

    Instead of just reducing delay, we actually hold the previous key down
    while pressing the next key, then release the previous key after a brief
    overlap period.
    """
    def __init__(self):
        self.held_key_info: dict | None = None
        self.held_needs_shift: bool = False

    def release_held(self, driver):
        """Release any currently held key."""
        if self.held_key_info is not None:
            try:
                cdp_key_up(driver, self.held_key_info)
                if self.held_needs_shift:
                    cdp_key_up(driver, SPECIAL_KEYS["ShiftLeft"])
            except Exception as exc:
                log.debug("Release held key failed: %s", exc)
            self.held_key_info = None
            self.held_needs_shift = False

    def type_with_overlap(self, driver, char: str, hold_duration: float,
                          overlap_time: float):
        """Type a char while the previous key is still held down (true rollover).

        Sequence:
        1. keyDown(char_n)         -- previous key still held
        2. sleep(overlap_time)
        3. keyUp(char_{n-1})       -- release previous key
        4. sleep(remaining_hold)
        5. Store char_n as held    -- will be released by next call or explicit release
        """
        info = char_to_key_info(char)
        needs_shift = info["needs_shift"]

        # Press Shift if needed for this char
        if needs_shift:
            cdp_key_down(driver, SPECIAL_KEYS["ShiftLeft"])
            time.sleep(random.uniform(0.010, 0.025))

        # Press the new key (previous still held)
        modifiers = 8 if needs_shift else 0
        cdp_key_down(driver, info, modifiers)

        # Brief overlap period where both keys are held
        time.sleep(overlap_time)

        # Release the PREVIOUS key
        self.release_held(driver)

        # Hold the new key for the remaining duration
        remaining = max(0.002, hold_duration - overlap_time)
        time.sleep(remaining)

        # Store as currently held (will be released by next overlap or explicit release)
        self.held_key_info = info
        self.held_needs_shift = needs_shift


# ===========================================================================
#  Anatomical Hand Model — per-finger timing and physics
# ===========================================================================

# Which finger types each key (0=L-pinky .. 7=R-pinky, 8=Thumb)
FINGER_MAP = {
    'q': 0, 'a': 0, 'z': 0, '1': 0, '`': 0,
    'w': 1, 's': 1, 'x': 1, '2': 1,
    'e': 2, 'd': 2, 'c': 2, '3': 2,
    'r': 3, 'f': 3, 'v': 3, 't': 3, 'g': 3, 'b': 3, '4': 3, '5': 3,
    'y': 4, 'h': 4, 'n': 4, 'u': 4, 'j': 4, 'm': 4, '6': 4, '7': 4,
    'i': 5, 'k': 5, ',': 5, '8': 5,
    'o': 6, 'l': 6, '.': 6, '9': 6,
    'p': 7, ';': 7, '/': 7, '0': 7, '-': 7, '=': 7, '[': 7, ']': 7,
    "'": 7, '\\': 7,
    ' ': 8,
}

# Row positions: 0=number, 1=top, 2=home, 3=bottom, 4=space
KEY_ROW = {
    '`': 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 0,
    '6': 0, '7': 0, '8': 0, '9': 0, '0': 0, '-': 0, '=': 0,
    'q': 1, 'w': 1, 'e': 1, 'r': 1, 't': 1, 'y': 1,
    'u': 1, 'i': 1, 'o': 1, 'p': 1, '[': 1, ']': 1, '\\': 1,
    'a': 2, 's': 2, 'd': 2, 'f': 2, 'g': 2, 'h': 2,
    'j': 2, 'k': 2, 'l': 2, ';': 2, "'": 2,
    'z': 3, 'x': 3, 'c': 3, 'v': 3, 'b': 3, 'n': 3,
    'm': 3, ',': 3, '.': 3, '/': 3,
    ' ': 4,
}

FINGER_SPEED = {
    0: 1.35, 1: 1.15, 2: 1.00, 3: 0.90, 4: 0.90,
    5: 1.00, 6: 1.15, 7: 1.35, 8: 0.75,
}

FINGER_HOLD = {
    0: 1.25, 1: 1.12, 2: 1.00, 3: 0.88,
    4: 0.88, 5: 1.00, 6: 1.12, 7: 1.25, 8: 0.80,
}


def get_finger(char: str) -> int:
    return FINGER_MAP.get(char.lower(), 5)


def get_row(char: str) -> int:
    return KEY_ROW.get(char.lower(), 2)


def same_hand(f1: int, f2: int) -> bool:
    if f1 == 8 or f2 == 8:
        return False
    return (f1 <= 3 and f2 <= 3) or (f1 >= 4 and f2 >= 4)


def row_distance(r1: int, r2: int) -> int:
    return abs(r1 - r2)


# Issue #17: bigram speeds regenerated per-round via function
_FAST_BIGRAMS = [
    'th', 'he', 'in', 'er', 'an', 'on', 'en', 'at', 'ou', 'ed',
    'is', 'it', 'al', 'ar', 'or', 'ti', 'te', 'st', 'se', 'le',
    'ng', 'io', 're', 'nd', 'ha', 'to', 'of',
]
_SLOW_BIGRAMS = [
    'bf', 'zx', 'qp', 'pq', 'xz', 'fb', 'mj', 'jm', 'vb', 'bv',
    'ce', 'ec', 'nu', 'un', 'my', 'ym', 'br', 'rb', 'gr', 'rg',
    'az', 'za', 'sx', 'xs', 'dc', 'cd', 'fv', 'vf', 'gt', 'tg',
    'hy', 'yh', 'ju', 'uj', 'ki', 'ik', 'lo', 'ol',
]


def _generate_bigram_speeds() -> dict:
    """Generate randomized bigram speed multipliers. Called per-round."""
    speeds = {}
    for pair in _FAST_BIGRAMS:
        speeds[pair] = random.uniform(0.55, 0.80)
    for pair in _SLOW_BIGRAMS:
        speeds[pair] = random.uniform(1.25, 1.80)
    return speeds


# Same-finger bigrams (precomputed, constant)
SAME_FINGER_PAIRS: set = set()
for _keys, _finger in [
    ('qaz', 0), ('wsx', 1), ('edc', 2), ('rfvtgb', 3),
    ('yhnujm', 4), ('ik,', 5), ('ol.', 6), ("p;/'-=[]\\", 7),
]:
    for _a in _keys:
        for _b in _keys:
            if _a != _b:
                SAME_FINGER_PAIRS.add(_a + _b)

# Adjacent keys for typos
ADJACENT_KEYS = {
    'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx', 'e': 'wsdfr',
    'f': 'dertgcv', 'g': 'frtyhhbv', 'h': 'gtyjnb', 'i': 'ujko',
    'j': 'hyuknm', 'k': 'juilm', 'l': 'kop', 'm': 'njk', 'n': 'bhjm',
    'o': 'iklp', 'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awedxz',
    't': 'rfgy', 'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
    'y': 'tghu', 'z': 'asx',
}

# Issue #8: common short words typed as motor chunks
MOTOR_CHUNKS = {
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
    'her', 'was', 'one', 'our', 'out', 'has', 'his', 'how', 'its', 'may',
    'new', 'now', 'old', 'see', 'way', 'who', 'did', 'get', 'let', 'say',
    'she', 'too', 'use', 'is', 'it', 'he', 'we', 'do', 'no', 'so', 'up',
    'if', 'my', 'as', 'at', 'be', 'by', 'go', 'in', 'me', 'of', 'on',
    'or', 'to', 'a', 'i',
}

# Letter frequency for word difficulty scoring (Issue #10)
_LETTER_FREQ = {
    'e': 13, 't': 9.1, 'a': 8.2, 'o': 7.5, 'i': 7.0, 'n': 6.7, 's': 6.3,
    'h': 6.1, 'r': 6.0, 'd': 4.3, 'l': 4.0, 'c': 2.8, 'u': 2.8, 'm': 2.4,
    'w': 2.4, 'f': 2.2, 'g': 2.0, 'y': 2.0, 'p': 1.9, 'b': 1.5, 'v': 1.0,
    'k': 0.8, 'j': 0.15, 'x': 0.15, 'q': 0.10, 'z': 0.07,
}


def word_difficulty(word: str) -> float:
    """Score word difficulty 0.0 (trivial) to 1.0+ (very hard).

    Issue #10: considers letter frequency, length, rare bigrams.
    """
    if not word:
        return 0.0
    # Length factor
    length_score = max(0, (len(word) - 3)) * 0.08

    # Letter rarity
    rarity = 0.0
    for ch in word.lower():
        freq = _LETTER_FREQ.get(ch, 0.5)
        rarity += max(0, (5.0 - freq)) * 0.02

    # Rare bigrams
    bigram_score = 0.0
    lower = word.lower()
    for j in range(len(lower) - 1):
        bg = lower[j:j+2]
        if bg in SAME_FINGER_PAIRS:
            bigram_score += 0.08

    return min(2.0, length_score + rarity + bigram_score)


# ===========================================================================
#  Kogasa Consistency Engine
# ===========================================================================

def kogasa(cov: float) -> float:
    """MonkeyType's exact consistency formula."""
    return 100 * (1 - math.tanh(cov + cov**3 / 3 + cov**5 / 5))


def compute_consistency(values: list) -> float:
    """Compute kogasa consistency from an array of values."""
    if len(values) < 2:
        return 100.0
    avg = sum(values) / len(values)
    if avg == 0:
        return 100.0
    sd = (sum((x - avg) ** 2 for x in values) / len(values)) ** 0.5
    return kogasa(sd / avg)


def target_cov_for_consistency(target_consistency: float) -> float:
    """Inverse kogasa via binary search."""
    lo, hi = 0.0, 5.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if kogasa(mid) > target_consistency:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ===========================================================================
#  Ex-Gaussian Distribution  (Issue #5)
# ===========================================================================

def exgaussian(mu: float, sigma: float, tau: float) -> float:
    """Sample from an ex-Gaussian distribution (Gaussian + Exponential).

    This is the empirically validated model for human keystroke inter-key
    intervals. Parameters:
        mu    - Gaussian mean (core typing speed)
        sigma - Gaussian SD (motor noise)
        tau   - Exponential mean (cognitive/attentional pauses)

    The result is always positive and right-skewed, matching real typing data.
    """
    gauss_part = random.gauss(mu, sigma)
    expo_part = random.expovariate(1.0 / tau) if tau > 0 else 0.0
    return gauss_part + expo_part


# ===========================================================================
#  Human Typing Profile — advanced parametric model
# ===========================================================================

class HumanProfile:
    """Comprehensive human typing simulation parameters.

    Issue #22: removed unused 'style' parameter.
    """

    def __init__(self, target_wpm: int):
        self.target_wpm = target_wpm

        # Calculate base delay from target WPM
        # Average word = 5 chars + 1 space = 6 keystrokes
        # base_delay = desired inter-key interval (keyDown to keyDown)
        # The typing loop subtracts the previous key's hold time from this
        # so hold is "inside" the interval, not added on top.
        # Speed-dependent correction: at higher WPMs, word-start pauses and
        # space gaps take proportionally more of the budget.  The correction
        # ranges from ~0.88 at low WPM to ~0.74 at very high WPM.
        # CDP overhead compensation (calibrate_cdp_overhead) handles the
        # infrastructure latency separately.
        raw_iki = 60.0 / (target_wpm * 6)
        speed_ratio = min(2.0, target_wpm / REFERENCE_WPM)  # REFERENCE_WPM=110
        # Correction factor: balances speed-up effects (motor chunks, hand
        # alternation, burst typing) against overhead (word-start pauses,
        # space gaps).  Calibrated post-variance-tightening via linear
        # interpolation: corr=0.913→158wpm, corr=1.196→84wpm @target100.
        correction = 1.04 + 0.10 * speed_ratio  # 1.13 at 100wpm, 1.14 at 110wpm, 1.15 at 120wpm
        self.base_delay = raw_iki * min(1.25, correction)

        # --- Consistency targets ---
        if target_wpm < 80:
            self.target_consistency = random.uniform(50, 65)
        elif target_wpm < 120:
            self.target_consistency = random.uniform(60, 75)
        elif target_wpm < 160:
            self.target_consistency = random.uniform(68, 82)
        else:
            self.target_consistency = random.uniform(72, 85)

        self.target_cov = target_cov_for_consistency(self.target_consistency)

        # --- Key hold duration (seconds) ---
        # Hold should be a fraction of the IKI so it fits "inside" the interval.
        # Typical human hold is ~40-55% of the inter-key interval.
        self.hold_mean = self.base_delay * random.uniform(0.40, 0.55)
        self.hold_sigma = self.hold_mean * random.uniform(0.25, 0.40)
        self.hold_min = 0.025
        self.hold_max = self.base_delay * 1.5  # never exceed 1.5x the base IKI

        # --- Ex-Gaussian parameters (Issue #5) ---
        # tau controls the exponential tail (cognitive pauses)
        speed_factor = max(0.5, min(2.0, target_wpm / REFERENCE_WPM))
        self.exgauss_sigma = self.base_delay * random.uniform(0.08, 0.15)
        self.exgauss_tau = self.base_delay * random.uniform(0.05, 0.12)

        # --- Mistake rates (scale with speed) ---
        # Base rates are per-character trigger probabilities, modulated by
        # position, finger, row, and fatigue in ErrorEngine.should_make_error.
        # Typical real-human accuracy is 95-99%, so keep these conservative.
        # Error rate rises gently with speed up to ~100 WPM, then plateaus —
        # fast typists are skilled, not just fast-but-sloppy.
        error_factor = 0.8 + 0.2 * min(1.0, target_wpm / 100)  # caps at 1.0
        self.typo_chance = 0.018 * error_factor
        self.leave_mistake_chance = random.uniform(0.08, 0.15)

        # Error type distribution weights (used by ErrorEngine.get_error_type).
        # These are relative weights, not probabilities — they get normalized.
        # Speed affects distribution: faster typists make more transpositions
        # and skips (motor coordination errors) vs. adjacent key hits.
        self.error_weights = {
            "adjacent":   0.45,
            "transpose":  0.15 + 0.05 * speed_factor,   # more at high speed
            "confusion":  0.15,
            "double_tap": 0.10 + 0.02 * speed_factor,   # more at high speed
            "skip":       0.06 + 0.02 * speed_factor,   # more at high speed
        }

        # --- Delayed error detection (Issue #13) ---
        self.delayed_notice_chance = 0.30  # 30% of errors noticed late
        self.delayed_notice_chars = (1, 3)  # type 1-3 more chars before noticing
        self.over_backspace_chance = 0.12   # 12% chance of one extra backspace

        # --- Word boundary timing ---
        self.word_start_extra = (1.05, 1.25)   # cognitive pause for first char
        self.space_gap_range = (0.75, 1.30)     # space IKI relative to base

        # --- Thinking pauses ---
        self.think_pause_chance = 0.04
        self.think_pause_range = (2.0, 5.0)

        # --- Warm-up (Issue #8E: noisy warmup) ---
        self.warmup_words = random.randint(2, 5)
        self.warmup_slowdown = random.uniform(1.10, 1.30)

        # --- Fatigue ---
        self.fatigue_max = random.uniform(1.10, 1.30)
        self.fatigue_onset_words = random.randint(40, 70)

        # --- Burst typing (motor chunks, Issue #8) ---
        self.burst_max_len = 4
        self.burst_speedup = random.uniform(0.72, 0.85)
        self.chunk_speedup = random.uniform(0.62, 0.78)  # even faster for known chunks

        # --- Correction reaction ---
        self.correction_react = (0.10, 0.35)
        self.backspace_delay = (0.03, 0.09)

        # --- Key overlap (rollover) ---
        self.overlap_chance = min(0.40, target_wpm / 500)
        self.overlap_time = (0.005, 0.035)

        # --- AR(1) autocorrelation (Issue #6) ---
        self.ar1_phi = random.uniform(0.10, 0.30)  # momentum coefficient

        # --- Rhythmic periodicity (Issue #15) ---
        self.rhythm_amplitude = random.uniform(0.02, 0.05)
        self.rhythm_period = random.uniform(12, 25)  # chars per cycle (~4-6 Hz at 120wpm)

        # --- Sigmoid speed curve (Issue #16) ---
        self.flow_accel = random.uniform(0.92, 0.97)   # peak speed multiplier (mid-test)
        self.flow_decel = random.uniform(1.02, 1.08)    # end-of-test slowdown

        # --- Word difficulty pause scaling (Issue #10) ---
        self.difficulty_pause_scale = random.uniform(0.3, 0.8)

        # --- Issue #17: bigram speeds regenerated per profile ---
        self.bigram_speeds = _generate_bigram_speeds()


def safe_sleep(seconds: float):
    """Sleep with platform-aware minimum."""
    time.sleep(max(MIN_SLEEP, seconds))


# ===========================================================================
#  Advanced Keystroke Dynamics Engine
#  Issues #5, #6, #7, #8, #9, #15, #16
# ===========================================================================

class KeystrokeDynamicsEngine:
    """Generates keystroke timing that passes MonkeyType's anti-cheat analysis.

    Features:
    1. Per-finger timing (pinky slower than index)
    2. Row distance penalties
    3. Same-finger vs different-finger transitions
    4. Hand alternation bonuses
    5. Bigram-specific speeds (regenerated per-round, with per-occurrence noise)
    6. Ex-Gaussian distribution for realistic right-skewed timing
    7. AR(1) serial autocorrelation for rhythmic momentum
    8. Correlated keySpacing/keyDuration
    9. Log-normal key hold durations
    10. Motor chunking for common short words
    11. Word difficulty-aware pre-word pauses
    12. Sigmoid speed curve across the test
    13. Rhythmic periodicity
    14. Warm-up with noise, fatigue
    """

    def __init__(self, profile: HumanProfile, total_words: int = 100):
        self.profile = profile
        self.total_words = total_words
        self.key_spacings: list[float] = []
        self.key_durations: list[float] = []
        self.prev_char: str | None = None
        self.prev_finger: int | None = None
        self.prev_row: int | None = None
        self.word_count = 0
        self.char_in_word = 0
        self.total_chars = 0
        self._current_word_len = 0   # Issue #3E: initialized properly
        self._current_word = ""
        self._ar1_residual = 0.0     # Issue #6: AR(1) state
        self._last_delay = None      # Issue #7: for spacing-duration correlation

    def compute_delay(self, char: str) -> float:
        """Compute inter-key delay with all anatomical, cognitive, and
        statistical realism features."""
        p = self.profile
        base = p.base_delay

        finger = get_finger(char)
        row = get_row(char)

        # 1. Finger speed
        base *= FINGER_SPEED.get(finger, 1.0)

        # 2. Row distance penalty
        if self.prev_row is not None:
            dist = row_distance(self.prev_row, row)
            if dist > 0:
                base *= 1.0 + dist * random.uniform(0.06, 0.14)

        # 3-7. Finger/key relationship penalties (mutually exclusive,
        #       most-specific wins to avoid compounding).
        is_same_key = (self.prev_char and self.prev_char.lower() == char.lower())
        bigram = (self.prev_char + char).lower() if self.prev_char else ""
        is_same_finger_bigram = bigram in SAME_FINGER_PAIRS
        is_same_finger = (self.prev_finger is not None
                          and finger == self.prev_finger and finger != 8)

        if is_same_key:
            # 7. Same key repeat — strongest penalty (subsumes same-finger)
            finger_mult = FINGER_HOLD.get(finger, 1.0)
            base *= random.uniform(1.25, 1.45) * (finger_mult ** 0.3)
        elif is_same_finger_bigram:
            # 6b. Same-finger bigram pair (subsumes generic same-finger)
            base *= random.uniform(1.18, 1.38)
        elif is_same_finger:
            # 3. Generic same-finger penalty
            base *= random.uniform(1.12, 1.30)
        elif (self.prev_finger is not None
              and not same_hand(finger, self.prev_finger)):
            # 4. Hand alternation bonus
            base *= random.uniform(0.85, 0.95)
        elif (self.prev_finger is not None
              and same_hand(finger, self.prev_finger)):
            # 5. Same hand, different finger
            base *= random.uniform(0.96, 1.08)

        # 6a. Bigram-specific speed (Issue #17: per-occurrence noise)
        #     Applied independently — this is a speed lookup, not a penalty.
        if self.prev_char:
            bg_speed = p.bigram_speeds.get(bigram)
            if bg_speed is not None:
                base *= bg_speed * random.uniform(0.93, 1.07)

        # 8. Word start: cognitive pause + word difficulty (Issue #10)
        if self.char_in_word == 0:
            base *= random.uniform(*p.word_start_extra)
            # Difficulty-aware pause for upcoming word
            diff = word_difficulty(self._current_word)
            base *= 1.0 + diff * p.difficulty_pause_scale * random.uniform(0.3, 0.7)

        # 9. Warm-up with noise (Issue #8E: stochastic warmup)
        if self.word_count < p.warmup_words:
            warmup_progress = self.word_count / p.warmup_words
            smooth = p.warmup_slowdown - (p.warmup_slowdown - 1.0) * warmup_progress
            noise = random.gauss(0, 0.08)  # stochastic jumps
            base *= max(1.0, smooth + noise)

        # 10. Fatigue
        if self.word_count > p.fatigue_onset_words:
            fatigue_progress = min(1.0, (self.word_count - p.fatigue_onset_words) / 60)
            base *= 1.0 + (p.fatigue_max - 1.0) * fatigue_progress

        # 11. Motor chunking (Issue #8: common words as single units)
        if self._current_word.lower() in MOTOR_CHUNKS and self.char_in_word > 0:
            base *= p.chunk_speedup
        elif self._current_word_len <= p.burst_max_len:
            base *= p.burst_speedup

        # 12. Sigmoid speed curve across test (Issue #16)
        if self.total_words > 0:
            test_progress = self.word_count / max(1, self.total_words)
            # Sigmoid: slow start -> fast middle -> slow end
            # Using logistic-like shape
            sigmoid = 1.0 / (1.0 + math.exp(-12 * (test_progress - 0.25)))
            end_decel = 1.0 + (p.flow_decel - 1.0) * max(0, (test_progress - 0.85)) / 0.15
            flow_mult = 1.0 - (1.0 - p.flow_accel) * sigmoid
            base *= flow_mult * end_decel

        # 13. Rhythmic periodicity (Issue #15: sinusoidal modulation)
        if p.rhythm_period > 0:
            phase = 2 * math.pi * self.total_chars / p.rhythm_period
            base *= 1.0 + p.rhythm_amplitude * math.sin(phase)

        # 14. Ex-Gaussian sampling (Issue #5: replaces discrete mixture)
        # Scale noise relative to current base, not profile base_delay,
        # so CoV stays stable regardless of per-character multipliers.
        sigma = base * (p.exgauss_sigma / p.base_delay)
        tau = base * (p.exgauss_tau / p.base_delay)
        delay = exgaussian(base, sigma, tau)

        # 15. AR(1) serial autocorrelation (Issue #6)
        innovation = delay - base
        self._ar1_residual = p.ar1_phi * self._ar1_residual + innovation
        delay = base + self._ar1_residual

        # Clamp: never exceed 2.0x base_delay (prevents outlier spikes
        # that destroy consistency)
        delay = max(MIN_SLEEP, min(delay, p.base_delay * 2.0))

        # Record for consistency tracking
        self.key_spacings.append(delay * 1000)  # ms
        self._last_delay = delay

        # Update state
        self.prev_char = char
        self.prev_finger = finger
        self.prev_row = row
        self.char_in_word += 1
        self.total_chars += 1

        log.debug("char='%s' finger=%d row=%d delay=%.1fms",
                  char, finger, row, delay * 1000)

        return delay

    def compute_hold(self, char: str) -> float:
        """Compute key hold duration.

        Issue #7:  Correlated with keySpacing (faster typing = shorter holds).
        Issue #9:  Log-normal distribution for realistic right-skewed shape.
        """
        p = self.profile
        finger = get_finger(char)

        # Base hold with finger modifier
        finger_mult = FINGER_HOLD.get(finger, 1.0)
        base_hold = p.hold_mean * finger_mult

        # Issue #9: log-normal distribution (right-skewed, always positive)
        mu_ln = math.log(base_hold) - 0.5 * (p.hold_sigma / base_hold) ** 2
        sigma_ln = p.hold_sigma / base_hold
        hold = random.lognormvariate(mu_ln, max(0.05, sigma_ln))

        # Home row bonus / number row penalty
        row = get_row(char)
        if row == 2:
            hold *= random.uniform(0.88, 0.97)
        elif row == 0:
            hold *= random.uniform(1.05, 1.20)

        # Space bar: consistent, shorter
        if char == ' ':
            hold = random.lognormvariate(
                math.log(p.hold_mean * 0.80), max(0.05, p.hold_sigma * 0.5 / base_hold))

        # Issue #7: correlate with spacing (faster typing = shorter holds)
        if self._last_delay is not None:
            speed_ratio = self._last_delay / p.base_delay
            hold *= 0.4 + 0.6 * min(1.5, speed_ratio)

        hold = max(p.hold_min, min(hold, p.hold_max))

        # Record
        self.key_durations.append(hold * 1000)  # ms

        return hold

    def should_overlap(self) -> bool:
        return random.random() < self.profile.overlap_chance

    def overlap_duration(self) -> float:
        return random.uniform(*self.profile.overlap_time)

    def word_boundary(self):
        self.char_in_word = 0
        self.word_count += 1

    def set_word_context(self, word: str):
        """Set context for the current word."""
        self._current_word = word
        self._current_word_len = len(word)

    def get_consistency_report(self) -> dict:
        spacing_cons = (compute_consistency(self.key_spacings)
                        if self.key_spacings else 0)
        duration_cons = (compute_consistency(self.key_durations)
                         if self.key_durations else 0)
        return {
            "keyConsistency": round(spacing_cons, 2),
            "holdConsistency": round(duration_cons, 2),
            "targetConsistency": round(self.profile.target_consistency, 2),
            "totalKeystrokes": self.total_chars,
        }


# ===========================================================================
#  Context-Aware Error Engine  (Issues #13, #14)
# ===========================================================================

# Issue #7B expanded: 100+ common typo patterns
COMMON_TYPOS = {
    'the': ['teh', 'hte', 'th', 'tje', 'tue'],
    'and': ['adn', 'nad', 'anf', 'ans'],
    'that': ['taht', 'htat', 'tath', 'thta'],
    'have': ['ahve', 'hvae', 'hav', 'haev'],
    'with': ['wiht', 'wtih', 'wth', 'iwth'],
    'this': ['tihs', 'thsi', 'htis', 'tis'],
    'from': ['form', 'fomr', 'fro', 'rfom'],
    'they': ['tehy', 'thye', 'htey', 'tey'],
    'been': ['eben', 'bene', 'ben', 'beem'],
    'their': ['thier', 'tehir', 'theri', 'ther'],
    'which': ['whcih', 'whihc', 'wich', 'wihch'],
    'would': ['woudl', 'wuold', 'woud', 'owuld'],
    'there': ['tehre', 'htere', 'ther', 'theer'],
    'about': ['abotu', 'abuot', 'abut', 'baout'],
    'just': ['jsut', 'just', 'juts', 'jusr'],
    'like': ['liek', 'likr', 'lik', 'lkie'],
    'what': ['waht', 'wath', 'whta', 'wat'],
    'when': ['wehn', 'whn', 'whne', 'hwen'],
    'your': ['yuor', 'yoru', 'yor', 'yoir'],
    'some': ['soem', 'smoe', 'soe', 'osme'],
    'them': ['tehm', 'thme', 'tem', 'htem'],
    'than': ['tahn', 'htan', 'thn', 'tahn'],
    'other': ['ohter', 'otehr', 'oter', 'toher'],
    'time': ['tiem', 'tmie', 'itme', 'tim'],
    'very': ['vrey', 'vey', 'ver', 'evry'],
    'also': ['aslo', 'laso', 'als', 'aldo'],
    'make': ['maek', 'mkae', 'amke', 'mak'],
    'know': ['knwo', 'konw', 'kno', 'nkow'],
    'people': ['peopel', 'poeple', 'peolpe', 'peopl'],
    'because': ['becasue', 'becuase', 'becaus', 'beacuse'],
    'could': ['cuold', 'coudl', 'coud', 'colud'],
    'should': ['shoudl', 'shuold', 'shoud', 'sholud'],
    'think': ['thnik', 'thnk', 'htink', 'thiink'],
    'after': ['aftre', 'atfer', 'afer', 'aftr'],
    'work': ['wokr', 'wrk', 'owrk', 'wrok'],
    'first': ['frist', 'fisrt', 'firt', 'firsr'],
    'well': ['wlel', 'wel', 'weel', 'wll'],
    'even': ['eevn', 'evne', 'ven', 'eevn'],
    'good': ['godo', 'god', 'goood', 'ogod'],
    'much': ['mcuh', 'muhc', 'mch', 'umch'],
    'where': ['wehre', 'wheer', 'wher', 'hwere'],
    'right': ['rihgt', 'rigth', 'rgiht', 'riight'],
    'still': ['sitll', 'stil', 'stll', 'tsill'],
    'between': ['bewteen', 'betwen', 'betwene', 'bteween'],
    'before': ['beofre', 'befroe', 'befor', 'bfore'],
    'through': ['thorugh', 'throught', 'throuhg', 'trhough'],
    'great': ['gerat', 'graet', 'gret', 'grear'],
    'being': ['bieng', 'beng', 'beign', 'beig'],
    'world': ['wrold', 'wolrd', 'worl', 'wrld'],
    'these': ['thees', 'tehse', 'thse', 'htese'],
    'those': ['thoes', 'htose', 'thoese', 'thsoe'],
    'does': ['dose', 'deos', 'doe', 'odes'],
    'going': ['giong', 'goign', 'gong', 'goig'],
    'take': ['taek', 'tkae', 'tka', 'atke'],
    'want': ['wnat', 'watn', 'wnt', 'awnt'],
    'same': ['saem', 'smae', 'sam', 'asme'],
    'each': ['eahc', 'aech', 'ech', 'eahc'],
    'come': ['coem', 'cmoe', 'com', 'ocme'],
    'many': ['mnay', 'mny', 'amny', 'mayn'],
    'then': ['tehn', 'thn', 'thne', 'hten'],
    'only': ['olny', 'onyl', 'noly', 'onl'],
    'over': ['oevr', 'voer', 'ovr', 'ovre'],
    'more': ['moer', 'mroe', 'mor', 'omre'],
    'such': ['scuh', 'shcu', 'suhc', 'uscb'],
    'into': ['itno', 'inot', 'nito', 'ino'],
    'year': ['yaer', 'yer', 'yera', 'eyar'],
    'most': ['msot', 'mos', 'omst', 'mots'],
    'find': ['fnd', 'fidn', 'fnid', 'ifnd'],
    'here': ['heer', 'hre', 'ehre', 'herr'],
    'thing': ['thign', 'thnig', 'ting', 'htign'],
    'long': ['lnog', 'logn', 'lon', 'olng'],
    'look': ['loko', 'lok', 'loook', 'olok'],
    'down': ['dwon', 'donw', 'don', 'odwn'],
    'life': ['lief', 'lfie', 'lif', 'ilfe'],
    'never': ['nver', 'neevr', 'nevr', 'enver'],
    'need': ['nede', 'ned', 'nee', 'ened'],
    'will': ['wll', 'iwll', 'wil', 'wlil'],
    'home': ['hmoe', 'hom', 'hoem', 'ohme'],
    'back': ['bakc', 'bck', 'abck', 'bcak'],
    'give': ['gvie', 'giev', 'giv', 'igve'],
    'help': ['hlep', 'hep', 'ehlp', 'hepl'],
    'hand': ['hnad', 'hnd', 'ahnd', 'hadn'],
    'high': ['hgih', 'hih', 'ihgh', 'hig'],
    'keep': ['kepe', 'kep', 'keeep', 'ekep'],
    'last': ['lsat', 'las', 'alst', 'lasr'],
    'name': ['naem', 'nmae', 'nam', 'anme'],
    'play': ['paly', 'ply', 'pla', 'lpay'],
    'small': ['smlal', 'smal', 'smll', 'samll'],
    'every': ['eevry', 'evrey', 'evry', 'evey'],
    'again': ['agian', 'agin', 'aagin', 'gaain'],
    'change': ['chnage', 'chagne', 'chang', 'cahnge'],
    'point': ['piont', 'ponit', 'pint', 'poin'],
    'place': ['palce', 'plcae', 'plac', 'place'],
    'under': ['uner', 'udner', 'undr', 'nuder'],
    'while': ['whiel', 'whlie', 'whil', 'hwile'],
}

CONFUSION_PAIRS = {
    'b': 'v', 'v': 'b', 'n': 'm', 'm': 'n',
    'd': 'f', 'f': 'd', 'g': 'h', 'h': 'g',
    'i': 'o', 'o': 'i', 'e': 'r', 'r': 'e',
    'c': 'x', 'x': 'c',
}


class ErrorEngine:
    """Context-aware error generation with position weighting and delayed detection.

    Issue #13: delayed error detection (type past error then backspace)
    Issue #14: position-weighted error probability
    """

    def __init__(self, profile: HumanProfile):
        self.profile = profile

    def should_make_error(self, char: str, char_index: int, word: str,
                          word_index: int, prev_char: str | None = None) -> bool:
        """Determine if an error should occur at this position.

        Issue #14: errors weighted by position (near-zero on first char,
        peak at positions 3-5, declining after).
        """
        p = self.profile
        base_chance = p.typo_chance

        # Issue #14: position weighting within word
        # Near-zero on first char, peak at 3-5, declining after
        if char_index == 0:
            base_chance *= 0.05  # almost never error on first char
        elif char_index <= 2:
            base_chance *= 0.5
        elif char_index <= 5:
            base_chance *= 1.5   # peak error zone
        else:
            base_chance *= 1.0

        # Pinky keys: higher error rate
        finger = get_finger(char)
        if finger in (0, 7):
            base_chance *= 1.5

        # Number row: higher error rate
        if get_row(char) == 0:
            base_chance *= 1.8

        # Long words: increase mid-word
        if len(word) > 6 and char_index > 3:
            base_chance *= 1.2

        # Fatigue over time
        if word_index > 40:
            base_chance *= 1.0 + min(0.3, (word_index - 40) / 200)

        # Issue #14 addition: difficult transitions increase error rate
        if prev_char:
            pf = get_finger(prev_char)
            pr = get_row(prev_char)
            # Same finger, different row = hard transition
            if pf == finger and pf != 8 and pr != get_row(char):
                base_chance *= 1.6

        return random.random() < base_chance

    def get_error_type(self, char: str, char_index: int, word: str) -> str:
        """Choose what type of error to make using profile-defined weights."""
        # Common whole-word typo (higher trigger rate with expanded dictionary).
        # Reduced at high WPM because it's very expensive (type wrong word +
        # backspace all + retype correct word) and fast typists rarely make
        # whole-word substitutions.
        if char_index == 0 and word.lower() in COMMON_TYPOS:
            wpm = self.profile.target_wpm
            common_typo_rate = 0.06 if wpm <= 100 else max(0.01, 0.06 - 0.001 * (wpm - 100))
            if random.random() < common_typo_rate:
                return "common_typo"

        # Use profile's error type weights (normalized to probabilities)
        weights = self.profile.error_weights
        types = list(weights.keys())
        vals = list(weights.values())
        total = sum(vals)
        # Cumulative distribution
        r = random.random() * total
        cumulative = 0.0
        for t, w in zip(types, vals):
            cumulative += w
            if r < cumulative:
                return t
        return types[-1]  # fallback

    def get_adjacent_typo(self, char: str) -> str:
        if char.lower() in ADJACENT_KEYS:
            neighbors = ADJACENT_KEYS[char.lower()]
            wrong = random.choice(neighbors)
            return wrong.upper() if char.isupper() else wrong
        # Fallback: pick a random nearby lowercase letter
        fallback = 'abcdefghijklmnopqrstuvwxyz'
        return random.choice(fallback)

    def get_confusion_typo(self, char: str) -> str:
        if char.lower() in CONFUSION_PAIRS:
            wrong = CONFUSION_PAIRS[char.lower()]
            return wrong.upper() if char.isupper() else wrong
        return self.get_adjacent_typo(char)

    def should_correct(self) -> bool:
        return random.random() > self.profile.leave_mistake_chance

    def should_delay_notice(self) -> bool:
        """Issue #13: should the error go unnoticed for a few more characters?"""
        return random.random() < self.profile.delayed_notice_chance

    def delayed_chars_count(self) -> int:
        """How many chars to type before noticing the error."""
        return random.randint(*self.profile.delayed_notice_chars)

    def should_over_backspace(self) -> bool:
        """Issue #13: chance of backspacing one too many characters."""
        return random.random() < self.profile.over_backspace_chance


# ===========================================================================
#  Mouse Behavior Simulation
# ===========================================================================

def simulate_mouse_idle(driver):
    """Subtle mouse micro-movements."""
    try:
        vw = driver.execute_script("return window.innerWidth;")
        vh = driver.execute_script("return window.innerHeight;")
        base_x = random.randint(int(vw * 0.6), int(vw * 0.85))
        base_y = random.randint(int(vh * 0.5), int(vh * 0.8))
        for _ in range(random.randint(1, 3)):
            dx = random.gauss(0, 3)
            dy = random.gauss(0, 3)
            cdp_mouse_move(driver, base_x + dx, base_y + dy)
            time.sleep(random.uniform(0.05, 0.2))
    except Exception as exc:
        log.debug("Mouse idle simulation failed: %s", exc)


# ===========================================================================
#  Main Typing Engine — orchestrates all subsystems
#  Issues #4, #13, #18
# ===========================================================================

def type_word_advanced(driver, word: str, engine: KeystrokeDynamicsEngine,
                       error_engine: ErrorEngine, word_index: int,
                       is_last_word: bool, overlap_state: OverlapState):
    """Type a single word with full human simulation.

    Issue #4:  No trailing space on last word.
    Issue #13: Delayed error detection.
    Issue #18: True key overlap via OverlapState.
    """
    chars = list(word)
    engine.word_boundary()
    engine.set_word_context(word)
    i = 0
    # Track previous hold so we can subtract it from the IKI budget.
    # delay = desired keyDown-to-keyDown interval; prev_hold was already
    # slept inside cdp_type_char, so the pre-key sleep = delay - prev_hold.
    prev_hold = 0.0

    while i < len(chars):
        ch = chars[i]

        # --- Check for errors ---
        prev_ch = engine.prev_char
        if error_engine.should_make_error(ch, i, word, word_index,
                                          prev_char=prev_ch):
            error_type = error_engine.get_error_type(ch, i, word)

            if error_type == "common_typo" and i == 0:
                typo_word = random.choice(COMMON_TYPOS[word.lower()])
                # Release any held key before error handling
                overlap_state.release_held(driver)
                prev_hold = 0.0
                for tc in typo_word:
                    delay = engine.compute_delay(tc)
                    hold = engine.compute_hold(tc)
                    safe_sleep(max(MIN_SLEEP, delay - prev_hold))
                    cdp_type_char(driver, tc, hold)
                    prev_hold = hold
                if error_engine.should_correct():
                    safe_sleep(random.uniform(*engine.profile.correction_react))
                    prev_hold = 0.0
                    # Issue #13: possible over-backspace
                    bs_count = len(typo_word)
                    if error_engine.should_over_backspace():
                        bs_count += 1
                    for _ in range(bs_count):
                        h = engine.compute_hold('a')
                        cdp_backspace(driver, h)
                        safe_sleep(random.uniform(*engine.profile.backspace_delay))
                    # If over-backspaced, retype the deleted char from before
                    if bs_count > len(typo_word):
                        # we deleted one char too many; nothing before this word though
                        pass
                    # Reset engine state for clean retype
                    engine.char_in_word = 0
                    prev_hold = 0.0
                    for cc in chars:
                        delay = engine.compute_delay(cc)
                        hold = engine.compute_hold(cc)
                        safe_sleep(max(MIN_SLEEP, delay - prev_hold))
                        cdp_type_char(driver, cc, hold)
                        prev_hold = hold
                i = len(chars)
                continue

            elif error_type == "transpose" and i < len(chars) - 1:
                overlap_state.release_held(driver)
                # Type next char first, then current (transposed)
                delay1 = engine.compute_delay(chars[i + 1])
                hold1 = engine.compute_hold(chars[i + 1])
                safe_sleep(max(MIN_SLEEP, delay1 - prev_hold))
                cdp_type_char(driver, chars[i + 1], hold1)
                delay2 = engine.compute_delay(chars[i])
                hold2 = engine.compute_hold(chars[i])
                safe_sleep(max(MIN_SLEEP, delay2 - hold1))
                cdp_type_char(driver, chars[i], hold2)
                prev_hold = hold2

                if error_engine.should_correct():
                    # Issue #13: delayed notice — might type 1-2 more chars first
                    extra_typed = 0
                    if error_engine.should_delay_notice() and i + 2 < len(chars):
                        n_extra = min(error_engine.delayed_chars_count(),
                                      len(chars) - i - 2)
                        for k in range(n_extra):
                            ci = i + 2 + k
                            d = engine.compute_delay(chars[ci])
                            h = engine.compute_hold(chars[ci])
                            safe_sleep(max(MIN_SLEEP, d - prev_hold))
                            cdp_type_char(driver, chars[ci], h)
                            prev_hold = h
                            extra_typed += 1

                    safe_sleep(random.uniform(*engine.profile.correction_react))
                    prev_hold = 0.0
                    # Backspace all: extra + 2 transposed chars
                    total_bs = 2 + extra_typed
                    if error_engine.should_over_backspace():
                        total_bs += 1
                    for _ in range(total_bs):
                        h = engine.compute_hold('a')
                        cdp_backspace(driver, h)
                        safe_sleep(random.uniform(*engine.profile.backspace_delay))
                    # Retype correctly
                    prev_hold = 0.0
                    start = i - 1 if total_bs > 2 + extra_typed else i
                    start = max(0, start)
                    for ci in range(start, i + 2 + extra_typed):
                        if ci < len(chars):
                            d = engine.compute_delay(chars[ci])
                            h = engine.compute_hold(chars[ci])
                            safe_sleep(max(MIN_SLEEP, d - prev_hold))
                            cdp_type_char(driver, chars[ci], h)
                            prev_hold = h
                    i = i + 2 + extra_typed
                else:
                    i += 2
                continue

            elif error_type == "adjacent":
                overlap_state.release_held(driver)
                wrong = error_engine.get_adjacent_typo(ch)
                delay = engine.compute_delay(wrong)
                hold = engine.compute_hold(wrong)
                safe_sleep(max(MIN_SLEEP, delay - prev_hold))
                cdp_type_char(driver, wrong, hold)
                prev_hold = hold

                if error_engine.should_correct():
                    extra_typed = 0
                    # Issue #13: delayed notice
                    if error_engine.should_delay_notice() and i + 1 < len(chars):
                        n_extra = min(error_engine.delayed_chars_count(),
                                      len(chars) - i - 1)
                        for k in range(n_extra):
                            ci = i + 1 + k
                            d = engine.compute_delay(chars[ci])
                            h = engine.compute_hold(chars[ci])
                            safe_sleep(max(MIN_SLEEP, d - prev_hold))
                            cdp_type_char(driver, chars[ci], h)
                            prev_hold = h
                            extra_typed += 1

                    safe_sleep(random.uniform(*engine.profile.correction_react))
                    prev_hold = 0.0
                    total_bs = 1 + extra_typed
                    if error_engine.should_over_backspace():
                        total_bs += 1
                    for _ in range(total_bs):
                        h = engine.compute_hold('a')
                        cdp_backspace(driver, h)
                        safe_sleep(random.uniform(*engine.profile.backspace_delay))
                    # Retype correct chars
                    prev_hold = 0.0
                    start = i - 1 if total_bs > 1 + extra_typed else i
                    start = max(0, start)
                    for ci in range(start, i + 1 + extra_typed):
                        if ci < len(chars):
                            d = engine.compute_delay(chars[ci])
                            h = engine.compute_hold(chars[ci])
                            safe_sleep(max(MIN_SLEEP, d - prev_hold))
                            cdp_type_char(driver, chars[ci], h)
                            prev_hold = h
                    i = i + 1 + extra_typed
                else:
                    i += 1
                continue

            elif error_type == "confusion":
                overlap_state.release_held(driver)
                wrong = error_engine.get_confusion_typo(ch)
                delay = engine.compute_delay(wrong)
                hold = engine.compute_hold(wrong)
                safe_sleep(max(MIN_SLEEP, delay - prev_hold))
                cdp_type_char(driver, wrong, hold)
                if error_engine.should_correct():
                    safe_sleep(random.uniform(*engine.profile.correction_react))
                    h = engine.compute_hold('a')
                    cdp_backspace(driver, h)
                    safe_sleep(random.uniform(*engine.profile.backspace_delay))
                    hold = engine.compute_hold(ch)
                    cdp_type_char(driver, ch, hold)
                    prev_hold = hold
                else:
                    prev_hold = hold
                i += 1
                continue

            elif error_type == "double_tap":
                overlap_state.release_held(driver)
                delay = engine.compute_delay(ch)
                hold = engine.compute_hold(ch)
                safe_sleep(max(MIN_SLEEP, delay - prev_hold))
                cdp_type_char(driver, ch, hold)
                # Accidental second tap (finger-dependent gap)
                finger_mult = FINGER_HOLD.get(get_finger(ch), 1.0)
                gap = max(MIN_SLEEP,
                          random.gauss(engine.profile.base_delay * 0.25 * finger_mult, 0.015))
                safe_sleep(gap)
                hold2 = engine.compute_hold(ch)
                cdp_type_char(driver, ch, hold2)
                if error_engine.should_correct():
                    safe_sleep(random.uniform(*engine.profile.correction_react))
                    cdp_backspace(driver, engine.compute_hold('a'))
                    prev_hold = 0.0
                else:
                    prev_hold = hold2
                i += 1
                continue

            elif error_type == "skip":
                # Skip this character (update engine state properly)
                engine.prev_char = ch
                engine.prev_finger = get_finger(ch)
                engine.prev_row = get_row(ch)
                engine.char_in_word += 1
                i += 1
                continue

        # --- Normal keystroke ---
        delay = engine.compute_delay(ch)
        hold = engine.compute_hold(ch)

        # Subtract previous hold + CDP overhead from the IKI budget.
        # Each cdp_type_char does 2 CDP calls (keyDown + keyUp), and the
        # previous char's CDP overhead was not accounted for in prev_hold.
        cdp_cost = 2 * CDP_OVERHEAD
        iki_sleep = max(MIN_SLEEP, delay - prev_hold - cdp_cost)

        # Issue #18: true key overlap (rollover)
        if engine.should_overlap() and engine.prev_char and i > 0:
            ov_time = engine.overlap_duration()
            effective_delay = max(MIN_SLEEP, iki_sleep - ov_time)
            safe_sleep(effective_delay)
            overlap_state.type_with_overlap(driver, ch, hold, ov_time)
        else:
            safe_sleep(iki_sleep)
            # Release any previously held key before normal typing
            overlap_state.release_held(driver)
            cdp_type_char(driver, ch, hold)

        prev_hold = hold
        i += 1

    # Release any held key before space
    overlap_state.release_held(driver)

    # Issue #4: No space after the last word
    if not is_last_word:
        # Space IKI: scale by space_gap_range, subtract prev hold + CDP cost
        space_delay = engine.profile.base_delay * random.uniform(
            *engine.profile.space_gap_range)
        safe_sleep(max(MIN_SLEEP, space_delay - prev_hold - 2 * CDP_OVERHEAD))
        space_hold = engine.compute_hold(' ')
        cdp_type_char(driver, ' ', space_hold)

        # Occasional thinking pause
        if random.random() < engine.profile.think_pause_chance:
            think = engine.profile.base_delay * random.uniform(
                *engine.profile.think_pause_range)
            safe_sleep(think)


# ===========================================================================
#  Browser Management
# ===========================================================================

def find_chrome_binary() -> str | None:
    system = platform.system()
    candidates = []
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        pf86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        candidates = [
            os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(pf, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join(local, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
    elif system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]

    for name in [
        "google-chrome-stable", "google-chrome", "chromium-browser",
        "chromium", "brave-browser", "brave", "microsoft-edge-stable",
        "microsoft-edge",
    ]:
        found = shutil.which(name)
        if found:
            candidates.insert(0, found)

    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


# Realistic user-agent strings (Issue #11)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def launch_browser():
    """Launch Chrome using the user's existing profile.

    Strategy:
    1. Try to attach to a running Chrome with --remote-debugging-port=9222
    2. If that fails, launch Chrome ourselves with the user's profile directory
       and remote debugging enabled.

    The user's existing Chrome must be CLOSED for option 2, because Chrome
    locks the profile directory (SingletonLock).
    """
    DEBUGGER_ADDRESS = "127.0.0.1:9222"
    CHROME_USER_DATA = os.path.expanduser("~/.config/google-chrome")
    CHROME_PROFILE = "Profile 3"  # "Abdullah Farooqi" profile

    # --- Try attaching to running Chrome first ---
    try:
        import urllib.request
        resp = urllib.request.urlopen(f"http://{DEBUGGER_ADDRESS}/json/version",
                                      timeout=2)
        resp.close()
        print(f"  Found running Chrome on {DEBUGGER_ADDRESS}")

        options = Options()
        options.debugger_address = DEBUGGER_ADDRESS

        driver = webdriver.Chrome(options=options)

        # Open a new tab and switch to it BEFORE applying stealth/navigating
        driver.switch_to.new_window("tab")
        time.sleep(0.3)

        # Apply stealth patches on the new tab context
        apply_stealth(driver)
        try:
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })
        except Exception as exc:
            log.warning("Could not patch webdriver at runtime: %s", exc)

        # Navigate to MonkeyType in this new tab
        driver.get(MONKEYTYPE_URL)
        print("  MonkeyType loaded (new tab in your Chrome)!")

        _verify_stealth(driver)
        return driver

    except Exception as e:
        log.debug("Could not attach to running Chrome: %s", e)

    # --- Launch Chrome with user's profile ---
    print("  No running Chrome with debugging port found.")
    print("  Launching Chrome with your profile...")

    chrome_binary = find_chrome_binary()

    options = Options()
    if chrome_binary:
        options.binary_location = chrome_binary

    # Use the user's actual Chrome profile
    options.add_argument(f"--user-data-dir={CHROME_USER_DATA}")
    options.add_argument(f"--profile-directory={CHROME_PROFILE}")
    options.add_argument(f"--remote-debugging-port=9222")

    options.add_experimental_option("detach", True)
    options.add_experimental_option("excludeSwitches",
                                    ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    # Stealth args
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    # Issue #11: WebRTC IP leak prevention at browser level
    options.add_argument("--disable-webrtc-hw-encoding")
    options.add_argument("--enforce-webrtc-ip-permission-check")

    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        err_msg = str(e)
        if "user data directory is already in use" in err_msg or "SingletonLock" in err_msg:
            print(f"\n  ERROR: Your Chrome profile is locked by another Chrome instance.")
            print(f"  Close ALL Chrome windows first, then run the bot again.")
            print(f"  (Or run: pkill -f chrome && sleep 2)")
        else:
            print(f"\nERROR: Could not launch Chrome.\n{e}")
            print("\nMake sure Google Chrome is installed.")
            system = platform.system()
            if system == "Windows":
                print("Download: https://www.google.com/chrome/")
            elif system == "Darwin":
                print("  brew install --cask google-chrome")
            else:
                print("  sudo apt install google-chrome-stable  (Debian/Ubuntu)")
                print("  sudo pacman -S google-chrome            (Arch)")
                print("  sudo dnf install google-chrome-stable   (Fedora)")
        _sys.exit(1)

    print(f"  Browser: Chrome ({CHROME_PROFILE})")

    # Apply stealth patches BEFORE navigating
    apply_stealth(driver)
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    except Exception as exc:
        log.warning("Could not patch webdriver at runtime: %s", exc)

    driver.get(MONKEYTYPE_URL)
    print("  MonkeyType loaded!")

    _verify_stealth(driver)
    return driver


def _verify_stealth(driver):
    """Check if stealth patches are working."""
    try:
        wd = driver.execute_script("return navigator.webdriver;")
        if wd:
            print("  WARNING: navigator.webdriver still true — stealth partial")
        else:
            print("  Stealth: OK (navigator.webdriver = undefined)")
    except Exception as exc:
        log.debug("Stealth verification failed: %s", exc)


def calibrate_cdp_overhead(driver, n: int = 20):
    """Measure average CDP call overhead by sending benign events.

    This lets us subtract the infrastructure latency from our sleep times
    so the actual inter-key intervals match the intended timing.
    """
    global CDP_OVERHEAD
    import time as _time
    times = []
    for _ in range(n):
        t0 = _time.perf_counter()
        try:
            driver.execute_cdp_cmd("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": "",
                "code": "",
                "windowsVirtualKeyCode": 0,
                "nativeVirtualKeyCode": 0,
            })
        except Exception:
            pass
        times.append(_time.perf_counter() - t0)

    if times:
        # Use median to avoid outlier spikes
        times.sort()
        median = times[len(times) // 2]
        CDP_OVERHEAD = median
        log.debug("CDP overhead calibrated: %.1fms (median of %d samples)",
                  median * 1000, n)


# ===========================================================================
#  MonkeyType Page Interaction
#  Issues #3, #20
# ===========================================================================

def wait_for_page_ready(driver, timeout: int = 20) -> bool:
    for _ in range(timeout):
        try:
            ready = driver.execute_script("""
                return document.querySelector('#words') !== null
                    && document.querySelector('#wordsInput') !== null;
            """)
            if ready:
                return True
        except Exception as exc:
            log.debug("Page ready check failed: %s", exc)
        time.sleep(1)
    return False


def dismiss_popups(driver):
    """Issue #20: dismiss cookie consent banners and other overlays."""
    try:
        driver.execute_script("""
            // Common cookie consent selectors
            var selectors = [
                '.fc-cta-consent',           // Funding Choices
                '#onetrust-accept-btn-handler', // OneTrust
                '.css-47sehv',                // Generic cookie button
                '[data-testid="cookie-policy-manage-cookies-accept"]',
                'button.accept-cookies',
                '.cookie-banner button',
                '#cookieConsent button',
                '.cc-btn.cc-dismiss',         // Cookie Consent plugin
                '.qc-cmp2-summary-buttons button:first-child',
            ];
            for (var s of selectors) {
                var el = document.querySelector(s);
                if (el && el.offsetParent !== null) {
                    el.click();
                    break;
                }
            }
            // Also dismiss any MonkeyType-specific notifications
            var notif = document.querySelector('.notification .close');
            if (notif) notif.click();
        """)
    except Exception as exc:
        log.debug("Popup dismissal failed: %s", exc)


def focus_typing_area(driver):
    """Focus the typing area via CDP mouse click + JS fallback."""
    try:
        rect = driver.execute_script("""
            var el = document.getElementById('wordsWrapper');
            if (!el) return null;
            var r = el.getBoundingClientRect();
            return {x: r.x + r.width/2, y: r.y + r.height/2,
                    w: r.width, h: r.height};
        """)
        if rect:
            x = rect['x'] + random.uniform(-rect['w'] * 0.2, rect['w'] * 0.2)
            y = rect['y'] + random.uniform(-rect['h'] * 0.15, rect['h'] * 0.15)
            cdp_mouse_click(driver, x, y)
            time.sleep(0.15)
    except Exception as exc:
        log.debug("CDP focus click failed: %s", exc)

    # Fallback: JS click + focus
    try:
        driver.execute_script("""
            var wrapper = document.getElementById('wordsWrapper');
            if (wrapper) wrapper.click();
            var input = document.getElementById('wordsInput');
            if (input) input.focus();
        """)
    except Exception as exc:
        log.debug("JS focus fallback failed: %s", exc)
    time.sleep(0.2)


def is_typing_focused(driver) -> bool:
    try:
        return driver.execute_script("""
            var words = document.getElementById('words');
            return words && !words.classList.contains('blurred');
        """) or False
    except Exception as exc:
        log.debug("Focus check failed: %s", exc)
        return False


def is_test_ready(driver) -> bool:
    try:
        return driver.execute_script("""
            var words = document.getElementById('words');
            if (!words) return false;
            var result = document.getElementById('result');
            if (result && !result.classList.contains('hidden')) return false;
            var wordEls = words.querySelectorAll('.word');
            if (wordEls.length === 0) return false;
            var active = words.querySelector('.word.active');
            if (!active) return false;
            var typed = words.querySelectorAll('.word.typed');
            if (typed.length > 0) return false;
            var correctOrIncorrect = active.querySelectorAll(
                'letter.correct, letter.incorrect');
            if (correctOrIncorrect.length > 0) return false;
            return true;
        """) or False
    except Exception as exc:
        log.debug("Test ready check failed: %s", exc)
        return False


def is_test_finished(driver) -> bool:
    try:
        return driver.execute_script("""
            var result = document.getElementById('result');
            return result && !result.classList.contains('hidden');
        """) or False
    except Exception as exc:
        log.debug("Test finished check failed: %s", exc)
        return False


def detect_test_mode(driver) -> dict:
    """Detect the current MonkeyType test mode and settings."""
    try:
        result = driver.execute_script("""
            var modeEl = document.querySelector('#testConfig .mode .textButton.active');
            var mode = modeEl ? modeEl.getAttribute('mode') : 'unknown';
            var detail = '';
            if (mode === 'time') {
                var timeEl = document.querySelector(
                    '#testConfig .time .textButton.active');
                detail = timeEl ? timeEl.getAttribute('timeConfig') : '';
            } else if (mode === 'words') {
                var wordEl = document.querySelector(
                    '#testConfig .wordCount .textButton.active');
                detail = wordEl ? wordEl.getAttribute('wordCount') : '';
            }
            return {mode: mode, detail: detail};
        """)
        return result if result else {"mode": "unknown", "detail": ""}
    except Exception as exc:
        log.debug("Mode detection failed: %s", exc)
        return {"mode": "unknown", "detail": ""}


def get_all_words(driver) -> list | None:
    """Read all currently visible words from the DOM."""
    try:
        return driver.execute_script("""
            var words = document.querySelectorAll('#words .word');
            if (!words.length) return null;
            return Array.from(words).map(function(w) {
                return Array.from(w.querySelectorAll('letter'))
                    .map(function(l) { return l.textContent; }).join('');
            });
        """)
    except Exception as exc:
        log.debug("Word reading failed: %s", exc)
        return None


def get_new_words_from(driver, start_index: int) -> list:
    """Issue #3: Read words starting from a given index for dynamic word loading.

    In time mode, MonkeyType lazily loads new words as you type. This function
    reads words from start_index onward, returning any new words that have appeared.
    """
    try:
        result = driver.execute_script(f"""
            var words = document.querySelectorAll('#words .word');
            var newWords = [];
            for (var i = {start_index}; i < words.length; i++) {{
                var letters = words[i].querySelectorAll('letter');
                var text = Array.from(letters).map(function(l) {{
                    return l.textContent;
                }}).join('');
                newWords.push(text);
            }}
            return newWords;
        """)
        return result if result else []
    except Exception as exc:
        log.debug("Dynamic word fetch failed: %s", exc)
        return []


def get_results(driver, timeout: int = 15) -> dict:
    for _ in range(timeout):
        time.sleep(1)
        if is_test_finished(driver):
            break
    try:
        result = driver.execute_script("""
            var wpm = document.querySelector('.group.wpm .bottom');
            var acc = document.querySelector('.group.acc .bottom');
            var con = document.querySelector('.group.flat.consistency .bottom');
            return {
                wpm: wpm ? wpm.textContent : null,
                acc: acc ? acc.textContent : null,
                consistency: con ? con.textContent : null
            };
        """)
        return result if result else {"wpm": None, "acc": None, "consistency": None}
    except Exception as exc:
        log.debug("Results reading failed: %s", exc)
        return {"wpm": None, "acc": None, "consistency": None}


def click_next_test(driver) -> bool:
    try:
        cdp_press_key(driver, SPECIAL_KEYS["Tab"], 0.05)
        return True
    except Exception as exc:
        log.debug("Click next test failed: %s", exc)
        return False


# ===========================================================================
#  Main Typing Orchestrator  (Issue #3: dynamic word loading)
# ===========================================================================

def type_all_words(driver, words: list, profile: HumanProfile,
                   mode: str = "unknown") -> tuple:
    """Orchestrate the full typing of all words with maximum realism.

    Issue #3: In time mode, continuously polls for new words as they appear.
    """
    engine = KeystrokeDynamicsEngine(profile, total_words=len(words))
    error_engine = ErrorEngine(profile)
    overlap_state = OverlapState()

    # Focus with realistic mouse behavior
    focus_typing_area(driver)
    time.sleep(random.uniform(0.2, 0.5))
    if not is_typing_focused(driver):
        focus_typing_area(driver)
        time.sleep(0.4)

    count = 0
    total_known = len(words)
    i = 0

    while i < len(words):
        is_last = (i == len(words) - 1)

        # Issue #3: in time mode, check for new words when running low
        if mode == "time" and is_last:
            new_words = get_new_words_from(driver, total_known)
            if new_words:
                words.extend(new_words)
                total_known += len(new_words)
                engine.total_words = len(words)
                is_last = False
                log.debug("Loaded %d new words (total: %d)", len(new_words), len(words))

        type_word_advanced(driver, words[i], engine, error_engine, i,
                           is_last, overlap_state)
        count += 1
        i += 1

        # Check if test ended (time mode can end mid-word)
        if mode == "time" and i % 5 == 0:
            if is_test_finished(driver):
                log.debug("Test finished mid-typing at word %d", i)
                break

        # Occasional mouse micro-movement
        if random.random() < 0.03:
            simulate_mouse_idle(driver)

    # Make sure no keys are still held
    overlap_state.release_held(driver)

    return count, engine.get_consistency_report()


# ===========================================================================
#  Display
# ===========================================================================

def display(data: dict, columns: list | None = None):
    if columns is None:
        columns = list(data.keys())
    print()
    widths = {}
    for k in columns:
        vals = data.get(k, [])
        w = max(len(k), max((len(str(v)) for v in vals), default=0))
        widths[k] = w + 2

    header = "".join(k.ljust(widths[k]) for k in columns)
    print(header)
    print("-" * len(header))

    row_count = len(next(iter(data.values())))
    for idx in range(row_count):
        row = "".join(str(data[k][idx]).ljust(widths[k]) for k in columns)
        print(row)
    print()


# ===========================================================================
#  CLI  (Issue #21: --verbose flag)
# ===========================================================================

PROFILES = {
    "casual":  {"wpm_range": (75, 95),   "desc": "Casual typist (75-95 WPM)"},
    "average": {"wpm_range": (95, 115),  "desc": "Average typist (95-115 WPM)"},
    "fast":    {"wpm_range": (115, 135), "desc": "Fast typist (115-135 WPM)"},
    "pro":     {"wpm_range": (130, 155), "desc": "Pro typist (130-155 WPM)"},
    "godlike": {"wpm_range": (155, 190), "desc": "Godlike (155-190 WPM, use words mode!)"},
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="MonkeyType Bot — god-level undetectable typing automation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python monkeytype.py                      # default ~110 WPM
  python monkeytype.py --wpm 90             # target 90 WPM
  python monkeytype.py --wpm 120 -n 5       # 5 rounds at 120 WPM
  python monkeytype.py --loop               # infinite rounds
  python monkeytype.py --profile casual     # casual preset (75-95 WPM)
  python monkeytype.py --profile pro        # pro preset (130-155 WPM)
  python monkeytype.py --profile godlike    # godlike (155-190 WPM)
  python monkeytype.py --verbose            # show debug metrics

profiles:
""" + "\n".join(f"  {k:10s} {v['desc']}" for k, v in PROFILES.items()),
    )
    speed = parser.add_mutually_exclusive_group()
    speed.add_argument("--wpm", type=int, default=None, metavar="N",
                       help="target WPM (default: 110)")
    speed.add_argument("--delay", type=float, default=None, metavar="SEC",
                       help="raw inter-key delay in seconds")
    speed.add_argument("--profile", type=str, default=None, metavar="NAME",
                       choices=list(PROFILES.keys()),
                       help="preset profile: " + ", ".join(PROFILES.keys()))
    rounds = parser.add_mutually_exclusive_group()
    rounds.add_argument("-n", "--count", type=int, default=None, metavar="N",
                        help="number of rounds (default: 1)")
    rounds.add_argument("--loop", action="store_true",
                        help="run forever until Ctrl+C")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="enable debug logging (keystroke metrics, timing)")
    return parser.parse_args()


# ===========================================================================
#  Main
# ===========================================================================

_results_data: dict = {
    "Round": [], "WPM": [], "Accuracy": [],
    "Consistency": [], "KeyCons": [],
}
_shutdown = False


def handle_exit(signum, frame):
    global _shutdown
    _shutdown = True
    print("\n\nStopping...")
    if _results_data["Round"]:
        print("\n--- Session Results ---")
        display(_results_data)
    else:
        print("No completed rounds.")
    print("Goodbye!")
    _sys.exit(0)


def main():
    global _shutdown

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    args = parse_args()

    # Issue #21: verbose mode
    if args.verbose:
        log.setLevel(logging.DEBUG)

    # Resolve target WPM
    if args.profile:
        wpm_lo, wpm_hi = PROFILES[args.profile]["wpm_range"]
        target_wpm = random.randint(wpm_lo, wpm_hi)
        profile_name = args.profile
    elif args.delay is not None:
        delay = max(0.02, min(args.delay, 1.0))
        target_wpm = int(60.0 / (delay / 0.82 * 6))
        profile_name = "custom"
    elif args.wpm is not None:
        target_wpm = args.wpm
        profile_name = "custom"
    else:
        target_wpm = 110
        profile_name = "default"

    # Resolve rounds
    if args.loop:
        max_rounds = float("inf")
    elif args.count is not None:
        max_rounds = max(1, args.count)
    else:
        max_rounds = 1

    # Banner
    print("=" * 62)
    print("  MonkeyType BOT — God-Level Undetectable Edition v2.0")
    print("  Ex-Gaussian Timing | AR(1) Autocorrelation | True Rollover")
    print("  Canvas/Audio Stealth | Motor Chunking | Position Errors")
    print("=" * 62)
    print()
    print(f"  OS:           {platform.system()} {platform.release()}")
    print(f"  Target WPM:   ~{target_wpm}")
    print(f"  Profile:      {profile_name}")
    rounds_str = ("infinite" if max_rounds == float("inf")
                  else str(int(max_rounds)))
    print(f"  Rounds:       {rounds_str}")
    if args.verbose:
        print(f"  Debug:        ON")
    if target_wpm > 130:
        print("  WARNING:      High speed! Use 'words' mode to avoid detection.")
    print()

    # Launch browser
    print("Launching stealth browser...")
    driver = launch_browser()

    # Calibrate CDP overhead for accurate timing
    calibrate_cdp_overhead(driver)

    print("  Waiting for MonkeyType...")
    if not wait_for_page_ready(driver):
        print("ERROR: MonkeyType did not load.")
        _sys.exit(1)

    # Issue #20: dismiss any popups/cookie banners
    dismiss_popups(driver)

    print()
    print("MonkeyType is ready!")
    print(f"You have {INITIAL_WAIT}s to log in / pick your mode.")
    print("The bot auto-starts when it detects a ready test.")
    print("Press Ctrl+C to stop.")
    print()

    for remaining in range(INITIAL_WAIT, 0, -1):
        if _shutdown:
            return
        print(f"  Starting in {remaining}s...  ", end="\r")
        time.sleep(1)
    print("  Watching for tests...              ")
    print()

    round_num = 0
    retry_count = 0  # Issue #19: track retries

    while round_num < max_rounds and not _shutdown:
        try:
            # Poll for test readiness
            waiting_msg_shown = False
            while not _shutdown:
                if is_test_ready(driver):
                    break
                if not waiting_msg_shown:
                    print("  Waiting for a test to be ready...")
                    waiting_msg_shown = True
                time.sleep(POLL_INTERVAL)

            if _shutdown:
                break

            round_num += 1
            retry_count = 0  # reset on successful round start

            # Detect mode
            mode_info = detect_test_mode(driver)
            mode_str = mode_info.get("mode", "?")
            detail_str = mode_info.get("detail", "")
            mode_display = f"{mode_str} {detail_str}".strip()

            # For profile mode, randomize WPM each round
            if args.profile:
                wpm_lo, wpm_hi = PROFILES[args.profile]["wpm_range"]
                target_wpm = random.randint(wpm_lo, wpm_hi)

            # Warn about time mode + high WPM
            if mode_str == "time" and target_wpm > 130:
                print(f"  WARNING: Time mode at {target_wpm} WPM — "
                      f"bot detection risk!")
                print(f"           Consider switching to 'words' mode.")

            print(f"--- Round {round_num} [{mode_display}] "
                  f"@ ~{target_wpm} WPM ---")

            # Issue #20: dismiss popups before each round
            dismiss_popups(driver)

            # Read words
            words = get_all_words(driver)
            if not words:
                retry_count += 1
                # Issue #19: prevent infinite retry
                if retry_count >= MAX_RETRY_PER_ROUND:
                    print(f"  Failed to read words after {MAX_RETRY_PER_ROUND}"
                          f" retries. Skipping round.")
                    retry_count = 0
                    continue
                print("  Could not read words. Retrying...")
                time.sleep(2)
                round_num -= 1
                continue

            print(f"  {len(words)} words detected. Typing...")

            # Create fresh profile for each round (Issue #17: fresh bigram speeds)
            profile = HumanProfile(target_wpm)

            count, consistency_report = type_all_words(
                driver, words, profile, mode=mode_str)

            if count == 0:
                retry_count += 1
                if retry_count >= MAX_RETRY_PER_ROUND:
                    print(f"  No words typed after {MAX_RETRY_PER_ROUND}"
                          f" retries. Skipping round.")
                    retry_count = 0
                    continue
                print("  No words typed. Retrying...")
                time.sleep(2)
                round_num -= 1
                continue

            print(f"  Typed {count} words. Waiting for results...")
            key_cons = consistency_report["keyConsistency"]
            hold_cons = consistency_report["holdConsistency"]
            print(f"  Internal key consistency: {key_cons}%"
                  f" (target: {consistency_report['targetConsistency']}%)")
            if args.verbose:
                print(f"  Hold consistency: {hold_cons}%"
                      f" | Total keystrokes: "
                      f"{consistency_report['totalKeystrokes']}")

            results = get_results(driver)
            wpm = results.get("wpm")
            acc = results.get("acc")
            consistency = results.get("consistency")

            if wpm:
                _results_data["Round"].append(round_num)
                _results_data["WPM"].append(wpm)
                _results_data["Accuracy"].append(acc or "?")
                _results_data["Consistency"].append(consistency or "?")
                _results_data["KeyCons"].append(f"{key_cons}%")
                display(_results_data)
            else:
                print("  Could not read results (test may not have "
                      "finished).")

            if round_num >= max_rounds:
                break

            # Issue: randomized cooldown between rounds (not fixed 3s)
            cooldown = random.uniform(2.0, 5.0)
            print(f"  Next round in {cooldown:.0f}s...")
            time.sleep(cooldown)

            # Trigger next test
            click_next_test(driver)
            time.sleep(1)

        except (NoSuchWindowException, InvalidSessionIdException):
            print("\n  Browser window was closed. Stopping.")
            break
        except WebDriverException as exc:
            msg = str(exc)
            if any(s in msg for s in ["no such window", "not connected",
                                       "disconnected", "session deleted"]):
                print("\n  Browser connection lost. Stopping.")
                break
            log.error("Unexpected WebDriver error: %s", exc)
            raise

    # Final summary
    if _results_data["Round"]:
        print("\n=== Session Complete ===")
        display(_results_data)
    else:
        print("\nNo completed rounds.")

    print("Done! Browser is still open.")
    print("Goodbye!")


if __name__ == "__main__":
    main()
