# APPLICATION FLOW SPECIFICATION

## JARVIS-Lite: Complete Flow Documentation

---

## 1. HIGH-LEVEL USER FLOW

### 1.1 User Journey Map

```
┌─────────────────────────────────────────────────────────────┐
│                    USER EXPERIENCE FLOW                      │
└─────────────────────────────────────────────────────────────┘

[START] User launches app
    ↓
[INIT] Loading screen (3-5 seconds)
    ├─ Load Whisper model
    ├─ Load spaCy NLP
    ├─ Initialize audio devices
    └─ Load configuration
    ↓
[READY] "JARVIS ready. Press SPACE to speak."
    ↓
┌───────────── MAIN LOOP ─────────────┐
│                                     │
│ [IDLE] Waiting for activation      │
│    ↓ (User holds SPACE)            │
│ [LISTENING] "Listening..."          │
│    ↓ (User speaks: "open chrome")  │
│ [PROCESSING] "Processing..."        │
│    ↓                                │
│ [EXECUTING] Chrome launches         │
│    ↓                                │
│ [RESPONDING] "Opened Chrome"        │
│    ↓                                │
│ [IDLE] Back to waiting              │
│    ↑                                │
└─────────────┘                       │
    │                                 │
    └─ (User presses ESC) → [EXIT]   │
```

---

## 2. DETAILED STATE MACHINE

### 2.1 System States

```
┌────────────────────────────────────────────────────────────┐
│                   STATE MACHINE DIAGRAM                     │
└────────────────────────────────────────────────────────────┘

States:
1. INITIALIZING
2. IDLE
3. LISTENING
4. TRANSCRIBING
5. PARSING
6. CLARIFYING (optional)
7. EXECUTING
8. RESPONDING
9. ERROR
10. SHUTTING_DOWN

Transitions:
INITIALIZING → IDLE (on success)
INITIALIZING → ERROR (on failure)

IDLE → LISTENING (on push-to-talk trigger)
IDLE → SHUTTING_DOWN (on exit command)

LISTENING → TRANSCRIBING (on audio captured)
LISTENING → IDLE (on timeout/silence)

TRANSCRIBING → PARSING (on STT success)
TRANSCRIBING → ERROR (on STT failure)

PARSING → EXECUTING (on clear intent)
PARSING → CLARIFYING (on ambiguous intent)
PARSING → ERROR (on unknown intent)

CLARIFYING → LISTENING (await user response)

EXECUTING → RESPONDING (on success)
EXECUTING → ERROR (on execution failure)

RESPONDING → IDLE (on TTS complete)
RESPONDING → LISTENING (on push-to-talk barge-in / interrupt)

ERROR → IDLE (after error message spoken)

SHUTTING_DOWN → [EXIT]
```

### 2.2 State Details

#### STATE: INITIALIZING

**Entry Actions:**
```python
1. Display "Initializing JARVIS-Lite..."
2. Load Whisper model (base, ~140MB)
   - Progress: "Loading speech recognition... 25%"
3. Load spaCy model (en_core_web_sm, ~40MB)
   - Progress: "Loading language processor... 50%"
4. Initialize audio devices
   - Test microphone availability
   - Test speaker availability
   - Progress: "Checking audio devices... 75%"
5. Load configuration (config/settings.json)
   - Whitelist directories
   - Command mappings
   - Progress: "Loading configuration... 90%"
6. Initialize TTS engine (pyttsx3)
   - Progress: "Initializing voice... 100%"
7. Create empty context object
8. Load Core Beliefs into context (from core_memory.sqlite)
```

**Exit Conditions:**
- ✅ Success → Transition to IDLE
- ❌ Failure → Transition to ERROR with specific message

**Typical Duration:** 3-5 seconds

---

#### STATE: IDLE

**Visual Indicator:** 
```
[JARVIS] Ready. Press SPACE to speak (or type 'help')
> _
```

**Behavior:**
- Listen for keyboard input (push-to-talk or text command)
- No CPU-intensive operations (idle <5% CPU)
- Context persists from previous command

**Transitions:**
```python
# Windows: SPACE is captured via pywin32 SetWindowsHookEx global hook
# (works even when another app has focus)
# macOS/Linux: keyboard library is sufficient
if ptt_key_pressed():          # platform-specific global hook
    transition_to(LISTENING)
elif user_typed_text():
    text = get_text_input()
    transition_to(PARSING, text=text)  # Skip STT
elif user_typed('exit') or user_typed('quit'):
    transition_to(SHUTTING_DOWN)
```

---

#### STATE: LISTENING

**Visual Indicator:**
```
🎤 Listening... (release SPACE when done)
```

**Behavior:**
```python
1. Start audio recording (16kHz, mono)
2. Real-time visualization (ASCII waveform):
   "████████▌▌▌▌▌▌▌████████"
3. Voice Activity Detection (VAD):
   - Silence detection (800ms threshold)
   - Max duration: 10 seconds
4. Buffer audio to memory
5. Phase 2 (LLM): Explicitly unload LLM from VRAM to make room for Whisper STT
```

**Exit Conditions:**
```python
if space_released:
    audio_data = stop_recording()
    transition_to(TRANSCRIBING, audio=audio_data)
elif silence_detected(800ms):
    audio_data = stop_recording()
    transition_to(TRANSCRIBING, audio=audio_data)
elif timeout(10s):
    stop_recording()
    transition_to(IDLE, error="Timeout")
```

