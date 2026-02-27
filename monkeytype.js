// ==UserScript==
// @name         MonkeyType Human Typer
// @author       MonkeyType-BOT
// @description  Undetectable human-like auto-typer for MonkeyType. Press F6 to toggle, F7 to change WPM.
// @icon         https://i.imgur.com/fUjylt3.png
// @version      2026.13
// @match        *://monkeytype.com/*
// @run-at       document-idle
// @grant        none
// @license      MIT
// @namespace    monkeytype-bot
// ==/UserScript==

(function () {
  "use strict";

  // ===========================================================================
  //  CONFIG
  // ===========================================================================
  let TARGET_WPM = 120;
  const TOGGLE_KEY = "F6";
  const WPM_KEY = "F7";
  const REFERENCE_WPM = 110;
  const MIN_SLEEP = 2; // ms

  let enabled = false;
  let running = false;
  let stopRequested = false;

  // ===========================================================================
  //  UTILITY
  // ===========================================================================
  function sleep(ms) {
    return new Promise((r) => setTimeout(r, Math.max(MIN_SLEEP, ms)));
  }

  function randUniform(a, b) {
    return Math.random() * (b - a) + a;
  }

  function randInt(a, b) {
    return Math.floor(Math.random() * (b - a + 1)) + a;
  }

  function randGauss(mu, sigma) {
    // Box-Muller transform
    let u1, u2;
    do {
      u1 = Math.random();
    } while (u1 === 0);
    u2 = Math.random();
    return (
      mu + sigma * Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2)
    );
  }

  function randExponential(lambda) {
    let u;
    do {
      u = Math.random();
    } while (u === 0);
    return -Math.log(u) / lambda;
  }

  function randLogNormal(mu, sigma) {
    return Math.exp(randGauss(mu, Math.max(0.05, sigma)));
  }

  function exGaussian(mu, sigma, tau) {
    const gauss = randGauss(mu, sigma);
    const expo = tau > 0 ? randExponential(1.0 / tau) : 0;
    return gauss + expo;
  }

  // ===========================================================================
  //  ANATOMICAL HAND MODEL CONSTANTS
  // ===========================================================================
  const FINGER_MAP = {
    q: 0,
    a: 0,
    z: 0,
    1: 0,
    "`": 0,
    w: 1,
    s: 1,
    x: 1,
    2: 1,
    e: 2,
    d: 2,
    c: 2,
    3: 2,
    r: 3,
    f: 3,
    v: 3,
    t: 3,
    g: 3,
    b: 3,
    4: 3,
    5: 3,
    y: 4,
    h: 4,
    n: 4,
    u: 4,
    j: 4,
    m: 4,
    6: 4,
    7: 4,
    i: 5,
    k: 5,
    ",": 5,
    8: 5,
    o: 6,
    l: 6,
    ".": 6,
    9: 6,
    p: 7,
    ";": 7,
    "/": 7,
    0: 7,
    "-": 7,
    "=": 7,
    "[": 7,
    "]": 7,
    "'": 7,
    "\\": 7,
    " ": 8,
  };

  const KEY_ROW = {
    "`": 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
    7: 0,
    8: 0,
    9: 0,
    0: 0,
    "-": 0,
    "=": 0,
    q: 1,
    w: 1,
    e: 1,
    r: 1,
    t: 1,
    y: 1,
    u: 1,
    i: 1,
    o: 1,
    p: 1,
    "[": 1,
    "]": 1,
    "\\": 1,
    a: 2,
    s: 2,
    d: 2,
    f: 2,
    g: 2,
    h: 2,
    j: 2,
    k: 2,
    l: 2,
    ";": 2,
    "'": 2,
    z: 3,
    x: 3,
    c: 3,
    v: 3,
    b: 3,
    n: 3,
    m: 3,
    ",": 3,
    ".": 3,
    "/": 3,
    " ": 4,
  };

  const FINGER_SPEED = {
    0: 1.35,
    1: 1.15,
    2: 1.0,
    3: 0.9,
    4: 0.9,
    5: 1.0,
    6: 1.15,
    7: 1.35,
    8: 0.75,
  };

  const FINGER_HOLD = {
    0: 1.25,
    1: 1.12,
    2: 1.0,
    3: 0.88,
    4: 0.88,
    5: 1.0,
    6: 1.12,
    7: 1.25,
    8: 0.8,
  };

  function getFinger(ch) {
    return FINGER_MAP[ch.toLowerCase()] ?? 5;
  }
  function getRow(ch) {
    return KEY_ROW[ch.toLowerCase()] ?? 2;
  }
  function sameHand(f1, f2) {
    if (f1 === 8 || f2 === 8) return false;
    return (f1 <= 3 && f2 <= 3) || (f1 >= 4 && f2 >= 4);
  }
  function rowDistance(r1, r2) {
    return Math.abs(r1 - r2);
  }

  // ---------------------------------------------------------------------------
  //  Bigram data
  // ---------------------------------------------------------------------------
  const FAST_BIGRAMS = [
    "th",
    "he",
    "in",
    "er",
    "an",
    "on",
    "en",
    "at",
    "ou",
    "ed",
    "is",
    "it",
    "al",
    "ar",
    "or",
    "ti",
    "te",
    "st",
    "se",
    "le",
    "ng",
    "io",
    "re",
    "nd",
    "ha",
    "to",
    "of",
  ];
  const SLOW_BIGRAMS = [
    "bf",
    "zx",
    "qp",
    "pq",
    "xz",
    "fb",
    "mj",
    "jm",
    "vb",
    "bv",
    "ce",
    "ec",
    "nu",
    "un",
    "my",
    "ym",
    "br",
    "rb",
    "gr",
    "rg",
    "az",
    "za",
    "sx",
    "xs",
    "dc",
    "cd",
    "fv",
    "vf",
    "gt",
    "tg",
    "hy",
    "yh",
    "ju",
    "uj",
    "ki",
    "ik",
    "lo",
    "ol",
  ];

  function generateBigramSpeeds() {
    const speeds = {};
    for (const pair of FAST_BIGRAMS) speeds[pair] = randUniform(0.55, 0.8);
    for (const pair of SLOW_BIGRAMS) speeds[pair] = randUniform(1.25, 1.8);
    return speeds;
  }

  // Same-finger bigrams
  const SAME_FINGER_PAIRS = new Set();
  const fingerGroups = [
    ["qaz", 0],
    ["wsx", 1],
    ["edc", 2],
    ["rfvtgb", 3],
    ["yhnujm", 4],
    ["ik,", 5],
    ["ol.", 6],
    ["p;/'-=[]\\", 7],
  ];
  for (const [keys] of fingerGroups) {
    for (const a of keys) {
      for (const b of keys) {
        if (a !== b) SAME_FINGER_PAIRS.add(a + b);
      }
    }
  }

  // ---------------------------------------------------------------------------
  //  Adjacent keys (for typos)
  // ---------------------------------------------------------------------------
  const ADJACENT_KEYS = {
    a: "sqwz",
    b: "vghn",
    c: "xdfv",
    d: "serfcx",
    e: "wsdfr",
    f: "dertgcv",
    g: "frtyhhbv",
    h: "gtyjnb",
    i: "ujko",
    j: "hyuknm",
    k: "juilm",
    l: "kop",
    m: "njk",
    n: "bhjm",
    o: "iklp",
    p: "ol",
    q: "wa",
    r: "edft",
    s: "awedxz",
    t: "rfgy",
    u: "yhji",
    v: "cfgb",
    w: "qase",
    x: "zsdc",
    y: "tghu",
    z: "asx",
  };

  // Motor chunks
  const MOTOR_CHUNKS = new Set([
    "the",
    "and",
    "for",
    "are",
    "but",
    "not",
    "you",
    "all",
    "can",
    "had",
    "her",
    "was",
    "one",
    "our",
    "out",
    "has",
    "his",
    "how",
    "its",
    "may",
    "new",
    "now",
    "old",
    "see",
    "way",
    "who",
    "did",
    "get",
    "let",
    "say",
    "she",
    "too",
    "use",
    "is",
    "it",
    "he",
    "we",
    "do",
    "no",
    "so",
    "up",
    "if",
    "my",
    "as",
    "at",
    "be",
    "by",
    "go",
    "in",
    "me",
    "of",
    "on",
    "or",
    "to",
    "a",
    "i",
  ]);

  // Letter frequency
  const LETTER_FREQ = {
    e: 13,
    t: 9.1,
    a: 8.2,
    o: 7.5,
    i: 7.0,
    n: 6.7,
    s: 6.3,
    h: 6.1,
    r: 6.0,
    d: 4.3,
    l: 4.0,
    c: 2.8,
    u: 2.8,
    m: 2.4,
    w: 2.4,
    f: 2.2,
    g: 2.0,
    y: 2.0,
    p: 1.9,
    b: 1.5,
    v: 1.0,
    k: 0.8,
    j: 0.15,
    x: 0.15,
    q: 0.1,
    z: 0.07,
  };

  function wordDifficulty(word) {
    if (!word) return 0;
    let lengthScore = Math.max(0, word.length - 3) * 0.08;
    let rarity = 0;
    for (const ch of word.toLowerCase()) {
      const freq = LETTER_FREQ[ch] ?? 0.5;
      rarity += Math.max(0, 5.0 - freq) * 0.02;
    }
    let bigramScore = 0;
    const lower = word.toLowerCase();
    for (let j = 0; j < lower.length - 1; j++) {
      if (SAME_FINGER_PAIRS.has(lower[j] + lower[j + 1])) bigramScore += 0.08;
    }
    return Math.min(2.0, lengthScore + rarity + bigramScore);
  }

  // ===========================================================================
  //  KOGASA CONSISTENCY
  // ===========================================================================
  function kogasa(cov) {
    return 100 * (1 - Math.tanh(cov + cov ** 3 / 3 + cov ** 5 / 5));
  }

  function targetCovForConsistency(target) {
    let lo = 0,
      hi = 5;
    for (let i = 0; i < 100; i++) {
      const mid = (lo + hi) / 2;
      if (kogasa(mid) > target) lo = mid;
      else hi = mid;
    }
    return (lo + hi) / 2;
  }

  // ===========================================================================
  //  COMMON TYPOS & CONFUSION PAIRS
  // ===========================================================================
  const COMMON_TYPOS = {
    the: ["teh", "hte", "th", "tje", "tue"],
    and: ["adn", "nad", "anf", "ans"],
    that: ["taht", "htat", "tath", "thta"],
    have: ["ahve", "hvae", "hav", "haev"],
    with: ["wiht", "wtih", "wth", "iwth"],
    this: ["tihs", "thsi", "htis", "tis"],
    from: ["form", "fomr", "fro", "rfom"],
    they: ["tehy", "thye", "htey", "tey"],
    been: ["eben", "bene", "ben", "beem"],
    their: ["thier", "tehir", "theri", "ther"],
    which: ["whcih", "whihc", "wich", "wihch"],
    would: ["woudl", "wuold", "woud", "owuld"],
    there: ["tehre", "htere", "ther", "theer"],
    about: ["abotu", "abuot", "abut", "baout"],
    just: ["jsut", "juts", "jusr"],
    like: ["liek", "likr", "lik", "lkie"],
    what: ["waht", "wath", "whta", "wat"],
    when: ["wehn", "whn", "whne", "hwen"],
    your: ["yuor", "yoru", "yor", "yoir"],
    some: ["soem", "smoe", "soe", "osme"],
    them: ["tehm", "thme", "tem", "htem"],
    than: ["tahn", "htan", "thn"],
    other: ["ohter", "otehr", "oter", "toher"],
    time: ["tiem", "tmie", "itme", "tim"],
    very: ["vrey", "vey", "ver", "evry"],
    also: ["aslo", "laso", "als", "aldo"],
    make: ["maek", "mkae", "amke", "mak"],
    know: ["knwo", "konw", "kno", "nkow"],
    people: ["peopel", "poeple", "peolpe", "peopl"],
    because: ["becasue", "becuase", "becaus", "beacuse"],
    could: ["cuold", "coudl", "coud", "colud"],
    should: ["shoudl", "shuold", "shoud", "sholud"],
    think: ["thnik", "thnk", "htink", "thiink"],
    after: ["aftre", "atfer", "afer", "aftr"],
    work: ["wokr", "wrk", "owrk", "wrok"],
    first: ["frist", "fisrt", "firt", "firsr"],
    well: ["wlel", "wel", "weel", "wll"],
    even: ["eevn", "evne", "ven"],
    good: ["godo", "god", "goood", "ogod"],
    much: ["mcuh", "muhc", "mch", "umch"],
    where: ["wehre", "wheer", "wher", "hwere"],
    right: ["rihgt", "rigth", "rgiht", "riight"],
    still: ["sitll", "stil", "stll", "tsill"],
    between: ["bewteen", "betwen", "betwene", "bteween"],
    before: ["beofre", "befroe", "befor", "bfore"],
    through: ["thorugh", "throught", "throuhg", "trhough"],
    great: ["gerat", "graet", "gret", "grear"],
    being: ["bieng", "beng", "beign", "beig"],
    world: ["wrold", "wolrd", "worl", "wrld"],
    these: ["thees", "tehse", "thse", "htese"],
    those: ["thoes", "htose", "thoese", "thsoe"],
    does: ["dose", "deos", "doe", "odes"],
    going: ["giong", "goign", "gong", "goig"],
    take: ["taek", "tkae", "tka", "atke"],
    want: ["wnat", "watn", "wnt", "awnt"],
    same: ["saem", "smae", "sam", "asme"],
    each: ["eahc", "aech", "ech"],
    come: ["coem", "cmoe", "com", "ocme"],
    many: ["mnay", "mny", "amny", "mayn"],
    then: ["tehn", "thn", "thne", "hten"],
    only: ["olny", "onyl", "noly", "onl"],
    over: ["oevr", "voer", "ovr", "ovre"],
    more: ["moer", "mroe", "mor", "omre"],
    such: ["scuh", "shcu", "suhc", "uscb"],
    into: ["itno", "inot", "nito", "ino"],
    year: ["yaer", "yer", "yera", "eyar"],
    most: ["msot", "mos", "omst", "mots"],
    find: ["fnd", "fidn", "fnid", "ifnd"],
    here: ["heer", "hre", "ehre", "herr"],
    thing: ["thign", "thnig", "ting", "htign"],
    long: ["lnog", "logn", "lon", "olng"],
    look: ["loko", "lok", "loook", "olok"],
    down: ["dwon", "donw", "don", "odwn"],
    life: ["lief", "lfie", "lif", "ilfe"],
    never: ["nver", "neevr", "nevr", "enver"],
    need: ["nede", "ned", "nee", "ened"],
    will: ["wll", "iwll", "wil", "wlil"],
    home: ["hmoe", "hom", "hoem", "ohme"],
    back: ["bakc", "bck", "abck", "bcak"],
    give: ["gvie", "giev", "giv", "igve"],
    help: ["hlep", "hep", "ehlp", "hepl"],
    hand: ["hnad", "hnd", "ahnd", "hadn"],
    high: ["hgih", "hih", "ihgh", "hig"],
    keep: ["kepe", "kep", "keeep", "ekep"],
    last: ["lsat", "las", "alst", "lasr"],
    name: ["naem", "nmae", "nam", "anme"],
    play: ["paly", "ply", "pla", "lpay"],
    small: ["smlal", "smal", "smll", "samll"],
    every: ["eevry", "evrey", "evry", "evey"],
    again: ["agian", "agin", "aagin", "gaain"],
    change: ["chnage", "chagne", "chang", "cahnge"],
    point: ["piont", "ponit", "pint", "poin"],
    place: ["palce", "plcae", "plac"],
    under: ["uner", "udner", "undr", "nuder"],
    while: ["whiel", "whlie", "whil", "hwile"],
  };

  const CONFUSION_PAIRS = {
    b: "v",
    v: "b",
    n: "m",
    m: "n",
    d: "f",
    f: "d",
    g: "h",
    h: "g",
    i: "o",
    o: "i",
    e: "r",
    r: "e",
    c: "x",
    x: "c",
  };

  // ===========================================================================
  //  CHAR -> KeyboardEvent CODE MAPPING
  // ===========================================================================
  const CHAR_TO_CODE = {
    a: "KeyA",
    b: "KeyB",
    c: "KeyC",
    d: "KeyD",
    e: "KeyE",
    f: "KeyF",
    g: "KeyG",
    h: "KeyH",
    i: "KeyI",
    j: "KeyJ",
    k: "KeyK",
    l: "KeyL",
    m: "KeyM",
    n: "KeyN",
    o: "KeyO",
    p: "KeyP",
    q: "KeyQ",
    r: "KeyR",
    s: "KeyS",
    t: "KeyT",
    u: "KeyU",
    v: "KeyV",
    w: "KeyW",
    x: "KeyX",
    y: "KeyY",
    z: "KeyZ",
    0: "Digit0",
    1: "Digit1",
    2: "Digit2",
    3: "Digit3",
    4: "Digit4",
    5: "Digit5",
    6: "Digit6",
    7: "Digit7",
    8: "Digit8",
    9: "Digit9",
    " ": "Space",
    "`": "Backquote",
    "-": "Minus",
    "=": "Equal",
    "[": "BracketLeft",
    "]": "BracketRight",
    "\\": "Backslash",
    ";": "Semicolon",
    "'": "Quote",
    ",": "Comma",
    ".": "Period",
    "/": "Slash",
  };

  // Shift-produced characters -> their base key and code
  const SHIFT_CHARS = {
    "~": ["`", "Backquote"],
    "!": ["1", "Digit1"],
    "@": ["2", "Digit2"],
    "#": ["3", "Digit3"],
    $: ["4", "Digit4"],
    "%": ["5", "Digit5"],
    "^": ["6", "Digit6"],
    "&": ["7", "Digit7"],
    "*": ["8", "Digit8"],
    "(": ["9", "Digit9"],
    ")": ["0", "Digit0"],
    _: ["-", "Minus"],
    "+": ["=", "Equal"],
    "{": ["[", "BracketLeft"],
    "}": ["]", "BracketRight"],
    "|": ["\\", "Backslash"],
    ":": [";", "Semicolon"],
    '"': ["'", "Quote"],
    "<": [",", "Comma"],
    ">": [".", "Period"],
    "?": ["/", "Slash"],
    A: ["a", "KeyA"],
    B: ["b", "KeyB"],
    C: ["c", "KeyC"],
    D: ["d", "KeyD"],
    E: ["e", "KeyE"],
    F: ["f", "KeyF"],
    G: ["g", "KeyG"],
    H: ["h", "KeyH"],
    I: ["i", "KeyI"],
    J: ["j", "KeyJ"],
    K: ["k", "KeyK"],
    L: ["l", "KeyL"],
    M: ["m", "KeyM"],
    N: ["n", "KeyN"],
    O: ["o", "KeyO"],
    P: ["p", "KeyP"],
    Q: ["q", "KeyQ"],
    R: ["r", "KeyR"],
    S: ["s", "KeyS"],
    T: ["t", "KeyT"],
    U: ["u", "KeyU"],
    V: ["v", "KeyV"],
    W: ["w", "KeyW"],
    X: ["x", "KeyX"],
    Y: ["y", "KeyY"],
    Z: ["z", "KeyZ"],
  };

  // Legacy keyCode values
  const KEY_CODES = {
    a: 65,
    b: 66,
    c: 67,
    d: 68,
    e: 69,
    f: 70,
    g: 71,
    h: 72,
    i: 73,
    j: 74,
    k: 75,
    l: 76,
    m: 77,
    n: 78,
    o: 79,
    p: 80,
    q: 81,
    r: 82,
    s: 83,
    t: 84,
    u: 85,
    v: 86,
    w: 87,
    x: 88,
    y: 89,
    z: 90,
    0: 48,
    1: 49,
    2: 50,
    3: 51,
    4: 52,
    5: 53,
    6: 54,
    7: 55,
    8: 56,
    9: 57,
    " ": 32,
    "`": 192,
    "-": 189,
    "=": 187,
    "[": 219,
    "]": 221,
    "\\": 220,
    ";": 186,
    "'": 222,
    ",": 188,
    ".": 190,
    "/": 191,
    Backspace: 8,
  };

  function getKeyCode(ch) {
    return KEY_CODES[ch.toLowerCase()] ?? ch.charCodeAt(0);
  }

  function getEventCode(ch) {
    // Check if it's a shift character
    if (SHIFT_CHARS[ch]) return SHIFT_CHARS[ch][1];
    return CHAR_TO_CODE[ch.toLowerCase()] ?? "NoCode";
  }

  function needsShift(ch) {
    return ch in SHIFT_CHARS;
  }

  // ===========================================================================
  //  HUMAN PROFILE
  // ===========================================================================
  class HumanProfile {
    constructor(targetWpm) {
      this.targetWpm = targetWpm;

      // Base delay from target WPM (6 keystrokes per word)
      const rawIki = 60000.0 / (targetWpm * 6); // in ms
      const speedRatio = Math.min(2.0, targetWpm / REFERENCE_WPM);
      const correction = 1.04 + 0.1 * speedRatio;
      this.baseDelay = rawIki * Math.min(1.25, correction);

      // Consistency targets
      if (targetWpm < 80) {
        this.targetConsistency = randUniform(50, 65);
      } else if (targetWpm < 120) {
        this.targetConsistency = randUniform(60, 75);
      } else if (targetWpm < 160) {
        this.targetConsistency = randUniform(68, 82);
      } else {
        this.targetConsistency = randUniform(72, 85);
      }
      this.targetCov = targetCovForConsistency(this.targetConsistency);

      // Key hold duration (ms)
      this.holdMean = this.baseDelay * randUniform(0.4, 0.55);
      this.holdSigma = this.holdMean * randUniform(0.25, 0.4);
      this.holdMin = 25; // ms
      this.holdMax = this.baseDelay * 1.5;

      // Ex-Gaussian parameters
      const speedFactor = Math.max(
        0.5,
        Math.min(2.0, targetWpm / REFERENCE_WPM),
      );
      this.exgaussSigma = this.baseDelay * randUniform(0.08, 0.15);
      this.exgaussTau = this.baseDelay * randUniform(0.05, 0.12);

      // Mistake rates
      const errorFactor = 0.8 + 0.2 * Math.min(1.0, targetWpm / 100);
      this.typoChance = 0.018 * errorFactor;
      this.leaveMistakeChance = randUniform(0.08, 0.15);

      // Error type distribution weights
      this.errorWeights = {
        adjacent: 0.45,
        transpose: 0.15 + 0.05 * speedFactor,
        confusion: 0.15,
        double_tap: 0.1 + 0.02 * speedFactor,
        skip: 0.06 + 0.02 * speedFactor,
      };

      // Delayed error detection
      this.delayedNoticeChance = 0.3;
      this.delayedNoticeChars = [1, 3];
      this.overBackspaceChance = 0.12;

      // Word boundary timing
      this.wordStartExtra = [1.05, 1.25];
      this.spaceGapRange = [0.75, 1.3];

      // Thinking pauses
      this.thinkPauseChance = 0.04;
      this.thinkPauseRange = [2.0, 5.0];

      // Warm-up
      this.warmupWords = randInt(2, 5);
      this.warmupSlowdown = randUniform(1.1, 1.3);

      // Fatigue
      this.fatigueMax = randUniform(1.1, 1.3);
      this.fatigueOnsetWords = randInt(40, 70);

      // Burst typing (motor chunks)
      this.burstMaxLen = 4;
      this.burstSpeedup = randUniform(0.72, 0.85);
      this.chunkSpeedup = randUniform(0.62, 0.78);

      // Correction reaction (ms)
      this.correctionReact = [100, 350];
      this.backspaceDelay = [30, 90];

      // Key overlap (rollover)
      this.overlapChance = Math.min(0.4, targetWpm / 500);
      this.overlapTime = [5, 35]; // ms

      // AR(1) autocorrelation
      this.ar1Phi = randUniform(0.1, 0.3);

      // Rhythmic periodicity
      this.rhythmAmplitude = randUniform(0.02, 0.05);
      this.rhythmPeriod = randUniform(12, 25);

      // Sigmoid speed curve
      this.flowAccel = randUniform(0.92, 0.97);
      this.flowDecel = randUniform(1.02, 1.08);

      // Word difficulty pause scaling
      this.difficultyPauseScale = randUniform(0.3, 0.8);

      // Bigram speeds (regenerated per profile)
      this.bigramSpeeds = generateBigramSpeeds();
    }
  }

  // ===========================================================================
  //  KEYSTROKE DYNAMICS ENGINE
  // ===========================================================================
  class KeystrokeDynamicsEngine {
    constructor(profile, totalWords) {
      this.profile = profile;
      this.totalWords = totalWords || 100;
      this.keySpacings = [];
      this.keyDurations = [];
      this.prevChar = null;
      this.prevFinger = null;
      this.prevRow = null;
      this.wordCount = 0;
      this.charInWord = 0;
      this.totalChars = 0;
      this._currentWordLen = 0;
      this._currentWord = "";
      this._ar1Residual = 0;
      this._lastDelay = null;
    }

    computeDelay(ch) {
      const p = this.profile;
      let base = p.baseDelay;

      const finger = getFinger(ch);
      const row = getRow(ch);

      // 1. Finger speed
      base *= FINGER_SPEED[finger] ?? 1.0;

      // 2. Row distance penalty
      if (this.prevRow !== null) {
        const dist = rowDistance(this.prevRow, row);
        if (dist > 0) base *= 1.0 + dist * randUniform(0.06, 0.14);
      }

      // 3-7. Finger/key relationship penalties (mutually exclusive)
      const isSameKey =
        this.prevChar && this.prevChar.toLowerCase() === ch.toLowerCase();
      const bigram = this.prevChar ? (this.prevChar + ch).toLowerCase() : "";
      const isSameFingerBigram = SAME_FINGER_PAIRS.has(bigram);
      const isSameFinger =
        this.prevFinger !== null && finger === this.prevFinger && finger !== 8;

      if (isSameKey) {
        const fingerMult = FINGER_HOLD[finger] ?? 1.0;
        base *= randUniform(1.25, 1.45) * fingerMult ** 0.3;
      } else if (isSameFingerBigram) {
        base *= randUniform(1.18, 1.38);
      } else if (isSameFinger) {
        base *= randUniform(1.12, 1.3);
      } else if (
        this.prevFinger !== null &&
        !sameHand(finger, this.prevFinger)
      ) {
        base *= randUniform(0.85, 0.95);
      } else if (
        this.prevFinger !== null &&
        sameHand(finger, this.prevFinger)
      ) {
        base *= randUniform(0.96, 1.08);
      }

      // 6a. Bigram-specific speed (applied independently)
      if (this.prevChar) {
        const bgSpeed = p.bigramSpeeds[bigram];
        if (bgSpeed !== undefined) base *= bgSpeed * randUniform(0.93, 1.07);
      }

      // 8. Word start: cognitive pause + word difficulty
      if (this.charInWord === 0) {
        base *= randUniform(...p.wordStartExtra);
        const diff = wordDifficulty(this._currentWord);
        base *= 1.0 + diff * p.difficultyPauseScale * randUniform(0.3, 0.7);
      }

      // 9. Warm-up
      if (this.wordCount < p.warmupWords) {
        const warmupProgress = this.wordCount / p.warmupWords;
        const smooth =
          p.warmupSlowdown - (p.warmupSlowdown - 1.0) * warmupProgress;
        const noise = randGauss(0, 0.08);
        base *= Math.max(1.0, smooth + noise);
      }

      // 10. Fatigue
      if (this.wordCount > p.fatigueOnsetWords) {
        const fatigueProgress = Math.min(
          1.0,
          (this.wordCount - p.fatigueOnsetWords) / 60,
        );
        base *= 1.0 + (p.fatigueMax - 1.0) * fatigueProgress;
      }

      // 11. Motor chunking
      if (
        MOTOR_CHUNKS.has(this._currentWord.toLowerCase()) &&
        this.charInWord > 0
      ) {
        base *= p.chunkSpeedup;
      } else if (this._currentWordLen <= p.burstMaxLen) {
        base *= p.burstSpeedup;
      }

      // 12. Sigmoid speed curve
      if (this.totalWords > 0) {
        const testProgress = this.wordCount / Math.max(1, this.totalWords);
        const sigmoid = 1.0 / (1.0 + Math.exp(-12 * (testProgress - 0.25)));
        const endDecel =
          1.0 + ((p.flowDecel - 1.0) * Math.max(0, testProgress - 0.85)) / 0.15;
        const flowMult = 1.0 - (1.0 - p.flowAccel) * sigmoid;
        base *= flowMult * endDecel;
      }

      // 13. Rhythmic periodicity
      if (p.rhythmPeriod > 0) {
        const phase = (2 * Math.PI * this.totalChars) / p.rhythmPeriod;
        base *= 1.0 + p.rhythmAmplitude * Math.sin(phase);
      }

      // 14. Ex-Gaussian sampling
      const sigma = base * (p.exgaussSigma / p.baseDelay);
      const tau = base * (p.exgaussTau / p.baseDelay);
      let delay = exGaussian(base, sigma, tau);

      // 15. AR(1) serial autocorrelation
      const innovation = delay - base;
      this._ar1Residual = p.ar1Phi * this._ar1Residual + innovation;
      delay = base + this._ar1Residual;

      // Clamp: never exceed 2.0x base_delay
      delay = Math.max(MIN_SLEEP, Math.min(delay, p.baseDelay * 2.0));

      // Record
      this.keySpacings.push(delay);
      this._lastDelay = delay;

      // Update state
      this.prevChar = ch;
      this.prevFinger = finger;
      this.prevRow = row;
      this.charInWord++;
      this.totalChars++;

      return delay;
    }

    computeHold(ch) {
      const p = this.profile;
      const finger = getFinger(ch);
      const fingerMult = FINGER_HOLD[finger] ?? 1.0;
      let baseHold = p.holdMean * fingerMult;

      // Log-normal distribution
      const muLn = Math.log(baseHold) - 0.5 * (p.holdSigma / baseHold) ** 2;
      const sigmaLn = p.holdSigma / baseHold;
      let hold = randLogNormal(muLn, Math.max(0.05, sigmaLn));

      // Home row bonus / number row penalty
      const row = getRow(ch);
      if (row === 2) hold *= randUniform(0.88, 0.97);
      else if (row === 0) hold *= randUniform(1.05, 1.2);

      // Space bar: consistent, shorter
      if (ch === " ") {
        hold = randLogNormal(
          Math.log(p.holdMean * 0.8),
          Math.max(0.05, (p.holdSigma * 0.5) / baseHold),
        );
      }

      // Correlate with spacing
      if (this._lastDelay !== null) {
        const speedRatio = this._lastDelay / p.baseDelay;
        hold *= 0.4 + 0.6 * Math.min(1.5, speedRatio);
      }

      hold = Math.max(p.holdMin, Math.min(hold, p.holdMax));

      this.keyDurations.push(hold);
      return hold;
    }

    shouldOverlap() {
      return Math.random() < this.profile.overlapChance;
    }

    overlapDuration() {
      return randUniform(...this.profile.overlapTime);
    }

    wordBoundary() {
      this.charInWord = 0;
      this.wordCount++;
    }

    setWordContext(word) {
      this._currentWord = word;
      this._currentWordLen = word.length;
    }
  }

  // ===========================================================================
  //  ERROR ENGINE
  // ===========================================================================
  class ErrorEngine {
    constructor(profile) {
      this.profile = profile;
    }

    shouldMakeError(ch, charIndex, word, wordIndex, prevChar) {
      const p = this.profile;
      let baseChance = p.typoChance;

      // Position weighting within word
      if (charIndex === 0) baseChance *= 0.05;
      else if (charIndex <= 2) baseChance *= 0.5;
      else if (charIndex <= 5) baseChance *= 1.5;

      // Pinky keys
      const finger = getFinger(ch);
      if (finger === 0 || finger === 7) baseChance *= 1.5;

      // Number row
      if (getRow(ch) === 0) baseChance *= 1.8;

      // Long words
      if (word.length > 6 && charIndex > 3) baseChance *= 1.2;

      // Fatigue
      if (wordIndex > 40)
        baseChance *= 1.0 + Math.min(0.3, (wordIndex - 40) / 200);

      // Difficult transitions
      if (prevChar) {
        const pf = getFinger(prevChar);
        const pr = getRow(prevChar);
        if (pf === finger && pf !== 8 && pr !== getRow(ch)) baseChance *= 1.6;
      }

      return Math.random() < baseChance;
    }

    getErrorType(ch, charIndex, word) {
      // Common whole-word typo
      if (charIndex === 0 && COMMON_TYPOS[word.toLowerCase()]) {
        const wpm = this.profile.targetWpm;
        const commonTypoRate =
          wpm <= 100 ? 0.06 : Math.max(0.01, 0.06 - 0.001 * (wpm - 100));
        if (Math.random() < commonTypoRate) return "common_typo";
      }

      // Weighted random from profile
      const weights = this.profile.errorWeights;
      const types = Object.keys(weights);
      const vals = Object.values(weights);
      const total = vals.reduce((a, b) => a + b, 0);
      let r = Math.random() * total;
      for (let i = 0; i < types.length; i++) {
        r -= vals[i];
        if (r <= 0) return types[i];
      }
      return types[types.length - 1];
    }

    getAdjacentTypo(ch) {
      const neighbors = ADJACENT_KEYS[ch.toLowerCase()];
      if (neighbors) {
        const wrong = neighbors[randInt(0, neighbors.length - 1)];
        return ch === ch.toUpperCase() && ch !== ch.toLowerCase()
          ? wrong.toUpperCase()
          : wrong;
      }
      return "abcdefghijklmnopqrstuvwxyz"[randInt(0, 25)];
    }

    getConfusionTypo(ch) {
      const pair = CONFUSION_PAIRS[ch.toLowerCase()];
      if (pair)
        return ch === ch.toUpperCase() && ch !== ch.toLowerCase()
          ? pair.toUpperCase()
          : pair;
      return this.getAdjacentTypo(ch);
    }

    shouldCorrect() {
      return Math.random() > this.profile.leaveMistakeChance;
    }

    shouldDelayNotice() {
      return Math.random() < this.profile.delayedNoticeChance;
    }

    delayedCharsCount() {
      return randInt(...this.profile.delayedNoticeChars);
    }

    shouldOverBackspace() {
      return Math.random() < this.profile.overBackspaceChance;
    }
  }

  // ===========================================================================
  //  KEYSTROKE DISPATCH
  //  Dispatches proper KeyboardEvent + InputEvent on #wordsInput
  //  MonkeyType listens on #wordsInput for keydown/keyup (timing recording)
  //  and beforeinput/input (text insertion)
  // ===========================================================================

  function getInputElement() {
    return document.querySelector("#wordsInput");
  }

  // Track which keys we've pressed down (for overlap simulation)
  const heldKeys = new Map(); // code -> true

  function dispatchKeyDown(inputEl, ch, withShift) {
    const code = getEventCode(ch);
    const keyCode = getKeyCode(ch);

    if (withShift && !heldKeys.has("ShiftLeft")) {
      // Press shift first
      const shiftDown = new KeyboardEvent("keydown", {
        key: "Shift",
        code: "ShiftLeft",
        keyCode: 16,
        which: 16,
        shiftKey: true,
        bubbles: true,
        cancelable: true,
        composed: true,
      });
      inputEl.dispatchEvent(shiftDown);
      heldKeys.set("ShiftLeft", true);
    }

    const kd = new KeyboardEvent("keydown", {
      key: ch,
      code: code,
      keyCode: keyCode,
      which: keyCode,
      shiftKey: withShift,
      bubbles: true,
      cancelable: true,
      composed: true,
    });
    inputEl.dispatchEvent(kd);
    heldKeys.set(code, true);
  }

  function dispatchKeyUp(inputEl, ch, withShift) {
    const code = getEventCode(ch);
    const keyCode = getKeyCode(ch);

    const ku = new KeyboardEvent("keyup", {
      key: ch,
      code: code,
      keyCode: keyCode,
      which: keyCode,
      shiftKey: withShift,
      bubbles: true,
      cancelable: true,
      composed: true,
    });
    inputEl.dispatchEvent(ku);
    heldKeys.delete(code);

    if (withShift && heldKeys.has("ShiftLeft")) {
      const shiftUp = new KeyboardEvent("keyup", {
        key: "Shift",
        code: "ShiftLeft",
        keyCode: 16,
        which: 16,
        shiftKey: false,
        bubbles: true,
        cancelable: true,
        composed: true,
      });
      inputEl.dispatchEvent(shiftUp);
      heldKeys.delete("ShiftLeft");
    }
  }

  function dispatchInput(inputEl, ch) {
    // Use execCommand('insertText') to produce isTrusted:true events.
    // This makes the browser generate trusted beforeinput + input events
    // and natively mutate the textarea value — indistinguishable from
    // real user input at the InputEvent level.
    inputEl.focus();
    // Place cursor at end of textarea to ensure correct insertion point
    inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length);
    document.execCommand("insertText", false, ch);
  }

  function dispatchBackspace(inputEl) {
    // keydown — still dispatched manually for MonkeyType's recordKeydownTime
    const kd = new KeyboardEvent("keydown", {
      key: "Backspace",
      code: "Backspace",
      keyCode: 8,
      which: 8,
      bubbles: true,
      cancelable: true,
      composed: true,
    });
    inputEl.dispatchEvent(kd);

    // Use execCommand('delete') to produce isTrusted:true beforeinput + input
    // events and let the browser natively mutate the textarea value.
    // Guard against deleting the leading space that MT prepends.
    if (inputEl.value.length > 1) {
      inputEl.focus();
      // Place cursor at end so 'delete' removes the last character
      inputEl.setSelectionRange(inputEl.value.length, inputEl.value.length);
      document.execCommand("delete", false, null);
    }

    // keyup — still dispatched manually for MonkeyType's recordKeyupTime
    const ku = new KeyboardEvent("keyup", {
      key: "Backspace",
      code: "Backspace",
      keyCode: 8,
      which: 8,
      bubbles: true,
      cancelable: true,
      composed: true,
    });
    inputEl.dispatchEvent(ku);
  }

  /**
   * Type a single character with proper keydown -> hold -> keyup sequence.
   * Returns a promise that resolves after the hold duration.
   */
  async function typeChar(inputEl, ch, holdMs) {
    const shift = needsShift(ch);

    // keydown (triggers MonkeyType's recordKeydownTime)
    dispatchKeyDown(inputEl, ch, shift);

    // input event (triggers MonkeyType's text processing)
    dispatchInput(inputEl, ch);

    // Hold the key for realistic duration
    await sleep(holdMs);

    // keyup (triggers MonkeyType's recordKeyupTime)
    dispatchKeyUp(inputEl, ch, shift);
  }

  /**
   * Type a character with overlap (rollover): press new key before releasing old.
   */
  async function typeCharWithOverlap(inputEl, ch, holdMs, overlapMs, prevCh) {
    const shift = needsShift(ch);

    // Press new key while previous is still held
    dispatchKeyDown(inputEl, ch, shift);
    dispatchInput(inputEl, ch);

    // Wait overlap time, then release previous key
    await sleep(overlapMs);
    if (prevCh) {
      const prevShift = needsShift(prevCh);
      dispatchKeyUp(inputEl, prevCh, prevShift);
    }

    // Wait remaining hold time
    const remaining = Math.max(MIN_SLEEP, holdMs - overlapMs);
    await sleep(remaining);

    // Don't release current key yet - it will be released by next overlap or explicit release
  }

  /**
   * Release any currently held key
   */
  function releaseAllHeld(inputEl) {
    // Release all held keys except tracking state
    for (const [code] of heldKeys) {
      if (code === "ShiftLeft") continue;
      const ku = new KeyboardEvent("keyup", {
        key: "",
        code: code,
        bubbles: true,
        cancelable: true,
        composed: true,
      });
      inputEl.dispatchEvent(ku);
    }
    if (heldKeys.has("ShiftLeft")) {
      const ku = new KeyboardEvent("keyup", {
        key: "Shift",
        code: "ShiftLeft",
        keyCode: 16,
        which: 16,
        bubbles: true,
        cancelable: true,
        composed: true,
      });
      inputEl.dispatchEvent(ku);
    }
    heldKeys.clear();
  }

  async function typeBackspace(inputEl, holdMs) {
    dispatchBackspace(inputEl);
    await sleep(holdMs);
  }

  // ===========================================================================
  //  DOM READING
  // ===========================================================================
  function isTestActive() {
    const tt = document.querySelector("#typingTest");
    return tt && !tt.classList.contains("hidden");
  }

  function getActiveWordElement() {
    return document.querySelector("#words .word.active");
  }

  function getAllWordElements() {
    return document.querySelectorAll("#words .word");
  }

  function getWordText(wordEl) {
    const letters = wordEl.querySelectorAll("letter");
    let text = "";
    for (const letter of letters) {
      text += letter.textContent || "";
    }
    return text;
  }

  function getNextCharFromDOM() {
    const activeWord = getActiveWordElement();
    if (!activeWord) return null;

    const letters = activeWord.querySelectorAll("letter");
    for (const letter of letters) {
      if (
        !letter.classList.contains("correct") &&
        !letter.classList.contains("incorrect")
      ) {
        return letter.textContent || " ";
      }
    }
    // All letters typed -> need space to move to next word
    return " ";
  }

  function isWordComplete() {
    const activeWord = getActiveWordElement();
    if (!activeWord) return false;
    const letters = activeWord.querySelectorAll("letter");
    for (const letter of letters) {
      if (
        !letter.classList.contains("correct") &&
        !letter.classList.contains("incorrect")
      ) {
        return false;
      }
    }
    return true;
  }

  function getWordsToType() {
    const words = [];
    const wordEls = getAllWordElements();
    let foundActive = false;

    for (const el of wordEls) {
      if (el.classList.contains("active")) {
        foundActive = true;
        words.push(getWordText(el));
      } else if (foundActive && !el.classList.contains("typed")) {
        words.push(getWordText(el));
      }
    }
    return words;
  }

  function countTotalWords() {
    return document.querySelectorAll("#words .word").length;
  }

  function focusInput() {
    const input = getInputElement();
    if (input) input.focus();

    // Also click the words wrapper to ensure focus
    const wrapper = document.querySelector("#wordsWrapper");
    if (wrapper) wrapper.click();
  }

  // ===========================================================================
  //  MAIN TYPING LOOP
  // ===========================================================================

  async function typeWordAdvanced(
    inputEl,
    word,
    engine,
    errorEngine,
    wordIndex,
    isLastWord,
    fullWord,
  ) {
    const chars = [...word];
    engine.wordBoundary();
    engine.setWordContext(fullWord || word);
    let i = 0;
    let prevHold = 0;
    let lastTypedChar = null;
    let holdingPrevKey = false;

    while (i < chars.length) {
      if (stopRequested) return;

      const ch = chars[i];
      const prevCh = engine.prevChar;

      // --- Check for errors ---
      if (errorEngine.shouldMakeError(ch, i, word, wordIndex, prevCh)) {
        const errorType = errorEngine.getErrorType(ch, i, word);

        if (errorType === "common_typo" && i === 0) {
          const typoWord =
            COMMON_TYPOS[word.toLowerCase()][
              randInt(0, COMMON_TYPOS[word.toLowerCase()].length - 1)
            ];

          if (holdingPrevKey) {
            releaseAllHeld(inputEl);
            holdingPrevKey = false;
          }
          prevHold = 0;

          for (const tc of typoWord) {
            if (stopRequested) return;
            const delay = engine.computeDelay(tc);
            const hold = engine.computeHold(tc);
            await sleep(Math.max(MIN_SLEEP, delay - prevHold));
            await typeChar(inputEl, tc, hold);
            prevHold = hold;
          }

          if (errorEngine.shouldCorrect()) {
            await sleep(randUniform(...engine.profile.correctionReact));
            prevHold = 0;
            let bsCount = typoWord.length;
            if (errorEngine.shouldOverBackspace()) bsCount += 1;
            for (let b = 0; b < bsCount; b++) {
              if (stopRequested) return;
              const h = engine.computeHold("a");
              await typeBackspace(inputEl, h);
              await sleep(randUniform(...engine.profile.backspaceDelay));
            }
            engine.charInWord = 0;
            prevHold = 0;
            for (const cc of chars) {
              if (stopRequested) return;
              const delay = engine.computeDelay(cc);
              const hold = engine.computeHold(cc);
              await sleep(Math.max(MIN_SLEEP, delay - prevHold));
              await typeChar(inputEl, cc, hold);
              prevHold = hold;
            }
            i = chars.length;
          } else {
            i = chars.length; // leave typo
          }
          continue;
        }

        if (errorType === "transpose" && i < chars.length - 1) {
          if (holdingPrevKey) {
            releaseAllHeld(inputEl);
            holdingPrevKey = false;
          }

          const delay1 = engine.computeDelay(chars[i + 1]);
          const hold1 = engine.computeHold(chars[i + 1]);
          await sleep(Math.max(MIN_SLEEP, delay1 - prevHold));
          await typeChar(inputEl, chars[i + 1], hold1);

          const delay2 = engine.computeDelay(chars[i]);
          const hold2 = engine.computeHold(chars[i]);
          await sleep(Math.max(MIN_SLEEP, delay2 - hold1));
          await typeChar(inputEl, chars[i], hold2);
          prevHold = hold2;

          if (errorEngine.shouldCorrect()) {
            let extraTyped = 0;
            if (errorEngine.shouldDelayNotice() && i + 2 < chars.length) {
              const nExtra = Math.min(
                errorEngine.delayedCharsCount(),
                chars.length - i - 2,
              );
              for (let k = 0; k < nExtra; k++) {
                if (stopRequested) return;
                const ci = i + 2 + k;
                const d = engine.computeDelay(chars[ci]);
                const h = engine.computeHold(chars[ci]);
                await sleep(Math.max(MIN_SLEEP, d - prevHold));
                await typeChar(inputEl, chars[ci], h);
                prevHold = h;
                extraTyped++;
              }
            }

            await sleep(randUniform(...engine.profile.correctionReact));
            prevHold = 0;
            let totalBs = 2 + extraTyped;
            if (errorEngine.shouldOverBackspace()) totalBs += 1;
            for (let b = 0; b < totalBs; b++) {
              if (stopRequested) return;
              const h = engine.computeHold("a");
              await typeBackspace(inputEl, h);
              await sleep(randUniform(...engine.profile.backspaceDelay));
            }
            prevHold = 0;
            const start = totalBs > 2 + extraTyped ? Math.max(0, i - 1) : i;
            for (let ci = start; ci < i + 2 + extraTyped; ci++) {
              if (stopRequested) return;
              if (ci < chars.length) {
                const d = engine.computeDelay(chars[ci]);
                const h = engine.computeHold(chars[ci]);
                await sleep(Math.max(MIN_SLEEP, d - prevHold));
                await typeChar(inputEl, chars[ci], h);
                prevHold = h;
              }
            }
            i = i + 2 + extraTyped;
          } else {
            i += 2;
          }
          continue;
        }

        if (errorType === "adjacent") {
          if (holdingPrevKey) {
            releaseAllHeld(inputEl);
            holdingPrevKey = false;
          }

          const wrong = errorEngine.getAdjacentTypo(ch);
          const delay = engine.computeDelay(wrong);
          const hold = engine.computeHold(wrong);
          await sleep(Math.max(MIN_SLEEP, delay - prevHold));
          await typeChar(inputEl, wrong, hold);
          prevHold = hold;

          if (errorEngine.shouldCorrect()) {
            let extraTyped = 0;
            if (errorEngine.shouldDelayNotice() && i + 1 < chars.length) {
              const nExtra = Math.min(
                errorEngine.delayedCharsCount(),
                chars.length - i - 1,
              );
              for (let k = 0; k < nExtra; k++) {
                if (stopRequested) return;
                const ci = i + 1 + k;
                const d = engine.computeDelay(chars[ci]);
                const h = engine.computeHold(chars[ci]);
                await sleep(Math.max(MIN_SLEEP, d - prevHold));
                await typeChar(inputEl, chars[ci], h);
                prevHold = h;
                extraTyped++;
              }
            }

            await sleep(randUniform(...engine.profile.correctionReact));
            prevHold = 0;
            let totalBs = 1 + extraTyped;
            if (errorEngine.shouldOverBackspace()) totalBs += 1;
            for (let b = 0; b < totalBs; b++) {
              if (stopRequested) return;
              const h = engine.computeHold("a");
              await typeBackspace(inputEl, h);
              await sleep(randUniform(...engine.profile.backspaceDelay));
            }
            prevHold = 0;
            const start = totalBs > 1 + extraTyped ? Math.max(0, i - 1) : i;
            for (let ci = start; ci < i + 1 + extraTyped; ci++) {
              if (stopRequested) return;
              if (ci < chars.length) {
                const d = engine.computeDelay(chars[ci]);
                const h = engine.computeHold(chars[ci]);
                await sleep(Math.max(MIN_SLEEP, d - prevHold));
                await typeChar(inputEl, chars[ci], h);
                prevHold = h;
              }
            }
            i = i + 1 + extraTyped;
          } else {
            i += 1;
          }
          continue;
        }

        if (errorType === "confusion") {
          if (holdingPrevKey) {
            releaseAllHeld(inputEl);
            holdingPrevKey = false;
          }

          const wrong = errorEngine.getConfusionTypo(ch);
          const delay = engine.computeDelay(wrong);
          const hold = engine.computeHold(wrong);
          await sleep(Math.max(MIN_SLEEP, delay - prevHold));
          await typeChar(inputEl, wrong, hold);

          if (errorEngine.shouldCorrect()) {
            await sleep(randUniform(...engine.profile.correctionReact));
            const h = engine.computeHold("a");
            await typeBackspace(inputEl, h);
            await sleep(randUniform(...engine.profile.backspaceDelay));
            const hold2 = engine.computeHold(ch);
            await typeChar(inputEl, ch, hold2);
            prevHold = hold2;
          } else {
            prevHold = hold;
          }
          i += 1;
          continue;
        }

        if (errorType === "double_tap") {
          if (holdingPrevKey) {
            releaseAllHeld(inputEl);
            holdingPrevKey = false;
          }

          const delay = engine.computeDelay(ch);
          const hold = engine.computeHold(ch);
          await sleep(Math.max(MIN_SLEEP, delay - prevHold));
          await typeChar(inputEl, ch, hold);

          const fingerMult = FINGER_HOLD[getFinger(ch)] ?? 1.0;
          const gap = Math.max(
            MIN_SLEEP,
            randGauss(engine.profile.baseDelay * 0.25 * fingerMult, 15),
          );
          await sleep(gap);

          const hold2 = engine.computeHold(ch);
          await typeChar(inputEl, ch, hold2);

          if (errorEngine.shouldCorrect()) {
            await sleep(randUniform(...engine.profile.correctionReact));
            await typeBackspace(inputEl, engine.computeHold("a"));
            prevHold = 0;
          } else {
            prevHold = hold2;
          }
          i += 1;
          continue;
        }

        if (errorType === "skip") {
          // In userscript mode, skipping causes DOM mismatch. Just type normally.
          // Fall through to normal keystroke below.
        }
      }

      // --- Normal keystroke ---
      const delay = engine.computeDelay(ch);
      const hold = engine.computeHold(ch);
      const ikiSleep = Math.max(MIN_SLEEP, delay - prevHold);

      // True key overlap (rollover)
      if (
        engine.shouldOverlap() &&
        engine.prevChar &&
        i > 0 &&
        holdingPrevKey
      ) {
        const ovTime = engine.overlapDuration();
        const effectiveDelay = Math.max(MIN_SLEEP, ikiSleep - ovTime);
        await sleep(effectiveDelay);
        await typeCharWithOverlap(inputEl, ch, hold, ovTime, lastTypedChar);
        holdingPrevKey = true;
        lastTypedChar = ch;
      } else {
        await sleep(ikiSleep);
        if (holdingPrevKey) {
          releaseAllHeld(inputEl);
          holdingPrevKey = false;
        }
        await typeChar(inputEl, ch, hold);
        lastTypedChar = ch;
        // For next potential overlap, mark as holding
        holdingPrevKey = engine.shouldOverlap();
      }

      prevHold = hold;
      i++;
    }

    // Release any held key before space
    if (holdingPrevKey) {
      releaseAllHeld(inputEl);
      holdingPrevKey = false;
    }

    // Space after word (unless last word)
    if (!isLastWord) {
      const spaceDelay =
        engine.profile.baseDelay * randUniform(...engine.profile.spaceGapRange);
      await sleep(Math.max(MIN_SLEEP, spaceDelay - prevHold));
      const spaceHold = engine.computeHold(" ");
      await typeChar(inputEl, " ", spaceHold);

      // Occasional thinking pause
      if (Math.random() < engine.profile.thinkPauseChance) {
        const think =
          engine.profile.baseDelay *
          randUniform(...engine.profile.thinkPauseRange);
        await sleep(think);
      }
    }
  }

  // ===========================================================================
  //  MAIN CONTROLLER
  // ===========================================================================

  async function runTypingSession() {
    if (running) return;
    running = true;
    stopRequested = false;

    const inputEl = getInputElement();
    if (!inputEl) {
      console.log("[MT-Bot] #wordsInput not found");
      running = false;
      return;
    }

    focusInput();
    await sleep(200);

    // Create fresh profile for this session
    const profile = new HumanProfile(TARGET_WPM);
    const totalWords = countTotalWords();
    const engine = new KeystrokeDynamicsEngine(profile, totalWords);
    const errorEngine = new ErrorEngine(profile);

    console.log(
      `[MT-Bot] Starting at ~${TARGET_WPM} WPM (base delay: ${profile.baseDelay.toFixed(1)}ms)`,
    );
    updateStatusUI("TYPING", TARGET_WPM);

    let wordIndex = 0;

    while (!stopRequested) {
      // Check if test is still active
      if (!isTestActive()) {
        console.log("[MT-Bot] Test ended or not active");
        break;
      }

      // Get words to type from DOM
      const words = getWordsToType();
      if (words.length === 0) {
        // Wait for words to load (time mode lazy loading)
        await sleep(50);
        continue;
      }

      // Type the first available word
      const word = words[0];
      if (!word || word.length === 0) {
        await sleep(50);
        continue;
      }

      // Check if this word is already being typed (partially complete)
      // by looking at the active word's letters
      const activeWordEl = getActiveWordElement();
      if (!activeWordEl) {
        await sleep(50);
        continue;
      }

      // Get word state from DOM
      const letters = activeWordEl.querySelectorAll("letter");
      let typedCount = 0;
      let fullWord = "";
      for (const letter of letters) {
        const ch = letter.textContent || "";
        fullWord += ch;
        if (
          letter.classList.contains("correct") ||
          letter.classList.contains("incorrect")
        ) {
          typedCount++;
        }
      }

      if (typedCount >= letters.length) {
        // Word is complete, type space to move to next
        const spaceDelay =
          engine.profile.baseDelay *
          randUniform(...engine.profile.spaceGapRange);
        await sleep(spaceDelay);
        const spaceHold = engine.computeHold(" ");
        await typeChar(inputEl, " ", spaceHold);
        await sleep(30);
        continue;
      }

      // Get only the remaining (untyped) portion of the word
      const remainingWord = fullWord.slice(typedCount);

      // Determine if this is the last word visible
      const isLast = words.length <= 1;
      engine.totalWords = Math.max(totalWords, wordIndex + words.length);

      // Set word context using the full word (for difficulty/chunking)
      // but only type the remaining characters
      await typeWordAdvanced(
        inputEl,
        remainingWord,
        engine,
        errorEngine,
        wordIndex,
        isLast,
        fullWord,
      );
      wordIndex++;

      // Small pause between words for DOM to update
      await sleep(10);
    }

    releaseAllHeld(inputEl);
    running = false;
    updateStatusUI(enabled ? "READY" : "OFF", TARGET_WPM);
    console.log("[MT-Bot] Session ended");
  }

  // ===========================================================================
  //  UI OVERLAY
  // ===========================================================================
  let statusEl = null;

  function createStatusUI() {
    statusEl = document.createElement("div");
    statusEl.id = "mt-bot-status";
    statusEl.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: rgba(30, 30, 30, 0.9);
      color: #ccc;
      font-family: 'Roboto Mono', monospace;
      font-size: 12px;
      padding: 8px 14px;
      border-radius: 6px;
      z-index: 999999;
      user-select: none;
      pointer-events: none;
      border: 1px solid rgba(100, 100, 100, 0.3);
      transition: opacity 0.3s;
    `;
    updateStatusUI("OFF", TARGET_WPM);
    document.body.appendChild(statusEl);
  }

  function updateStatusUI(state, wpm) {
    if (!statusEl) return;
    const colors = {
      OFF: "#666",
      READY: "#4a9",
      TYPING: "#e94",
      ERROR: "#e44",
    };
    const color = colors[state] || "#666";
    statusEl.innerHTML = `<span style="color:${color}">[${state}]</span> ${wpm} WPM | F6: toggle | F7: set WPM`;
  }

  // ===========================================================================
  //  KEYBOARD HANDLER
  // ===========================================================================
  document.addEventListener(
    "keydown",
    function (e) {
      if (e.code === TOGGLE_KEY) {
        e.preventDefault();
        e.stopPropagation();
        if (e.repeat) return;

        enabled = !enabled;
        if (enabled) {
          console.log("[MT-Bot] Enabled");
          updateStatusUI("READY", TARGET_WPM);
          // Start typing if test is active
          if (isTestActive() && !running) {
            runTypingSession();
          }
        } else {
          console.log("[MT-Bot] Disabled");
          stopRequested = true;
          updateStatusUI("OFF", TARGET_WPM);
        }
      }

      if (e.code === WPM_KEY) {
        e.preventDefault();
        e.stopPropagation();
        if (e.repeat) return;

        const input = prompt(
          `Set target WPM (current: ${TARGET_WPM}):`,
          String(TARGET_WPM),
        );
        if (input !== null) {
          const val = parseInt(input, 10);
          if (val >= 1) {
            TARGET_WPM = val;
            updateStatusUI(enabled ? "READY" : "OFF", TARGET_WPM);
            console.log(`[MT-Bot] WPM set to ${TARGET_WPM}`);
          }
        }
      }
    },
    true,
  ); // useCapture to intercept before MonkeyType

  // Auto-start when test becomes active
  const observer = new MutationObserver(() => {
    if (enabled && isTestActive() && !running) {
      // Small delay to let MonkeyType initialize
      setTimeout(() => {
        if (enabled && isTestActive() && !running) {
          runTypingSession();
        }
      }, 300);
    }
  });

  // Wait for DOM, then initialize
  function init() {
    const typingTest = document.querySelector("#typingTest");
    if (typingTest) {
      observer.observe(typingTest, {
        attributes: true,
        attributeFilter: ["class"],
      });
    } else {
      // Retry until #typingTest exists
      setTimeout(init, 500);
      return;
    }
    createStatusUI();
    console.log(
      "[MT-Bot] MonkeyType Human Typer loaded. F6: toggle, F7: set WPM",
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
