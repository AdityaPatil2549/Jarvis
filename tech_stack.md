# TECHNICAL STACK SPECIFICATION

## JARVIS-Lite: Complete Technology Stack

**Last Updated:** February 6, 2026
**Target:** Production-ready, offline-first voice assistant
**Philosophy:** Free, stable, well-documented libraries only

---

## 1. CORE TECHNOLOGY DECISIONS

### 1.1 Programming Language

**Choice:** Python 3.11+

**Justification:**

- ✅ Best ecosystem for AI/ML (Whisper, spaCy, transformers)
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Rapid development (dynamic typing, REPL)
- ✅ Extensive audio libraries (sounddevice, PyAudio)
- ✅ Strong subprocess/OS integration

**Alternatives Rejected:**

- ❌ **JavaScript/Node.js** - Weaker ML ecosystem, no Whisper bindings
- ❌ **Rust** - Steep learning curve, slower development
- ❌ **C++** - Overkill for glue code, harder debugging

**Version Requirements:**

```
Python: >=3.11, <3.13
Reason: 3.11 has performance improvements, 3.13 not yet stable
```

**Installation:**

```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Windows
# Download from python.org (3.11.x installer)
```

---

## 2. AUDIO LAYER

### 2.1 Audio Capture & Playback

#### Primary: **sounddevice**

**Version:** `sounddevice==0.4.6`

**Why This:**

- ✅ Actively maintained (last update: 2023)
- ✅ Cross-platform (PortAudio backend)
- ✅ NumPy integration (efficient processing)
- ✅ Lower latency than PyAudio
- ✅ Better error messages

**Installation:**

```bash
pip install sounddevice==0.4.6
```

**System Dependencies:**

```bash
# macOS - No additional dependencies (built-in)

# Ubuntu/Debian
sudo apt install libportaudio2 portaudio19-dev

# Windows - No additional dependencies
```

**Usage Example:**

```python
import sounddevice as sd
import numpy as np

# Record audio
duration = 5  # seconds
fs = 16000  # sample rate
recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
sd.wait()  # Wait until recording is finished

# Play audio
sd.play(recording, fs)
sd.wait()
```

**Known Issues:**

- Linux: Requires PulseAudio or ALSA configured
- Some USB mics need explicit device selection
- High CPU on Raspberry Pi (use PyAudio instead)

**Fallback:** `PyAudio==0.2.14` (if sounddevice fails)

---

#### Alternative: **PyAudio** (Fallback)

**Version:** `PyAudio==0.2.14`

**When to Use:**

- sounddevice installation fails
- Raspberry Pi / low-power devices
- Older systems (pre-2015)

**Installation:**

```bash
# macOS
brew install portaudio
pip install pyaudio==0.2.14

# Ubuntu/Debian
sudo apt install python3-pyaudio

# Windows (prebuilt wheel)
pip install pipwin
pipwin install pyaudio
```

**Known Issues:**

- ⚠️ Installation is painful on Linux/Windows
- ⚠️ Higher latency than sounddevice
- ⚠️ Worse error messages

---

### 2.2 Audio Processing

#### **NumPy**

**Version:** `numpy==1.26.4`

**Why This:**

- ✅ Industry standard for numerical computing
- ✅ Required by Whisper and sounddevice
- ✅ Fast array operations (C backend)

**Installation:**

```bash
pip install numpy==1.26.4
```

**Usage:**

```python
import numpy as np

# Convert audio to correct format for Whisper
audio_float32 = recording.flatten().astype(np.float32)
```

---

#### **SciPy** (Optional, for advanced filtering)

**Version:** `scipy==1.12.0`

**When to Use:**

- Noise reduction
- Audio normalization
- Frequency filtering

**Installation:**

```bash
pip install scipy==1.12.0
```

**Usage Example:**

```python
from scipy.signal import butter, filtfilt

def remove_noise(audio, fs=16000):
    """Apply low-pass filter to remove high-frequency noise"""
    nyquist = 0.5 * fs
    normal_cutoff = 3000 / nyquist  # 3kHz cutoff
    b, a = butter(5, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, audio)
```

---

## 3. SPEECH-TO-TEXT LAYER