**Typical Duration:** 2-5 seconds

---

#### STATE: TRANSCRIBING

**Visual Indicator:**
```
💭 Processing speech...
```

**Behavior:**
```python
def transcribe_audio(audio_data):
    try:
        # Primary: Whisper
        result = whisper_model.transcribe(audio_data)
        text = result['text'].strip()
        confidence = result.get('confidence', 0.0)
        
        if confidence > 0.7:
            return text, "whisper"
    except Exception as e:
        log_error(e)
    
    try:
        # Fallback: Vosk (if Whisper fails)
        text = vosk_recognize(audio_data)
        return text, "vosk"
    except Exception as e:
        return None, None
```

**Exit Conditions:**
```python
if text is not None:
    print(f"You: {text}")
    
    # F1.7 — STT Confirmation Display
    # Show transcription for 1.5s before executing.
    # Allows user to cancel mis-transcriptions via ESC.
    print(f"  I heard: '{text}'  (ESC to cancel)")
    if wait_for_cancel(timeout=1.5):   # returns True if ESC pressed
        speak("Cancelled.")
        transition_to(IDLE)
    else:
        transition_to(PARSING, text=text)
else:
    speak("Sorry, I didn't catch that.")
    transition_to(IDLE)
```

**Typical Duration:** hardware-dependent (see PRD §6.1 tiered STT targets)

---

#### STATE: PARSING

**Visual Indicator:**
```
🧠 Understanding command...
```

**Behavior:**
```python
# Phase 2 VRAM Orchestration:
# If LLM is active, move Whisper to CPU RAM, and explicitly reload the LLM into VRAM

def parse_intent(text, context):
    """
    Intent parsing with correct priority order.
    
    CRITICAL: The clarification check MUST come before any fresh parse.
    If context.awaiting_clarification is True and we attempt a fresh parse,
    "the second one" will match UNKNOWN instead of resolving to clarification[1].
    """
    text_lower = text.lower()
    
    # STEP 1 — Clarification resolution (MUST be first)
    if context.awaiting_clarification:
        resolved = resolve_clarification(text, context)
        if resolved:
            context.clear_clarification()
            return resolved
        else:
            speak("I couldn't match that. Say the number (1, 2, 3) or the name.")
            # Stay in clarification state — return to LISTENING
            return None
    
    # STEP 2 — UNDO / REPEAT short-circuit (no NLP needed)
    if any(w in text_lower for w in ['undo', 'reverse that', 'go back']):
        return {'intent': 'undo', 'confidence': 0.99}
    if any(w in text_lower for w in ['do that again', 'repeat', 'again']):
        return {'intent': 'repeat', 'confidence': 0.99}
    
    # STEP 3 — Context-aware reference resolution
    # "open the first one" → resolve against last_search_results
    if context.get_variable('last_search_results'):
        resolved = resolve_reference(text_lower, context)
        if resolved:
            return resolved
    
    # STEP 4 — Pattern matching (intent detection)
    intent = None
    
    # File operations
    if any(verb in text_lower for verb in ['open', 'launch', 'start']):
        if any(app in text_lower for app in ['chrome', 'browser', 'firefox']):
            intent = {
                'intent': 'open_app',
                'entity': extract_app_name(text),
                'confidence': 0.95
            }
        elif 'file' in text_lower or extract_filename(text):
            intent = {
                'intent': 'open_file',
                'entity': extract_filename(text),
                'location': extract_location(text) or 'auto',
                'confidence': 0.9
            }
    
    # Search operations
    elif any(verb in text_lower for verb in ['find', 'search', 'locate']):
        intent = {
            'intent': 'search_files',
            'query': extract_search_query(text),
            'location': extract_location(text),
            'confidence': 0.85
        }
    
    # System commands
    elif 'volume' in text_lower:
        intent = {
            'intent': 'adjust_volume',
            'action': 'up' if 'up' in text_lower else 'down',
            'confidence': 0.95
        }
    
    # STEP 5 — Confidence floor handling
    if intent and 0.5 <= intent['confidence'] < 0.8:
        # Don't fail silently — ask for confirmation
        return {
            'intent': intent['intent'],
            'entity': intent.get('entity'),
            'confidence': intent['confidence'],
            'below_confidence_floor': True,   # Caller speaks "Did you mean X?"
        }
    
    # STEP 6 — Hard threshold / return unknown
    if intent and intent['confidence'] >= 0.8:
        return intent
    else:
        return {
            'intent': 'unknown',
            'original_text': text,
            'confidence': 0.0
        }
```

**Exit Conditions:**
```python
if parse_result is None:
    # Still in clarification — transition back to LISTENING
    transition_to(LISTENING)
elif parse_result.get('below_confidence_floor'):
    speak(f"Did you mean '{parse_result['intent'].replace('_', ' ')}'? Say yes to confirm.")
    context.set_variable('pending_confirmation', parse_result)
    transition_to(LISTENING)  # Wait for yes/no
elif parse_result['confidence'] >= 0.8:
    transition_to(EXECUTING, intent=parse_result)
elif parse_result['intent'] == 'unknown':
    speak("I didn't understand. Try 'open chrome' or say 'help'.")
    transition_to(IDLE)
elif requires_clarification(parse_result):
    transition_to(CLARIFYING, intent=parse_result)
```

