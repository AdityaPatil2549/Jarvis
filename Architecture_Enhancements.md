 

# JARVIS-Lite: Advanced Architecture Enhancements

This document outlines the solutions for five critical architectural challenges required to elevate JARVIS-Lite from a functional prototype to a world-class, robust, and secure desktop assistant.

---

## 1. UX & Interaction: TTS Interruption (Barge-in)

**Problem:** Standard Text-to-Speech execution is blocking. If the assistant speaks a long paragraph, the user is locked out from issuing new commands until it finishes.
**Solution:** Threaded, Interruptible TTS Loop

- **Architecture:** The TTS engine (`pyttsx3`) will run in a dedicated daemon thread using its non-blocking event loop method (`engine.startLoop(False)` and `engine.iterate()`).
- **Mechanism:** The global keyboard hook (`pywin32`) continuously monitors the push-to-talk (SPACE) key. If pressed during the `RESPONDING` state, it fires a threading `Event` (`tts_interrupt_flag`).
- **Execution:** The TTS loop checks this flag on every iteration. If detected, it immediately flushes the audio queue, gracefully terminates the current utterance, and forces the state machine back to `LISTENING`.

---

## 2. Security: Skill Permission Manifests (Whitelist)

**Problem:** Blacklist regex parsing (e.g., blocking `rm -rf`) is easily bypassed. A rogue or poorly coded third-party skill currently runs with the same global permissions as the main JARVIS process.
**Solution:** Android-Style Capability Manifests

- **Architecture:** Every skill (core and third-party) must include a `manifest.json` defining its required capabilities (e.g., `["network_access", "file_system_read", "process_control"]`).
- **Mechanism:** The `SkillManager` parses this manifest before loading the skill.
- **Execution:** When a user installs a skill, they are presented with a capability prompt (e.g., *"WeatherSkill requests network access. Allow? [Y/n]"*). Granted permissions are logged in `config/settings.json`. If a skill attempts an operation outside its approved capabilities, the `Executor` blocks the action and throws a `PermissionDeniedError`.

---

## 3. Memory Management: Working Memory vs. Core Beliefs

**Problem:** The `ConversationContext` only stores the last 50 turns. Long-term user preferences (e.g., "Always use VSCode," "My project directory is X") are lost upon reboot or queue pruning.
**Solution:** Bifurcated Memory System (Short-Term vs. Core)

- **Architecture:** Introduce a `core_memory.sqlite` database to complement the JSON-based `ConversationContext`.
- **Mechanism (Phase 2):** The LLM-native NLP engine is given a system prompt function: `commit_to_memory(key, value)`.
- **Execution:** When a user explicitly states a preference or a fact, the LLM triggers a memory commit. At the start of every session, these "Core Beliefs" are retrieved and injected into the system prompt, ensuring JARVIS behaves consistently across sessions without polluting the short-term working context.

---

## 4. Ecosystem: The Skill Installer & Dependency Isolation

**Problem:** Third-party skills downloaded from GitHub will have conflicting Python dependencies (e.g., differing library versions). Installing them globally breaks the host application.
**Solution:** Subprocess Virtual Environments

- **Architecture:** Introduce a new CLI command: `jarvis --install-skill <github-url>`.
- **Mechanism:** The installer clones the skill into `skills/third_party/<skill_name>` and automatically runs `python -m venv venv` to create an isolated environment specifically for that skill. It then installs the skill's `requirements.txt`.
- **Execution:** Instead of importing third-party skills directly into the JARVIS memory space, the `SkillManager` triggers them as secure subprocesses using the skill's local virtual environment executable. This guarantees dependency isolation and enhances security.

---

## 5. Hardware Constraints: VRAM Orchestration (Phase 2)

**Problem:** Running a local LLM via Ollama alongside a local Whisper model can easily exceed the VRAM of standard 8GB GPUs, causing Out-Of-Memory (OOM) crashes.
**Solution:** Explicit Model Eviction and Swapping

- **Architecture:** Implement a `ModelManager` orchestrator responsible for VRAM allocation.
- **Mechanism:** The system treats VRAM as a mutually exclusive resource between the listening phase and the processing phase.
- **Execution:**
  1. During `LISTENING` / `TRANSCRIBING`, the LLM is explicitly evicted from VRAM (e.g., via Ollama's `keep_alive=0` API call) to make room for Whisper.
  2. Once transcription succeeds, Whisper is forcibly moved to CPU RAM (`model.cpu()`).
  3. The LLM is re-loaded into VRAM for the `PARSING` / `EXECUTING` phase.
  4. This ping-pong strategy introduces a minor latency hit (1-2 seconds) but guarantees absolute stability on mid-range hardware.