### 3.1 Primary STT: **OpenAI Whisper**

**Version:** `openai-whisper==20231117`

**Why This:**

- ✅ State-of-the-art accuracy (95%+ WER)
- ✅ Works offline
- ✅ Multilingual (99 languages)
- ✅ Handles accents well
- ✅ MIT License (fully open)

**Installation:**

```bash
pip install openai-whisper==20231117
```

**System Dependencies:**

```bash
# FFmpeg required for audio loading
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from ffmpeg.org, add to PATH
```

**Model Selection:**

| Model  | Size   | RAM   | Speed (CPU) | Speed (GPU) | Accuracy |
| ------ | ------ | ----- | ----------- | ----------- | -------- |
| tiny   | 39 MB  | 1 GB  | ~10s        | ~0.5s       | 85%      |
| base   | 74 MB  | 1 GB  | ~15s        | ~0.7s       | 90%      |
| small  | 244 MB | 2 GB  | ~30s        | ~1.5s       | 94%      |
| medium | 769 MB | 5 GB  | ~60s        | ~3s         | 96%      |
| large  | 1.5 GB | 10 GB | ~120s       | ~5s         | 98%      |

**Recommended:** `base` for MVP (best speed/accuracy tradeoff)

**Usage:**

```python
import whisper

# Load model once at startup
model = whisper.load_model("base")

# Transcribe audio
def transcribe_audio(audio_array, sample_rate=16000):
    """
    Args:
        audio_array: NumPy float32 array
        sample_rate: int (16000 recommended)
    Returns:
        str: Transcribed text
    """
    result = model.transcribe(
        audio_array,
        language='en',  # Optional: force language
        fp16=False,     # Disable for CPU
        verbose=False
    )
    return result['text'].strip()
```

**GPU Acceleration:**

```bash
# Install PyTorch with CUDA (if NVIDIA GPU available)
pip install torch==2.1.2+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# Whisper will automatically use GPU
model = whisper.load_model("base").cuda()
```

**Known Issues:**

- First run downloads model (~74MB for base)
- Requires 1GB+ RAM even for tiny model
- CPU inference is slow (1.5-2s for 5s audio)

---

### 3.2 Fallback STT: **Vosk**

**Version:** `vosk==0.3.45`

**Why This:**

- ✅ Faster than Whisper on CPU
- ✅ Smaller models (40MB vs 74MB)
- ✅ Lower RAM usage (200MB vs 1GB)
- ✅ Good for real-time streaming

**Installation:**

```bash
pip install vosk==0.3.45
```

**Model Download:**

```bash
# Download small English model (40MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d models/
```

**Usage:**

```python
from vosk import Model, KaldiRecognizer
import json

# Load model once
vosk_model = Model("models/vosk-model-small-en-us-0.15")

def vosk_transcribe(audio_bytes, sample_rate=16000):
    """
    Args:
        audio_bytes: bytes (PCM 16-bit)
        sample_rate: int
    Returns:
        str: Transcribed text
    """
    rec = KaldiRecognizer(vosk_model, sample_rate)
    rec.AcceptWaveform(audio_bytes)
    result = json.loads(rec.FinalResult())
    return result.get('text', '')
```

**When to Use:**

- Whisper too slow on user's hardware
- Real-time transcription needed
- Memory constrained (<2GB RAM)

**Trade-offs:**

- Lower accuracy (85% vs 90%)
- Less robust to accents
- English-only in small model

---

## 4. NATURAL LANGUAGE PROCESSING

### 4.1 Intent Parsing: **spaCy**

**Version:** `spacy==3.7.4`

**Why This:**

- ✅ Industrial-strength NLP
- ✅ Fast (Cython backend)
- ✅ Pre-trained models available
- ✅ Named Entity Recognition (NER)
- ✅ Dependency parsing

**Installation:**

```bash
pip install spacy==3.7.4

# Download English model
python -m spacy download en_core_web_sm
```

**Model Sizes:**

| Model          | Size   | Speed  | Features          |
| -------------- | ------ | ------ | ----------------- |
| en_core_web_sm | 12 MB  | Fast   | Basic NER, POS    |
| en_core_web_md | 40 MB  | Medium | + Word vectors    |
| en_core_web_lg | 560 MB | Slow   | + Full embeddings |