**Typical Duration:** 0.1-0.3 seconds

---

#### STATE: CLARIFYING

**Visual Indicator:**
```
❓ Need more information...
```

**Behavior:**
```python
def handle_clarification(intent, context):
    """
    Ask user to disambiguate when multiple matches found
    """
    if intent['intent'] == 'open_file':
        query = intent['entity']
        matches = search_files(query)
        
        if len(matches) == 0:
            return None, f"No files found matching '{query}'"
        
        elif len(matches) == 1:
            # Auto-select single match
            intent['entity'] = matches[0]
            return intent, None
        
        else:
            # Multiple matches - ask user
            context.awaiting_clarification = True
            context.clarification_options = matches
            context.clarification_intent = intent
            
            message = f"Found {len(matches)} files:\n"
            for i, file in enumerate(matches[:5], 1):
                message += f"  {i}. {file}\n"
            message += "Say the number or filename."
            
            return None, message
```

**Exit Conditions:**
```python
if clarification_message:
    speak(clarification_message)
    transition_to(LISTENING)  # Wait for user response
else:
    transition_to(EXECUTING, intent=intent)
```

**Example Flow:**
```
User: "Open my resume"
System: "Found 3 files:
  1. resume.pdf
  2. resume_2024.pdf
  3. resume_old.pdf
Say the number or filename."

[Context stores: awaiting_clarification=True, options=[...]]

User: "two" or "the second one" or "resume 2024"
System: [Resolves to resume_2024.pdf]
System: "Opening resume_2024.pdf"
```

---

#### STATE: EXECUTING

**Visual Indicator:**
```
⚙️  Executing command...
```

**Behavior:**
```python
def execute_intent(intent, context):
    """
    Map intent to actual system command.
    MUST update context after execution for reference resolution.
    """
    action_map = {
        'open_app': execute_open_app,
        'open_file': execute_open_file,
        'search_files': execute_search_files,
        'adjust_volume': execute_volume_control,
        'close_app': execute_close_app,
        'screenshot': execute_screenshot,
        'lock_screen': execute_lock_screen,
        'undo': execute_undo,
        'repeat': execute_repeat,
        'macro': execute_macro,
    }
    
    handler = action_map.get(intent['intent'])
    
    if not handler:
        return False, f"No handler for {intent['intent']}"
    
    try:
        # Security check
        if not validate_safe_execution(intent):
            return False, "Command blocked for safety"
        
        # Execute with timeout
        result = timeout_wrapper(handler, intent, context, timeout=5)
        
        # --- Context variable writes (MUST happen after successful execution) ---
        if intent['intent'] == 'search_files' and result.data:
            context.set_variable('last_search_results', result.data.get('files', []))
        if intent['intent'] == 'open_file' and result.success:
            context.set_variable('last_opened_file', intent.get('entity'))
        if intent['intent'] == 'open_app' and result.success:
            context.set_variable('last_opened_app', intent.get('entity'))
        # Always store last successful intent for undo/repeat
        if result.success:
            context.last_intent = intent
        # ---
        
        return True, result
        
    except TimeoutError:
        return False, "Command timed out"
    except PermissionError:
        return False, "Permission denied"
    except Exception as e:
        return False, f"Error: {str(e)}"
```

**Example Execution Functions:**

```python
def execute_open_file(intent):
    """Open file in default application"""
    filename = intent['entity']
    location = intent.get('location', 'auto')
    
    # Auto-search if location not specified
    if location == 'auto':
        matches = search_files(filename, limit=1)
        if not matches:
            return f"File not found: {filename}"
        filepath = matches[0]
    else:
        filepath = os.path.join(get_path(location), filename)
    
    # Open file (cross-platform)
    if sys.platform == 'win32':
        os.startfile(filepath)
    elif sys.platform == 'darwin':
        subprocess.run(['open', filepath])
    else:
        subprocess.run(['xdg-open', filepath])
    
    return f"Opened {os.path.basename(filepath)}"

def execute_open_app(intent):
    """Launch application"""
    app_name = intent['entity'].lower()
    
    # Application mapping
    app_commands = {
        'chrome': {'win': 'chrome', 'mac': 'Google Chrome', 'linux': 'google-chrome'},
        'vscode': {'win': 'code', 'mac': 'Visual Studio Code', 'linux': 'code'},
        'terminal': {'win': 'cmd', 'mac': 'Terminal', 'linux': 'gnome-terminal'},
        # ... more apps
    }
    
    if app_name not in app_commands:
        return f"Unknown application: {app_name}"
    
    platform = 'win' if sys.platform == 'win32' else 'mac' if sys.platform == 'darwin' else 'linux'
    command = app_commands[app_name][platform]
    
    if sys.platform == 'darwin':
        subprocess.Popen(['open', '-a', command])
    else:
        subprocess.Popen([command])
    
    return f"Launched {app_name}"
```

**Exit Conditions:**
```python
success, result_message = execute_intent(intent)

if success:
    transition_to(RESPONDING, message=result_message)
else:
    transition_to(ERROR, message=result_message)
```

**Typical Duration:** 0.2-1 second

