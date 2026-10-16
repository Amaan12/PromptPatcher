import ctypes
from ctypes import wintypes
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

# Win32 API Definitions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Function prototypes for 64-bit safety
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.GetForegroundWindow.argtypes = []
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

# Constants
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_V = 0x56
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key
VK_A = 0x41
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002
WM_HOTKEY = 0x0312
HOTKEY_ID = 101
CREATE_NO_WINDOW = 0x08000000

# Dynamically resolve paths without hardcoded usernames or machine info
USER_HOME = os.path.expanduser("~")
LOCAL_APPDATA = os.environ.get("LOCALAPPDATA", os.path.join(USER_HOME, "AppData", "Local"))

DEFAULT_EXE = os.path.join(LOCAL_APPDATA, "Programs", "antigravity", "resources", "bin", "language_server.exe")
DEFAULT_BRAIN = os.path.join(USER_HOME, ".gemini", "antigravity", "brain")

AGENTAPI_EXE = os.environ.get("ANTIGRAVITY_AGENTAPI_EXE", DEFAULT_EXE)
BRAIN_DIR = os.environ.get("ANTIGRAVITY_APP_DATA_DIR", "")
if BRAIN_DIR:
    BRAIN_DIR = os.path.join(BRAIN_DIR, "brain")
else:
    BRAIN_DIR = DEFAULT_BRAIN


def get_clipboard() -> str:
    """Reads unicode text from the Windows clipboard."""
    for _ in range(10):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return ""

    try:
        h_mem = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_mem:
            return ""
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            return ""
        text = ctypes.wstring_at(p_mem)
        kernel32.GlobalUnlock(h_mem)
        return text
    finally:
        user32.CloseClipboard()


