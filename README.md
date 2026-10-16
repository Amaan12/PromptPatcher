# PromptPatcher

> **High-speed, non-destructive text and prompt orthography patcher for 140+ WPM typists.**  
> Built to eliminate the Backspace penalty by batch-fixing typos, mechanical motor slips, and phonetic errors in-place without ever altering your sentence structure, tone, or voice.

---

## The Philosophy

When typing at 130–150+ WPM, the biggest bottleneck to raw throughput is the **Backspace penalty**—reaching for Backspace disrupts rhythm, resets motor macros, and introduces 200–400ms of cognitive drag per error.

Traditional tools (like Grammarly) force a slow "hover, click, and review each underlined word" loop that kills momentum. **PromptPatcher** takes the opposite approach:
* Type at full thought-speed without ever backspacing.
* Hit a single hotkey (`Alt + V`).
* The active text field snaps to clean, grammatically sound prose in ~1.5 seconds.
* **Zero AI sanitization:** It will never "elevate" your words or reword your sentences into generic corporate speak.

---

## The Agent Ruleset (System Prompt)

Below is the complete, battle-tested prompt directive used by the **`PromptPatcher`** engine:

```text
Fix all typos, misspellings, grammar, and errors in the text below.

STRICT RULES:

1. CAPITALIZATION & PUNCTUATION:
   - Capitalize the first letter of each sentence and standalone 'I'.
   - Capitalize proper nouns, brands, and product names (e.g., Google Chrome, Windows, Python, GitHub).
   - Ensure proper terminal punctuation (period/full stop, '?', '!') at the end of sentences.
   - Fix punctuation spacing: remove space before punctuation ('word ,' -> 'word,'), ensure space after ('word,word' -> 'word, word').
   - Clamp runaway punctuation ('....' -> '...', '????' -> '?', '!!!!' -> '!').
   - Auto-close any dangling or unclosed parentheses, brackets, or quotes.
   - STRICTLY AVOID the em dash ('—' or '--'); it is an AI giveaway. Use commas, colons, or standard punctuation instead.

2. WORDS, CONTRACTIONS & COMMON SLIPS:
   - Remove accidental duplicate repeated words (e.g., 'that that' -> 'that', 'to to' -> 'to').
   - Fix missing apostrophe homographs based on context (e.g., 'ill do it' -> 'I'll do it', 'well see' -> 'we'll see', 'wont' -> 'won't', 'cant' -> 'can't').
   - Fix phonetic grammar slips (e.g., 'could of' -> 'could have', 'should of' -> 'should have', 'suppose to' -> 'supposed to', 'use to' -> 'used to').
   - Expand casual phonetic text slang into proper words (e.g., 'plz' -> 'please', 'thx' -> 'thanks', 'u' -> 'you', 'r' -> 'are', 'gonna' -> 'going to', 'wanna' -> 'want to').
   - Hyphenate compound modifiers before nouns (e.g., 'real time' -> 'real-time', 'low latency' -> 'low-latency') and format units (e.g., '10gb' -> '10 GB').
   - PRESERVE common acronyms and technical terms (e.g., 'idk', 'tbh', 'afaik', 'api', 's3', 'pr', 'repo', 'json', 'cli').
   - Apply fixes ONLY at the word level. Strictly DO NOT rewrite, rephrase, embellish, or change sentence structure.

3. SPEED & OUTPUT:
   - DO NOT call any tools. Do NOT deliberate or overthink.
   - Output ONLY the raw corrected text with NO conversational filler and NO markdown blocks.
```

---

## What It Fixes vs. What It Protects

| Category | Raw Input | Patched Output |
| :--- | :--- | :--- |
| **Mechanical Inversions** | `typign way to fast on teh keybaord` | `Typing way too fast on the keyboard.` |
| **Motor Stutter** | `i think that that we can can test` | `I think that we can test.` |
| **Missing Apostrophes** | `ill check if its working and well see` | `I'll check if it's working and we'll see.` |
| **Phonetic Slips** | `we could of tested this earlier` | `We could have tested this earlier.` |
| **Casual Slang Expansion** | `plz send the files when u r ready` | `Please send the files when you are ready.` |
| **Acronym Preservation** | `tbh idk if the s3 api is down` | `Tbh idk if the s3 api is down.` |
| **Dangling Brackets & Dots** | `check the config (in the root dir....` | `Check the config (in the root dir).` |
| **Proper Nouns & Units** | `google chrome on 16gb ram` | `Google Chrome on 16 GB RAM.` |
| **Anti-AI Polish** | Strictly **bans em dashes (`—`)** and never rephrases clauses. |

---

## Live Stress-Test Benchmark

### Before Patching (Raw Input)
```text
honestly idk why my google chrome is crashing soooo much today ,but i think my 16gb ram is just completely maxed out. we were suppose to deploy the new python api to aws s3 this mornng, but noone checked the configuration files (like we discussed in the team meetng. i could of pushed the code directly to github ,but ill wait until the team lead looks at the pr because we dont wanna break production again....

also plz tell the devops team that that our low latency database is having major issues with with high speed queries???? well see if they can fix it before tomorrow, but tbh its reallly frstrating when things like this happen without any warning. thx for checking this out and u can let me know when its ready to to test
```

### After Patching (Instant Output)
```text
Honestly, idk why my Google Chrome is crashing so much today, but I think my 16 GB RAM is just completely maxed out. We were supposed to deploy the new Python API to AWS S3 this morning, but no one checked the configuration files (like we discussed in the team meeting). I could have pushed the code directly to GitHub, but I'll wait until the team lead looks at the pr because we don't want to break production again.

Also, please tell the DevOps team that our low-latency database is having major issues with high-speed queries? We'll see if they can fix it before tomorrow, but tbh it's really frustrating when things like this happen without any warning. Thanks for checking this out and you can let me know when it's ready to test.
```

---

## Integration

PromptPatcher is implemented as a lightweight, background Windows daemon listening for `Alt + V` via native Win32 `ctypes` (`RegisterHotKey`, `SendInput`) and dispatched to Gemini Flash via Google Antigravity's headless Agent API (`agentapi`).