---

#### STATE: RESPONDING

**Visual Indicator:**
```
🤖 JARVIS: Opened Chrome
```

**Behavior:**
```python
def speak_response(message):
    """
    Text-to-speech output
    """
    # Visual output
    print(f"🤖 JARVIS: {message}")
    
    # Audio output
    engine.say(message)
    engine.runAndWait()  # Blocking call
    
    # Log to history
    context.add_turn('assistant', message)
```

**Exit Conditions:**
```python
# If barge-in (SPACE key) triggered during TTS:
if tts_interrupt_flag.is_set():
    transition_to(LISTENING)
else:
    # Always return to idle after speaking finishes
    transition_to(IDLE)
```

**Typical Duration:** 1-3 seconds (depending on message length)

---

#### STATE: ERROR

**Visual Indicator:**
```
❌ Error: File not found
```

**Behavior:**
```python
def handle_error(error_message, error_type='user'):
    """
    User-friendly error handling
    """
    # Log technical details
    logger.error(f"{error_type}: {error_message}")
    
    # Speak user-friendly message
    friendly_messages = {
        'file_not_found': "I couldn't find that file. Try being more specific.",
        'permission_denied': "I don't have permission to do that.",
        'timeout': "That took too long. Please try again.",
        'unknown_command': "I didn't understand. Say 'help' for examples.",
        'audio_device': "Microphone not available. Check your audio settings.",
    }
    
    user_message = friendly_messages.get(error_type, error_message)
    
    print(f"❌ Error: {user_message}")
    speak(user_message)
```

**Exit Conditions:**
```python
# Always return to idle after error
transition_to(IDLE)
```

**Typical Duration:** 1-2 seconds

---

#### STATE: SHUTTING_DOWN

**Visual Indicator:**
```
👋 Goodbye!
```

**Behavior:**
```python
def cleanup_and_exit():
    """
    Graceful shutdown
    """
    # 1. Save context (if configured)
    if config.save_history:
        context.save_to_file('logs/last_session.json')
    
    # 2. Close audio streams
    audio_stream.stop()
    audio_stream.close()
    
    # 3. Unload models (free memory)
    whisper_model = None
    nlp = None
    
    # 4. Goodbye message
    speak("Goodbye!")
    
    # 5. Exit
    sys.exit(0)
```

**Typical Duration:** 1 second

---

## 3. TECHNICAL EXECUTION FLOW

### 3.1 Sequence Diagram: Successful Command

```
User          CLI         Audio       STT         NLP         Executor    TTS
 │             │            │           │           │            │          │
 ├─ Press SPACE ──────────→│           │           │            │          │
 │             │            │           │           │            │          │
 │             │←─── "Listening..." ───┤           │            │          │
 │             │            │           │           │            │          │
 ├─ Speak ─────────────────→│           │           │            │          │
 │  "open chrome"           │           │           │            │          │
 │             │            │           │           │            │          │
 ├─ Release SPACE ─────────→│           │           │            │          │
 │             │            │           │           │            │          │
 │             │            ├─ Stop recording       │            │          │
 │             │            │           │           │            │          │
 │             │            ├─ Send audio ─────────→│           │            │
 │             │            │           │           │            │          │
 │             │            │           ├─ Transcribe (1.5s)     │          │
 │             │            │           │           │            │          │
 │             │            │           ├─ Return "open chrome" │            │
 │             │            │           │           │            │          │
 │             │←────────────────── "You: open chrome" ──────────┤          │
 │             │            │           │           │            │          │
 │             │            │           │           ├─ Parse intent         │
 │             │            │           │           │            │          │
 │             │            │           │           ├─ Return {intent: "open_app",...}
 │             │            │           │           │            │          │
 │             │            │           │           │            ├─ Execute │
 │             │            │           │           │            │  (launch Chrome)
 │             │            │           │           │            │          │
 │             │            │           │           │            ├─ Return "Opened Chrome"
 │             │            │           │           │            │          │
 │             │            │           │           │            │          ├─ Speak
 │             │            │           │           │            │          │  (0.8s)
 │             │            │           │           │            │          │
 │             │←──────────────────────────────── "🤖 Opened Chrome" ───────┤
 │             │            │           │           │            │          │
 │             │←─── "Press SPACE to speak" ───────────────────────────────┤
 │             │            │           │           │            │          │
```

**Total Time:** ~3.5 seconds (1.5s STT + 0.2s parse + 0.3s execute + 0.8s TTS)

---

### 3.2 Sequence Diagram: Clarification Flow