**Recommended:** `en_core_web_sm` (sufficient for intent parsing)

**Usage:**

```python
import spacy

# Load model once
nlp = spacy.load("en_core_web_sm")

def extract_entities(text):
    """
    Extract named entities from text
  
    Args:
        text: str (e.g., "open chrome on my desktop")
    Returns:
        dict: {verbs: [...], nouns: [...], entities: [...]}
    """
    doc = nlp(text)
  
    return {
        'verbs': [token.text for token in doc if token.pos_ == 'VERB'],
        'nouns': [token.text for token in doc if token.pos_ == 'NOUN'],
        'entities': [(ent.text, ent.label_) for ent in doc.ents],
        'dependencies': [(token.text, token.dep_) for token in doc]
    }

# Example
result = extract_entities("open chrome on my desktop")
# {
#   'verbs': ['open'],
#   'nouns': ['chrome', 'desktop'],
#   'entities': [],
#   'dependencies': [('open', 'ROOT'), ('chrome', 'dobj'), ...]
# }
```

**Alternative: Regex + Manual Parsing (Lighter)**

If spaCy is too heavy:

```python
import re

def lightweight_parse(text):
    """Simple pattern matching without ML"""
    text = text.lower()
  
    # Extract action verbs
    action_patterns = {
        'open': r'\b(open|launch|start|run)\b',
        'close': r'\b(close|quit|exit|kill)\b',
        'find': r'\b(find|search|locate)\b',
    }
  
    action = None
    for act, pattern in action_patterns.items():
        if re.search(pattern, text):
            action = act
            break
  
    # Extract target (noun after action)
    target = None
    if action:
        match = re.search(rf'{action_patterns[action]}\s+(\w+)', text)
        if match:
            target = match.group(2)
  
    return {'action': action, 'target': target}
```

**Recommendation:** Start with regex, upgrade to spaCy if needed.

---

### 4.2 Fuzzy Matching: **fuzzywuzzy** / **rapidfuzz**

**Version:** `rapidfuzz==3.6.1`

**Why This:**

- ✅ Fast fuzzy string matching
- ✅ Handles typos and variations
- ✅ Levenshtein distance algorithm
- ✅ 10x faster than fuzzywuzzy

**Installation:**

```bash
pip install rapidfuzz==3.6.1
```

**Usage:**

```python
from rapidfuzz import fuzz, process

def fuzzy_match_command(user_input, valid_commands):
    """
    Match user input to closest valid command
  
    Args:
        user_input: str (e.g., "opn crome")
        valid_commands: list (e.g., ["open chrome", "open firefox"])
    Returns:
        str: Best match or None
    """
    match, score, _ = process.extractOne(user_input, valid_commands)
  
    if score > 80:  # 80% similarity threshold
        return match
    return None

# Example
commands = ["open chrome", "open firefox", "close chrome"]
fuzzy_match_command("opn crome", commands)  # Returns "open chrome"
```

**Use Cases:**

- File name matching ("resum" → "resume.pdf")
- Command correction ("opn crome" → "open chrome")
- Clarification resolution ("the second one" → match from context)

---

## 5. TEXT-TO-SPEECH LAYER

### 5.1 Primary TTS: **pyttsx3**

**Version:** `pyttsx3==2.90`

**Why This:**

- ✅ Zero-latency (uses system TTS)
- ✅ No downloads required
- ✅ Cross-platform
- ✅ Offline
- ✅ Simple API

**Installation:**

```bash
pip install pyttsx3==2.90
```

**System Dependencies:**

```bash
# macOS - Uses NSSpeechSynthesizer (built-in)

# Windows - Uses SAPI5 (built-in)

# Linux - Requires espeak
sudo apt install espeak
```

**Usage:**