def set_clipboard(text: str) -> bool:
    """Writes unicode text to the Windows clipboard."""
    for _ in range(10):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.02)
    else:
        return False

    try:
        user32.EmptyClipboard()
        encoded = text.encode("utf-16le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        p_mem = kernel32.GlobalLock(h_mem)
        ctypes.memmove(p_mem, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()


def send_key(vk: int, up: bool = False):
    """Simulates a key press or release."""
    flags = KEYEVENTF_KEYUP if up else 0
    user32.keybd_event(vk, 0, flags, 0)


def press_combination(*keys):
    """Presses and releases a combination of keys."""
    for k in keys:
        send_key(k, up=False)
    time.sleep(0.03)
    for k in reversed(keys):
        send_key(k, up=True)
    time.sleep(0.03)


def correct_text_with_agent(text_to_fix: str) -> str:
    """Invokes Antigravity agentapi to fix text errors preserving voice/tone."""
    prompt = (
        "Fix all typos, misspellings, grammar, and syntax errors in the text below.\n"
        "STRICT RULES:\n"
        "1. CAPITALIZATION & PUNCTUATION:\n"
        "   - Capitalize the first letter of each sentence and standalone 'I'.\n"
        "   - Capitalize proper nouns, brands, product names, locations, and days/months (e.g., Google Chrome, Windows, Python, Elm Blvd, Sarah, Friday).\n"
        "   - Ensure proper terminal punctuation (period/full stop, '?', '!') at the end of sentences.\n"
        "   - Fix punctuation spacing: remove space before punctuation ('word ,' -> 'word,'), ensure space after ('word,word' -> 'word, word').\n"
        "   - Clamp runaway punctuation ('....' -> '...', '????' -> '?', '!!!!' -> '!').\n"
        "   - Auto-close any dangling or unclosed parentheses, brackets, or quotes.\n"
        "   - STRICTLY AVOID the em dash ('—' or '--'); it is an AI giveaway. Use commas, colons, or standard punctuation instead.\n"
        "2. COMPREHENSIVE GRAMMAR, TENSE & SYNTAX:\n"
        "   - SUBJECT-VERB AGREEMENT & TENSE CONSISTENCY: Align verbs with their subjects and maintain consistent narrative tense (e.g., 'we tries' -> 'we tried', 'we end up' -> 'we ended up', 'securty take away' -> 'security took away', 'it were' -> 'it was', 'which make no sens' -> 'which makes/made no sense').\n"
        "   - IRREGULAR VERBS & PARTICIPLES: Correct non-standard or missing auxiliary verb forms (e.g., 'we ringed him' -> 'we rang him', 'termites eaten' -> 'termites had eaten' / 'termites ate', 'let you buyed' -> 'let you buy', 'can finded' -> 'could find').\n"
        "   - DOUBLE NEGATIVES: Resolve ungrammatical double negatives cleanly (e.g., 'no one hasn't come' -> 'no one has come', 'nobody never understood' -> 'nobody ever understood').\n"
        "   - CORRELATIVE CONJUNCTIONS: Fix paired conjunctions (e.g., 'neither X or Y' -> 'neither X nor Y', 'either X nor Y' -> 'either X or Y').\n"
        "   - GERUNDS VS. INFINITIVES & ADVERBS: Fix unnatural gerund/infinitive misuse and adjective/adverb confusion (e.g., 'forgot putting sugar' -> 'forgot to put sugar', 'cry very loud' -> 'cry very loudly').\n"
        "   - MISSING NECESSARY WORDS & PREPOSITIONS: Supply missing copulas, auxiliary verbs, or necessary articles (e.g., 'who suposed to' -> 'who was supposed to', 'give us key' -> 'give us the key', 'every bare skin' -> 'every patch of bare skin').\n"
        "   - CONTEXTUAL IDIOMATIC USAGE: Fix distorted idioms or malapropisms (e.g., glass 'scratched into pieces' -> 'shattered into pieces').\n"
        "3. WORDS, CONTRACTIONS & COMMON SLIPS:\n"
        "   - Remove accidental duplicate repeated words (e.g., 'that that' -> 'that', 'to to' -> 'to').\n"
        "   - Fix missing apostrophe homographs and homophones based on context (e.g., 'ill' -> 'I'll', 'well' -> 'we'll', 'wont' -> 'won't', 'cant' -> 'can't', 'its' vs 'it's', 'their' vs 'they're' vs 'there', 'your' vs 'you're', 'then' vs 'than', 'untill mourning' -> 'until morning').\n"
        "   - Fix phonetic grammar slips (e.g., 'could of' -> 'could have', 'should of' -> 'should have', 'suppose to' -> 'supposed to', 'use to' -> 'used to').\n"
        "   - Expand casual phonetic text slang into proper words (e.g., 'plz' -> 'please', 'thx' -> 'thanks', 'u' -> 'you', 'r' -> 'are', 'gonna' -> 'going to').\n"
        "   - Hyphenate compound modifiers before nouns (e.g., 'real time' -> 'real-time', 'low latency' -> 'low-latency') and format units (e.g., '10gb' -> '10 GB', '3 ounces' -> '3 oz').\n"
        "   - PRESERVE common acronyms and technical terms (e.g., 'idk', 'tbh', 'afaik', 'api', 's3', 'pr', 'repo', 'json', 'cli').\n"
        "   - DO NOT rewrite, rephrase unnecessarily, embellish, or change conversational voice.\n"
        "4. SPEED & OUTPUT:\n"
        "   - DO NOT call any tools. Do NOT deliberate or overthink.\n"
        "   - Output ONLY the raw corrected text with NO conversational filler and NO markdown blocks.\n\n"
        "Text to fix:\n"
        f"{text_to_fix}"
    )


    cmd = [
        AGENTAPI_EXE,
        "agentapi",
        "new-conversation",
        "--model=flash_lite",
        "--title=[Alt+V Fix]",
        prompt,
    ]

    try:
        # Run with CREATE_NO_WINDOW so it never steals focus from the active app
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            creationflags=CREATE_NO_WINDOW
        )
        data = json.loads(res.stdout)
        conv_id = data.get("response", {}).get("newConversation", {}).get("conversationId")
        if not conv_id:
            return ""

        transcript_path = os.path.join(BRAIN_DIR, conv_id, ".system_generated", "logs", "transcript.jsonl")

        # Poll transcript for up to 15 seconds
        for _ in range(150):
            time.sleep(0.1)
            if not os.path.exists(transcript_path):
                continue
            with open(transcript_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                try:
                    record = json.loads(line)
                    if record.get("source") == "MODEL" and record.get("type") == "PLANNER_RESPONSE":
                        content = record.get("content", "").strip()
                        if content:
                            code_match = re.search(r"```(?:\w+)?\s*(.*?)\s*```", content, re.DOTALL)
                            if code_match:
                                return code_match.group(1).strip()
                            return content
                except Exception:
                    pass
        return ""
    except Exception as e:
        print(f"[Error in correction] {e}", file=sys.stderr, flush=True)
        return ""


def on_hotkey_pressed():
    """Handler executed when Ctrl + Alt + V is detected."""
    print("[Ctrl+Alt+V Triggered] Processing active text...", flush=True)

    # 1. Capture the target window currently in the foreground
    target_hwnd = user32.GetForegroundWindow()

    # 2. Release Ctrl, Alt, and V physically so they don't interfere with Ctrl+C/V
    send_key(VK_CONTROL, up=True)
    send_key(VK_MENU, up=True)
    send_key(VK_V, up=True)
    time.sleep(0.06)

    # 3. Backup current clipboard
    old_clipboard = get_clipboard()

    # 4. Try copying active selection first
    set_clipboard("")  # Clear clipboard so we can detect if Ctrl+C writes anything
    time.sleep(0.02)
    press_combination(VK_CONTROL, VK_C)
    time.sleep(0.08)

    selected_text = get_clipboard()

    # 5. If nothing was selected, select all and copy (Hybrid mode)
    if not selected_text.strip():
        press_combination(VK_CONTROL, VK_A)
        time.sleep(0.04)
        press_combination(VK_CONTROL, VK_C)
        time.sleep(0.08)
        selected_text = get_clipboard()

    if not selected_text.strip():
        print("[Alt+V] No text found in active field.", flush=True)
        set_clipboard(old_clipboard)
        return

    print(f"[Alt+V] Input captured ({len(selected_text)} chars): {selected_text[:60]!r}...", flush=True)

    # 6. Send to Antigravity Flash Lite
    start_time = time.time()
    corrected = correct_text_with_agent(selected_text)
    duration = time.time() - start_time

    if not corrected or corrected == selected_text:
        print(f"[Alt+V] No changes needed or failed ({duration:.2f}s).", flush=True)
        set_clipboard(old_clipboard)
        return

    print(f"[Alt+V] Corrected in {duration:.2f}s! Result: {corrected!r}", flush=True)

    # 7. Ensure target window is foreground before pasting
    if target_hwnd:
        user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.05)

    # 8. Put corrected text on clipboard
    set_clipboard(corrected)
    time.sleep(0.05)

    # 9. Paste (Ctrl + V)
    press_combination(VK_CONTROL, VK_V)
    time.sleep(0.1)

    print("[Alt+V] Pasted cleanly back to active window!", flush=True)


def monitor_parent_and_antigravity():
    """Watches the parent process and Antigravity language server.
    Exits cleanly if Antigravity or the parent process terminates.
    """
    parent_pid = os.getppid()
    SYNCHRONIZE = 0x00100000
    h_parent = kernel32.OpenProcess(SYNCHRONIZE, False, parent_pid)

    ls_addr = os.environ.get("ANTIGRAVITY_LS_ADDRESS", "")
    fail_count = 0

    while True:
        time.sleep(2.0)

        # 1. Check parent process alive
        if h_parent:
            # WaitForSingleObject with 0ms timeout: WAIT_OBJECT_0 (0) means terminated
            wait_res = kernel32.WaitForSingleObject(h_parent, 0)
            if wait_res == 0:
                print("[Alt+V Daemon] Parent process terminated. Shutting down.", flush=True)
                os._exit(0)

        # 2. Check Antigravity language server heartbeat if address is known
        if ls_addr:
            try:
                req = urllib.request.Request(f"http://{ls_addr}/healthz")
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        fail_count = 0
            except Exception:
                fail_count += 1
                if fail_count >= 3:
                    print("[Alt+V Daemon] Antigravity language server disconnected. Shutting down.", flush=True)
                    os._exit(0)


def main():
    print("=" * 60)
    print("  Antigravity Text Correction Daemon Active")
    print(f"  AgentAPI Binary: {AGENTAPI_EXE}")
    print(f"  Brain Directory: {BRAIN_DIR}")
    print("  Press Ctrl + Alt + V anywhere in Windows to fix typos & errors.")
    print("=" * 60, flush=True)

    # Start parent & Antigravity lifecycle monitor thread
    monitor_thread = threading.Thread(target=monitor_parent_and_antigravity, daemon=True)
    monitor_thread.start()

    # Retry registering hotkey if previous instance is still releasing it
    registered = False
    for attempt in range(15):
        if user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, VK_V):
            registered = True
            break
        time.sleep(0.5)

    if not registered:
        err = kernel32.GetLastError()
        print(f"[Error] Failed to register Ctrl + Alt + V hotkey (Error code: {err})", file=sys.stderr, flush=True)
        sys.exit(1)

    print("[Text Fixer Daemon] Hotkey Ctrl + Alt + V registered successfully.", flush=True)


    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                # Handle in a background thread so the Windows message loop doesn't stall
                threading.Thread(target=on_hotkey_pressed, daemon=True).start()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)
        print("[Alt+V Daemon Stopped]", flush=True)


if __name__ == "__main__":
    main()