```
User          CLI         Audio       STT         NLP         FileSearch  TTS
 │             │            │           │           │            │          │
 ├─ "open my resume" ──────────────────→│           │            │          │
 │             │            │           │           │            │          │
 │             │            │           ├─ Transcribe            │          │
 │             │            │           │           │            │          │
 │             │            │           ├─ Parse "open_file" ───→│          │
 │             │            │           │           │            │          │
 │             │            │           │           ├─ Search "resume" ────→│
 │             │            │           │           │            │          │
 │             │            │           │           │←─── Found 3 matches ──┤
 │             │            │           │           │            │          │
 │             │            │           │           ├─ Clarification needed │
 │             │            │           │           │            │          │
 │             │←──── "Found 3 files: 1. resume.pdf, 2. resume_2024.pdf..." │
 │             │            │           │           │            │          │
 │             │            │           │           │ [Context stores options]
 │             │            │           │           │            │          │
 ├─ "the second one" ───────────────────→│           │            │          │
 │             │            │           │           │            │          │
 │             │            │           ├─ Transcribe            │          │
 │             │            │           │           │            │          │
 │             │            │           ├─ Resolve from context ─┤          │
 │             │            │           │           │            │          │
 │             │            │           │           ├─ Select resume_2024.pdf
 │             │            │           │           │            │          │
 │             │            │           │           ├─ Execute open         │
 │             │            │           │           │            │          │
 │             │←──── "Opened resume_2024.pdf" ──────────────────────────── │
 │             │            │           │           │            │          │
```

---

### 3.3 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     DATA FLOW ARCHITECTURE                    │
└──────────────────────────────────────────────────────────────┘

[Raw Audio] (PCM, 16kHz, mono)
    ↓
┌─────────────────┐
│ Audio Buffer    │ (3-10 seconds)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Whisper STT     │ → [Text String] "open chrome"
└────────┬────────┘
         ↓
┌─────────────────┐
│ Intent Parser   │ → [Intent JSON]
└────────┬────────┘    {
         │               "intent": "open_app",
         │               "entity": "chrome",
         │               "confidence": 0.95
         ↓            }
┌─────────────────┐
│ Context Manager │ ← [Previous Context]
└────────┬────────┘    {
         │               "history": [...],
         │               "awaiting_clarification": false
         ↓            }
┌─────────────────┐
│ Validator       │ → [Validated Intent]
└────────┬────────┘    (Security check passed)
         ↓
┌─────────────────┐
│ Executor        │ → [Result]
└────────┬────────┘    "Opened Chrome"
         ↓
┌─────────────────┐
│ TTS Engine      │ → [Audio Output]
└─────────────────┘    (Spoken response)
```

---

## 4. CONTEXT MANAGEMENT FLOW

### 4.1 Context Object Structure

```python
class ConversationContext:
    def __init__(self):
        self.history = []  # List of {role, content, timestamp}
        self.variables = {}  # Temporary state storage
        self.awaiting_clarification = False
        self.clarification_options = []
        self.last_intent = None
        self.last_parameters = {}
    
    def add_turn(self, role, content):
        """Add message to history"""
        self.history.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep last 20 exchanges only
        if len(self.history) > 40:  # 20 exchanges = 40 messages
            self.history = self.history[-40:]
    
    def set_clarification(self, intent, options):
        """Store clarification state"""
        self.awaiting_clarification = True
        self.clarification_options = options
        self.last_intent = intent
    
    def resolve_clarification(self, user_response):
        """Resolve user's clarification response"""
        # Try number (1, 2, 3)
        if user_response.isdigit():
            index = int(user_response) - 1
            if 0 <= index < len(self.clarification_options):
                selected = self.clarification_options[index]
                self.clear_clarification()
                return selected
        
        # Try fuzzy match
        from difflib import get_close_matches
        matches = get_close_matches(user_response, 
                                    self.clarification_options, 
                                    n=1, 
                                    cutoff=0.6)
        if matches:
            self.clear_clarification()
            return matches[0]
        
        return None
    
    def clear_clarification(self):
        """Reset clarification state"""
        self.awaiting_clarification = False
        self.clarification_options = []
    
    def get_variable(self, key, default=None):
        """Retrieve context variable"""
        return self.variables.get(key, default)
    
    def set_variable(self, key, value):
        """Store context variable"""
        self.variables[key] = value
```

### 4.2 Context Flow Example

```python
# Example: Multi-turn file search and open

# Turn 1
user_input = "find my python files"
intent = {
    'intent': 'search_files',
    'query': '*.py',
    'location': 'auto'
}
results = ['/home/user/project/main.py', '/home/user/script.py', ...]
context.set_variable('last_search_results', results)
context.add_turn('user', user_input)
context.add_turn('assistant', f"Found {len(results)} Python files.")

# Turn 2
user_input = "open the first one"
# Parser checks: context.get_variable('last_search_results')
# Resolves "first one" → results[0]
intent = {
    'intent': 'open_file',
    'entity': results[0],
    'location': 'explicit'
}
execute(intent)
context.add_turn('user', user_input)
context.add_turn('assistant', "Opened main.py")
```

---

## 5. ERROR HANDLING FLOWS

### 5.1 Error Recovery Decision Tree

```
                    [ERROR OCCURS]
                          │
                    ┌─────┴─────┐
                    │           │
            [User Error]   [System Error]
                 │              │
        ┌────────┼────────┐     │
        │        │        │     │
   [Unknown] [Ambiguous] [Not   │
   Command]   [Input]   Found]  │
        │        │        │     │
        ├────────┴────────┘     │
        │                       │
  [Speak friendly         ┌─────┴─────┐
   error message]         │           │
        │            [Recoverable] [Critical]
   [Return to              │           │
    IDLE state]       [Try again] [Attempt
                       with lower   restart]
                       quality]       │
                           │          │
                      [Success]  [Shutdown
                           │      with log]
                      [Continue]     │
                           │     [Exit with
                      [Normal    error code]
                       flow]