```python
import pyttsx3

# Initialize once
engine = pyttsx3.init()

# Configure voice properties
def setup_voice(rate=175, volume=0.9):
    """
    Args:
        rate: Words per minute (default 200, slower = 150-175)
        volume: 0.0 to 1.0
    """
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)
  
    # Optional: Select voice
    voices = engine.getProperty('voices')
    # engine.setProperty('voice', voices[0].id)  # Male voice
    # engine.setProperty('voice', voices[1].id)  # Female voice

def speak(text):
    """Blocking TTS call"""
    engine.say(text)
    engine.runAndWait()

# Non-blocking version
def speak_async(text, callback=None):
    """Non-blocking TTS"""
    engine.say(text)
    if callback:
        engine.connect('finished-utterance', callback)
    engine.startLoop(False)
    engine.iterate()
    engine.endLoop()
```

**Pros:**

- Instant (no model loading)
- No disk space
- Reliable

**Cons:**

- Robotic voice quality (6/10)
- Limited voice customization
- Platform-dependent quality

---

### 5.2 Upgrade TTS: **Piper** (Phase 2)

**Version:** `piper-tts==1.2.0`

**Why Upgrade:**

- ✅ Near-human quality (8/10)
- ✅ Still offline
- ✅ Customizable voices
- ✅ Fast (real-time synthesis)

**Installation:**

```bash
pip install piper-tts==1.2.0
```

**Model Download:**

```bash
# Download voice model (50MB)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

**Usage:**

```python
from piper import PiperVoice
import wave

# Load voice once
voice = PiperVoice.load("en_US-lessac-medium.onnx")

def piper_speak(text, output_file="output.wav"):
    """
    Generate speech to WAV file
  
    Args:
        text: str
        output_file: str (path to save audio)
    """
    with wave.open(output_file, 'wb') as wav_file:
        wav_file.setparams((1, 2, 22050, 0, 'NONE', 'NONE'))
      
        # Synthesize
        audio = voice.synthesize(text)
        wav_file.writeframes(audio)
  
    # Play with sounddevice
    import sounddevice as sd
    import soundfile as sf
    data, fs = sf.read(output_file)
    sd.play(data, fs)
    sd.wait()
```

**Recommendation:** Start with pyttsx3, upgrade to Piper after MVP works.

---

## 6. SYSTEM AUTOMATION

### 6.1 GUI Automation: **PyAutoGUI**

**Version:** `pyautogui==0.9.54`

**Why This:**

- ✅ Cross-platform mouse/keyboard control
- ✅ Screenshot capture
- ✅ Window management
- ✅ Simple API

**Installation:**

```bash
pip install pyautogui==0.9.54
```

**System Dependencies:**

```bash
# macOS - Grant accessibility permissions
# System Preferences > Security > Privacy > Accessibility

# Linux
sudo apt install python3-tk python3-dev scrot
```

**Usage:**

```python
import pyautogui

# Failsafe: Move mouse to corner to abort
pyautogui.FAILSAFE = True

def click_at(x, y):
    """Click at screen coordinates"""
    pyautogui.click(x, y)

def type_text(text):
    """Type text (simulates keyboard)"""
    pyautogui.write(text, interval=0.05)

def press_keys(*keys):
    """Press key combination"""
    pyautogui.hotkey(*keys)
    # Example: press_keys('ctrl', 'c')  # Copy

def take_screenshot(filename='screenshot.png'):
    """Capture screen"""
    screenshot = pyautogui.screenshot()
    screenshot.save(filename)
    return filename
```

**Use Cases:**

- Window management
- Keyboard shortcuts
- Screenshot commands
- Emergency mouse control

**⚠️ Security Warning:**

- Never allow arbitrary PyAutoGUI commands from voice input
- Whitelist specific actions only

---

### 6.2 Process Management: **psutil**

**Version:** `psutil==5.9.8`

**Why This:**

- ✅ Cross-platform system info
- ✅ Process listing
- ✅ CPU/memory monitoring
- ✅ Network stats

**Installation:**

```bash
pip install psutil==5.9.8
```

**Usage:**

```python
import psutil

def list_processes():
    """Get all running processes"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        processes.append(proc.info)
    return processes

def find_process(name):
    """Find process by name"""
    for proc in psutil.process_iter(['pid', 'name']):
        if name.lower() in proc.info['name'].lower():
            return proc.info['pid']
    return None

def kill_process(pid):
    """Terminate process by PID"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=3)
        return True
    except (psutil.NoSuchProcess, psutil.TimeoutExpired):
        return False