```

### 5.2 Specific Error Scenarios

#### Scenario 1: STT Failure

```python
def handle_stt_failure(audio_data, error):
    """
    Handle speech-to-text failure
    """
    # Try fallback engine
    if whisper_failed and vosk_available:
        try:
            text = vosk_transcribe(audio_data)
            return text
        except:
            pass
    
    # Both failed - ask user to repeat
    speak("Sorry, I didn't catch that. Please try again.")
    return None
```

#### Scenario 2: File Not Found

```python
def handle_file_not_found(filename):
    """
    Handle file not found error
    """
    # Try fuzzy search
    similar = fuzzy_search_files(filename, cutoff=0.6)
    
    if similar:
        if len(similar) == 1:
            # Auto-correct
            speak(f"Did you mean {similar[0]}? Opening it.")
            return similar[0]
        else:
            # Offer suggestions
            context.set_clarification({
                'intent': 'open_file',
                'entity': filename
            }, similar)
            speak(f"File '{filename}' not found. Did you mean: {', '.join(similar[:3])}?")
            return None
    else:
        speak(f"I couldn't find any file matching '{filename}'.")
        return None
```

#### Scenario 3: Command Timeout

```python
def handle_timeout(command):
    """
    Handle execution timeout
    """
    speak("That's taking longer than expected. Still working on it...")
    
    # Extend timeout once
    try:
        result = execute_with_timeout(command, timeout=10)
        return result
    except TimeoutError:
        speak("The command timed out. You may need to check manually.")
        log_error(f"Timeout: {command}")
        return None
```

#### Scenario 4: Microphone Not Available

```python
def handle_audio_error():
    """
    Handle audio device failure
    """
    speak("Microphone not available. Switching to text mode.")
    print("\n[Text Mode] Type your command:")
    
    while True:
        text_input = input("> ")
        if text_input.lower() in ['exit', 'quit']:
            break
        
        # Process text directly (skip STT)
        process_text_command(text_input)
```

---

## 6. EDGE CASES & SPECIAL FLOWS

### 6.1 Help Command Flow

```
User: "help"
    ↓
[Parse] → intent = 'show_help'
    ↓
[Execute] → Display command examples
    ↓
System: "Available commands:
  - 'open [app]' - Launch application
  - 'open [file]' - Open file
  - 'find [query]' - Search files
  - 'volume up/down' - Adjust volume
  - 'exit' - Quit
  
  Try saying: 'open chrome'"
```

### 6.2 Undo Flow (`IntentType.UNDO`)

**Trigger phrases (short-circuit in PARSING — no NLP needed):**
- "undo", "undo that", "go back", "reverse that", "cancel that"

```
User: "open chrome"
System: [Opens Chrome] → context.last_intent = {intent: open_app, entity: chrome}

User: "undo"
System: [Checks context.last_intent]
        [UNDO handler: open_app → reversal is close_app(chrome)]
        "Closed Chrome"
```

**Reversibility Table:**

| Intent | Reversal | Reversible |
|--------|---------|------------|
| open_app | close_app(same entity) | ✅ |
| open_file | no-op (file already open; JARVIS didn't write it) | ✅ (best effort) |
| volume_control | volume_control(opposite direction) | ✅ |
| screenshot | delete screenshot file | ✅ |
| create_file | delete_file(same path) | ✅ (with confirmation) |
| delete_file | **NOT reversible** | ❌ |
| lock_screen | **NOT reversible** (requires password) | ❌ |
| shutdown | **NOT reversible** | ❌ |
| search_files | no-op | n/a |

**Implementation:**
```python
REVERSIBLE_ACTIONS = {
    'open_app':   lambda intent, ctx: execute_close_app(intent['entity']),
    'open_file':  lambda intent, ctx: None,  # Best-effort: file stays open
    'volume_control': lambda intent, ctx: execute_volume_control(
        'down' if intent['action'] == 'up' else 'up'
    ),
    'screenshot': lambda intent, ctx: delete_file(ctx.get_variable('last_screenshot_path')),
    'create_file': lambda intent, ctx: execute_delete_file(intent['entity'], confirm=True),
}

def execute_undo(intent, context):
    last = context.last_intent
    if not last:
        return ExecutionResult(success=False, message="Nothing to undo.")
    
    reversal = REVERSIBLE_ACTIONS.get(last['intent'])
    if reversal:
        reversal(last, context)
        context.last_intent = None  # Prevent double-undo
        return ExecutionResult(success=True, message=f"Undid: {last['intent']}")
    else:
        return ExecutionResult(
            success=False,
            message=f"I can't undo '{last['intent']}'. That action is not reversible."
        )
```

### 6.3 Repeat Flow (`IntentType.REPEAT`)

**Trigger phrases:**
- "do that again", "repeat", "again", "once more"

```
User: "open chrome"
System: [Opens Chrome]

User: "do that again"
System: [Reads context.last_intent → re-executes open_app(chrome)]
        "Launching Chrome again"
```

**Implementation:**
```python
def execute_repeat(intent, context):
    last = context.last_intent
    if not last:
        return ExecutionResult(success=False, message="Nothing to repeat.")
    if last['intent'] in ('undo', 'repeat'):
        return ExecutionResult(success=False, message="Can't repeat an undo/repeat.")
    
    # Re-execute the stored intent
    return execute_intent(last, context)
```

### 6.4 Multi-Step Command Flow

```
User: "open my todo list and yesterday's notes"
    ↓
[Parse] → NLP detects compound command (AND-split)
    ↓
intent_list = [
    Intent(type=OPEN_FILE, parameters={'filename': 'todo.txt'}),
    Intent(type=OPEN_FILE, parameters={'filename': 'notes_yesterday.md'})
]
    ↓
[Executor: iterate intent_list sequentially]
    ↓
execute(intent_list[0])  → speak("Opened todo.txt")
execute(intent_list[1])  → speak("Opened yesterday's notes")
```

**Implementation (executor multi-intent loop):**
```python
def execute_intent_list(intent_list: List[Intent], context: ConversationContext):
    results = []
    for intent in intent_list:
        result = execute_intent(intent, context)
        results.append(result)
        if result.success:
            speak(result.message)
        else:
            speak(f"Couldn't complete '{intent.type.value}': {result.message}")
            # Continue with remaining intents (don't abort on partial failure)
    return results
```

### 6.5 Macro Flow (`IntentType.MACRO`)

```
User: "morning routine"
    ↓
[Parse] → intent = {type: MACRO, parameters: {macro_name: 'morning routine'}}
    ↓
[MacroSkill] reads config/macros.json
    → Finds steps: [open_app(chrome), open_file(todo.txt), system_info]
    ↓
[Executor] calls execute_intent_list(steps, context)
    → speak("Launching Chrome...")
    → speak("Opening todo.txt...")
    → speak("RAM usage: 42%")
    ↓
speak("Morning routine complete. 3 of 3 steps done.")
```

**Note:** If `config/macros.json` does not exist, MacroSkill responds: "No macros configured. Add them to config/macros.json." and does not crash.

---

## 7. PERFORMANCE OPTIMIZATION FLOWS

### 7.1 Lazy Loading Strategy

```
┌─────────────────────────────────────┐
│ INITIALIZATION OPTIMIZATION          │
└─────────────────────────────────────┘

[App Start]
    ↓
Load: Core modules only (0.5s)
    - Audio driver
    - Config parser
    - Basic I/O
    ↓
Display: "JARVIS starting..."
    ↓
Background Load: Heavy models (3-5s)
    - Whisper (async)
    - spaCy (async)
    ↓
    [User can start typing commands immediately]
    ↓
Ready: "JARVIS ready" (when models loaded)
```

**Implementation:**
```python
def async_initialization():
    """
    Non-blocking initialization
    """
    # 1. Quick start (UI available)
    init_basic_components()  # 0.5s
    display_ui()
    
    # 2. Background loading
    model_thread = Thread(target=load_heavy_models)
    model_thread.start()
    
    # 3. Allow text input immediately
    enable_text_mode()
    
    # 4. Enable voice when ready
    model_thread.join()
    enable_voice_mode()
```

### 7.2 Caching Strategy

```python
# Cache frequently used file searches
file_search_cache = LRUCache(maxsize=100)

def search_files_cached(query, location):
    cache_key = f"{query}:{location}"
    
    if cache_key in file_search_cache:
        return file_search_cache[cache_key]
    
    results = search_files(query, location)
    file_search_cache[cache_key] = results
    return results

# Cache intent parsing results for identical inputs
intent_cache = LRUCache(maxsize=50)

def parse_intent_cached(text):
    if text in intent_cache:
        return intent_cache[text]
    
    intent = parse_intent(text)
    intent_cache[text] = intent
    return intent
```

---

## 8. LOGGING & DEBUGGING FLOW

### 8.1 Structured Logging

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self):
        self.logger = logging.getLogger('jarvis')
        handler = logging.FileHandler('logs/jarvis.log')
        self.logger.addHandler(handler)
    
    def log_state_transition(self, from_state, to_state, data=None):
        """Log state changes"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'state_transition',
            'from': from_state,
            'to': to_state,
            'data': data
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_command(self, text, intent, result):
        """Log command execution"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'command',
            'input': text,
            'intent': intent,
            'result': result
        }
        self.logger.info(json.dumps(log_entry))
```

**Sample Log Output:**
```json
{"timestamp": "2026-02-06T10:30:15", "type": "state_transition", "from": "IDLE", "to": "LISTENING"}
{"timestamp": "2026-02-06T10:30:18", "type": "state_transition", "from": "LISTENING", "to": "TRANSCRIBING"}
{"timestamp": "2026-02-06T10:30:19", "type": "command", "input": "open chrome", "intent": {"intent": "open_app", "entity": "chrome"}, "result": "success"}
{"timestamp": "2026-02-06T10:30:20", "type": "state_transition", "from": "EXECUTING", "to": "RESPONDING"}
```

---

## 9. STARTUP SEQUENCE (DETAILED)