def get_system_stats():
    """Get CPU, RAM, disk usage"""
    return {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_percent': psutil.disk_usage('/').percent
    }
```

**Use Cases:**

- "Close Chrome" → find_process('chrome') → kill_process()
- "How much RAM am I using?" → get_system_stats()
- List running apps

---

### 6.3 File Operations: **pathlib** (stdlib)

**No Installation Required** (Python 3.4+)

**Usage:**

```python
from pathlib import Path
import shutil

def search_files(query, directory=None, recursive=True):
    """
    Search for files by name
  
    Args:
        query: str (e.g., "*.py" or "resume")
        directory: Path or str (default: home)
        recursive: bool
    Returns:
        list of Path objects
    """
    search_dir = Path(directory or Path.home())
  
    if '*' in query:
        # Glob pattern
        pattern = query
    else:
        # Fuzzy search
        pattern = f"*{query}*"
  
    if recursive:
        return list(search_dir.rglob(pattern))
    else:
        return list(search_dir.glob(pattern))

def open_file(filepath):
    """Open file in default application"""
    import subprocess
    import sys
  
    path = Path(filepath)
  
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
  
    if sys.platform == 'win32':
        os.startfile(path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', path])
    else:
        subprocess.run(['xdg-open', path])

def create_file(filepath, content=''):
    """Create new file with content"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
```

---

## 7. CONFIGURATION & LOGGING

### 7.1 Configuration: **JSON** (stdlib)

**No Installation Required**

**Structure:**

```python
import json
from pathlib import Path

CONFIG_FILE = Path('config/settings.json')

def load_config():
    """Load configuration from JSON"""
    if not CONFIG_FILE.exists():
        return create_default_config()
  
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config):
    """Save configuration to JSON"""
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def create_default_config():
    """Create default configuration"""
    default = {
        "audio": {
            "sample_rate": 16000,
            "channels": 1,
            "device": "default"
        },
        "stt": {
            "engine": "whisper",
            "model": "base",
            "language": "en"
        },
        "tts": {
            "engine": "pyttsx3",
            "rate": 175,
            "volume": 0.9
        },
        "security": {
            "allowed_directories": [
                "~/Documents",
                "~/Desktop",
                "~/Downloads"
            ],
            "dangerous_commands": ["rm", "del", "format"]
        },
        "features": {
            "wake_word": false,
            "auto_save_history": true,
            "verbose_logging": false
        }
    }
    save_config(default)
    return default
```

---

### 7.2 Logging: **logging** (stdlib)

**No Installation Required**

**Setup:**

```python
import logging
from datetime import datetime
from pathlib import Path

def setup_logging(level=logging.INFO):
    """Configure structured logging"""
  
    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
  
    # Log filename with date
    log_file = log_dir / f"jarvis_{datetime.now().strftime('%Y%m%d')}.log"
  
    # Configure format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
  
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
  
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
  
    # Root logger
    logger = logging.getLogger('jarvis')
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
  
    return logger

# Usage
logger = setup_logging()
logger.info("Application started")
logger.error("Failed to load model", exc_info=True)
```

---

## 8. DEVELOPMENT TOOLS

### 8.1 Testing: **pytest**

**Version:** `pytest==8.0.0`

**Installation:**

```bash
pip install pytest==8.0.0 pytest-cov==4.1.0
```

**Usage:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jarvis tests/

# Run specific test file
pytest tests/test_stt.py

# Run with verbose output
pytest -v
```

---

### 8.2 Code Quality: **black** + **pylint**

**Versions:**

```bash
pip install black==24.1.1 pylint==3.0.3
```

**Usage:**

```bash
# Auto-format code
black jarvis/

# Lint code
pylint jarvis/
```

---

### 8.3 Type Checking: **mypy**

**Version:** `mypy==1.8.0`

**Installation:**

```bash
pip install mypy==1.8.0
```

**Usage:**

```bash
mypy jarvis/ --strict
```

---

## 9. COMPLETE REQUIREMENTS.TXT

```txt
# requirements.txt - JARVIS-Lite Production Dependencies

# Core
numpy==1.26.4
scipy==1.12.0

# Audio
sounddevice==0.4.6
PyAudio==0.2.14  # Fallback only

# Speech-to-Text
openai-whisper==20231117
vosk==0.3.45  # Fallback

# NLP
spacy==3.7.4
rapidfuzz==3.6.1

# Text-to-Speech
pyttsx3==2.90
piper-tts==1.2.0  # Optional upgrade

# System Automation
pyautogui==0.9.54
psutil==5.9.8

# Development
pytest==8.0.0
pytest-cov==4.1.0
black==24.1.1
pylint==3.0.3
mypy==1.8.0

# Optional
soundfile==0.12.1  # For Piper audio loading
```

---

## 10. INSTALLATION SCRIPT

### Complete Setup (One Command)

```bash
#!/bin/bash
# setup.sh - Complete JARVIS-Lite Installation

set -e  # Exit on error

echo "🚀 JARVIS-Lite Installation Script"
echo "===================================="

# 1. Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [[ $(echo "$python_version < $required_version" | bc) -eq 1 ]]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version"

# 2. Create virtual environment
echo "📌 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"

# 3. Upgrade pip
echo "📌 Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✅ pip upgraded"

# 4. Install system dependencies
echo "📌 Installing system dependencies..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew install portaudio ffmpeg || echo "⚠️  Install Homebrew first"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    sudo apt update
    sudo apt install -y portaudio19-dev ffmpeg espeak python3-tk
fi
echo "✅ System dependencies installed"

# 5. Install Python packages
echo "📌 Installing Python packages..."
pip install -r requirements.txt
echo "✅ Python packages installed"

# 6. Download models
echo "📌 Downloading AI models..."

# Whisper base model
python -c "import whisper; whisper.load_model('base')"
echo "✅ Whisper model downloaded"

# spaCy model
python -m spacy download en_core_web_sm
echo "✅ spaCy model downloaded"

# Vosk model (optional)
mkdir -p models
cd models
if [ ! -d "vosk-model-small-en-us-0.15" ]; then
    wget -q https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
    unzip -q vosk-model-small-en-us-0.15.zip
    rm vosk-model-small-en-us-0.15.zip
fi
cd ..
echo "✅ Vosk model downloaded"

# 7. Create config
echo "📌 Creating default configuration..."
mkdir -p config logs
python -c "
import json
config = {
    'audio': {'sample_rate': 16000, 'channels': 1},
    'stt': {'engine': 'whisper', 'model': 'base'},
    'tts': {'engine': 'pyttsx3', 'rate': 175},
    'security': {'allowed_directories': ['~/Documents', '~/Desktop']}
}
with open('config/settings.json', 'w') as f:
    json.dump(config, f, indent=2)
"
echo "✅ Configuration created"

# 8. Run tests
echo "📌 Running tests..."
pytest tests/ -v || echo "⚠️  Some tests failed (this is okay for initial setup)"

echo ""
echo "✅ Installation complete!"
echo ""
echo "To run JARVIS-Lite:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
```

**Usage:**

```bash
chmod +x setup.sh
./setup.sh
```

---

## 11. PLATFORM-SPECIFIC NOTES

### 11.1 Windows

**Issues:**

- PyAudio installation is painful
- Path separators (`\` vs `/`)
- No native `espeak` (pyttsx3 uses SAPI)

**Solutions:**

```bash
# Use pipwin for PyAudio
pip install pipwin
pipwin install pyaudio

# Use pathlib (handles separators)
from pathlib import Path  # Always works

# pyttsx3 works out-of-box on Windows
```

---

### 11.2 macOS

**Issues:**

- Microphone permissions required
- Some system commands need sudo

**Solutions:**

```bash
# Grant mic permission
# System Preferences > Security & Privacy > Microphone

# Grant automation permission
# System Preferences > Security & Privacy > Accessibility
```

---

### 11.3 Linux

**Issues:**

- Audio driver hell (ALSA vs PulseAudio)
- pyttsx3 requires espeak
- Different distros, different packages

**Solutions:**

```bash
# Ubuntu/Debian
sudo apt install portaudio19-dev ffmpeg espeak python3-tk

# Fedora
sudo dnf install portaudio-devel ffmpeg espeak python3-tkinter

# Arch
sudo pacman -S portaudio ffmpeg espeak tk
```

---

## 12. RESOURCE REQUIREMENTS

### 12.1 Disk Space

```
Base Installation:
├─ Python 3.11: 100 MB
├─ pip packages: 200 MB
├─ Whisper base model: 74 MB
├─ spaCy model: 12 MB
├─ Vosk model (optional): 40 MB
└─ Total: ~430 MB

With Upgrades:
├─ Piper voice: 50 MB
├─ Whisper small: 244 MB
└─ Total: ~720 MB
```

### 12.2 RAM Usage

```
Idle (models loaded):
├─ Python runtime: 50 MB
├─ Whisper base: 1 GB
├─ spaCy: 50 MB
├─ pyttsx3: 10 MB
└─ Total: ~1.1 GB

Processing (peak):
├─ Audio buffer: 50 MB
├─ Whisper inference: 1.5 GB
├─ OS buffers: 200 MB
└─ Total: ~2.8 GB
```

**Minimum System:** 4GB RAM
**Recommended:** 8GB RAM

### 12.3 CPU Requirements

```
Minimum: Dual-core 2.0 GHz
Recommended: Quad-core 2.5 GHz
Optimal: 8+ cores or Apple Silicon
```

**Benchmarks (5 seconds audio):**

| Hardware             | Whisper Base Time |
| -------------------- | ----------------- |
| Intel i5-8250U (4c)  | ~3.5s             |
| Intel i7-10700K (8c) | ~1.2s             |
| Apple M1             | ~0.8s             |
| NVIDIA RTX 3060      | ~0.3s             |

---

## 13. OPTIONAL ACCELERATIONS

### 13.1 GPU Support (NVIDIA)

**Installation:**

```bash
# Install CUDA toolkit (11.8 recommended)
# Download from nvidia.com/cuda-downloads

# Install PyTorch with CUDA
pip install torch==2.1.2+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# Verify GPU availability
python -c "import torch; print(torch.cuda.is_available())"
```

**Benefits:**

- 10x faster Whisper inference
- Can use larger models (small, medium)
- Better for real-time processing

---

### 13.2 Apple Silicon Optimization

**Installation:**

```bash
# Install Apple Silicon optimized PyTorch
pip install torch==2.1.2 torchvision==0.16.2
```

**Benefits:**

- 5x faster than Intel Macs
- Efficient memory usage
- Low power consumption

---

## 14. DEPENDENCY GRAPH

```
┌──────────────────────────────────────────────────────────┐
│                   DEPENDENCY TREE                         │
└──────────────────────────────────────────────────────────┘

jarvis-lite
├── Audio Layer
│   ├── sounddevice (requires: numpy, portaudio)
│   └── PyAudio (backup, requires: portaudio)
│
├── STT Layer
│   ├── openai-whisper (requires: torch, ffmpeg, numpy)
│   └── vosk (requires: none)
│
├── NLP Layer
│   ├── spacy (requires: numpy, model download)
│   └── rapidfuzz (requires: none)
│
├── TTS Layer
│   ├── pyttsx3 (requires: espeak on Linux)
│   └── piper-tts (requires: onnxruntime, numpy)
│
├── Automation Layer
│   ├── pyautogui (requires: tkinter, pillow)
│   └── psutil (requires: none)
│
└── Core
    ├── numpy (base dependency)
    ├── pathlib (stdlib)
    ├── json (stdlib)
    └── logging (stdlib)
```

---

## 15. FINAL TECH STACK SUMMARY

### ✅ Confirmed Stack (MVP)

```yaml
Language: Python 3.11+
Audio: sounddevice + NumPy
STT: Whisper (base model)
NLP: spaCy (en_core_web_sm) + regex
TTS: pyttsx3
Automation: pyautogui + psutil + pathlib
Config: JSON (stdlib)
Logging: logging (stdlib)
Testing: pytest

Total Dependencies: 12 packages
Total Disk: 430 MB
Total RAM: 1.1 GB idle, 2.8 GB peak
Installation Time: 5-10 minutes
```

### 🎯 Upgrade Path (Phase 2)

```yaml
STT: Add Vosk fallback
TTS: Upgrade to Piper
NLP: Add fuzzy matching (rapidfuzz)
Performance: GPU acceleration (optional)
```