```
┌────────────────────────────────────────────────────────────┐
│               COMPLETE STARTUP SEQUENCE                     │
└────────────────────────────────────────────────────────────┘

[T=0.0s] main.py executed
    ↓
[T=0.1s] Import standard libraries (os, sys, subprocess)
    ↓
[T=0.2s] Import audio libraries (sounddevice, pyaudio)
    ↓
[T=0.3s] Display ASCII banner
    ╔═══════════════════════════════════╗
    ║  JARVIS-Lite Voice Assistant      ║
    ║  Initializing...                  ║
    ╚═══════════════════════════════════╝
    ↓
[T=0.5s] Load configuration (config/settings.json)
    ├─ Read command whitelist
    ├─ Read audio settings
    ├─ Read voice preferences
    └─ Read security settings
    ↓
[T=0.7s] Initialize audio devices
    ├─ Enumerate microphones
    ├─ Select default input
    ├─ Test mic availability
    └─ Display: "✓ Microphone: [Device Name]"
    ↓
[T=1.0s] Load Whisper model (async)
    ├─ Check if model cached
    ├─ Load from disk: ~/.cache/whisper/
    ├─ Progress: ████████░░ 80%
    └─ Display: "✓ Speech Recognition Ready"
    ↓
[T=2.5s] Load spaCy model (async)
    ├─ Import spacy
    ├─ Load en_core_web_sm
    └─ Display: "✓ Language Processing Ready"
    ↓
[T=3.0s] Initialize TTS engine
    ├─ Import pyttsx3
    ├─ Initialize engine
    ├─ Set voice properties
    └─ Display: "✓ Voice Output Ready"
    ↓
[T=3.2s] Create conversation context object
    ├─ Initialize empty history
    ├─ Load previous session (if exists)
    └─ Display: "✓ Context Manager Ready"
    ↓
[T=3.5s] Register signal handlers
    ├─ SIGINT (Ctrl+C) → graceful shutdown
    ├─ SIGTERM → save and exit
    └─ Display: "✓ System Ready"
    ↓
[T=4.0s] Display ready message
    ╔═══════════════════════════════════╗
    ║  JARVIS Ready                     ║
    ║  Press SPACE to speak             ║
    ║  Type 'help' for commands         ║
    ╚═══════════════════════════════════╝
    ↓
[T=4.0s+] Enter IDLE state (main loop)
```

---

## 10. MAIN LOOP PSEUDOCODE

```python
def main_loop():
    """
    Core event loop
    """
    state = State.IDLE
    context = ConversationContext()
    
    while True:
        if state == State.IDLE:
            # Wait for user input
            event = wait_for_event()  # Blocking
            
            if event.type == 'KEYPRESS' and event.key == 'SPACE':
                state = State.LISTENING
            elif event.type == 'TEXT_INPUT':
                text = event.data
                state = State.PARSING
            elif event.type == 'EXIT_COMMAND':
                state = State.SHUTTING_DOWN
        
        elif state == State.LISTENING:
            audio_data = capture_audio()
            state = State.TRANSCRIBING
        
        elif state == State.TRANSCRIBING:
            text = transcribe(audio_data)
            if text:
                print(f"You: {text}")
                context.add_turn('user', text)
                state = State.PARSING
            else:
                speak("Sorry, I didn't catch that.")
                state = State.IDLE
        
        elif state == State.PARSING:
            intent = parse_intent(text, context)
            
            if intent['confidence'] > 0.8:
                state = State.EXECUTING
            elif requires_clarification(intent):
                state = State.CLARIFYING
            else:
                speak("I didn't understand. Try 'help'.")
                state = State.IDLE
        
        elif state == State.CLARIFYING:
            clarification_msg = generate_clarification(intent)
            speak(clarification_msg)
            state = State.LISTENING  # Wait for clarification
        
        elif state == State.EXECUTING:
            success, result = execute_intent(intent)
            
            if success:
                context.add_turn('assistant', result)
                state = State.RESPONDING
            else:
                state = State.ERROR
        
        elif state == State.RESPONDING:
            speak(result)
            state = State.IDLE
        
        elif state == State.ERROR:
            handle_error(error_message)
            state = State.IDLE
        
        elif state == State.SHUTTING_DOWN:
            cleanup_and_exit()
            break
```

---

## 11. VISUAL UI FLOW (CLI)

### 11.1 Screen States

**IDLE State:**
```
╔═══════════════════════════════════════════════════════════╗
║  JARVIS-Lite v1.0                                         ║
║  Status: Ready                                            ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  Commands (10):                                           ║
║  • open_app, open_file, search_files, close_app          ║
║  • volume_up, volume_down, screenshot, lock_screen        ║
║  • help, exit                                             ║
║                                                           ║
║  Recent:                                                  ║
║  10:30:15 - Opened Chrome                                 ║
║  10:28:42 - Found 5 Python files                          ║
║                                                           ║
╠═══════════════════════════════════════════════════════════╣
║  Press SPACE to speak | Type command | 'help' for info   ║
╚═══════════════════════════════════════════════════════════╝
> _
```

**LISTENING State:**
```
╔═══════════════════════════════════════════════════════════╗
║  🎤 LISTENING...                                          ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  ████████████████▌▌▌▌▌▌▌██████████████                   ║
║  [Recording... Release SPACE when done]                   ║
║                                                           ║
║  Duration: 2.3s / 10s max                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

**PROCESSING State:**
```
╔═══════════════════════════════════════════════════════════╗
║  💭 PROCESSING...                                         ║
╠═══════════════════════════════════════════════════════════╣
║                                                           ║
║  You: "open chrome"                                       ║
║                                                           ║
║  ⚙️  Analyzing command...                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
```

