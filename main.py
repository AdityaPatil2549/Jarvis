"""
JARVIS-Lite — Main entry point.
Usage: python main.py [--cli] [--verbose] [--no-voice] [--test-tts TEXT]

Source of truth: Implementation_plan.md §6.2
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def parse_args():
    parser = argparse.ArgumentParser(description='JARVIS-Lite Voice Assistant')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--no-voice', action='store_true',
                        help='Disable TTS output')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable colored output')
    parser.add_argument('--ascii', action='store_true',
                        help='ASCII-only mode (no Unicode)')
    parser.add_argument('--test-tts', type=str, metavar='TEXT',
                        help='Test TTS with given text and exit')
    parser.add_argument('--config', type=str,
                        help='Custom config file path')
    parser.add_argument('--install-skill', type=str, metavar='URL',
                        help='Install a third-party skill from GitHub URL')
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Handle --install-skill ─────────────────────────────────────────
    if args.install_skill:
        from skills.installer import install_skill
        success = install_skill(args.install_skill)
        sys.exit(0 if success else 1)

    # ── Handle --test-tts ──────────────────────────────────────────────
    if args.test_tts:
        import time
        from core.tts import KokoroTTS, Pyttsx3TTS
        tts = KokoroTTS()
        if not tts.initialize():
            print("Kokoro unavailable, trying pyttsx3 fallback...")
            tts = Pyttsx3TTS()
            if not tts.initialize():
                print("TTS initialization failed.")
                sys.exit(1)
        print(f"Speaking: '{args.test_tts}'")
        tts.speak(args.test_tts)
        time.sleep(5)
        tts.shutdown()
        sys.exit(0)

    # ── Handle --verbose logger setup ──────────────────────────────────
    if args.verbose:
        from utils.logger import JarvisLogger
        JarvisLogger.reset()
        JarvisLogger(verbose=True, log_file="logs/jarvis.log")

    # ── First-run wizard ───────────────────────────────────────────────
    from core.config_manager import ConfigManager
    config_path = args.config if args.config else None
    cm = ConfigManager(config_path=config_path)
    if not cm.CONFIG_FILE.exists():
        from core.first_run_wizard import run_setup_wizard
        run_setup_wizard()

    # ── Start JARVIS ───────────────────────────────────────────────────
    from jarvis_engine import JarvisEngine
    from interface.cli import CLI

    engine = JarvisEngine()
    cli = CLI(engine)

    # Apply CLI flags
    if args.no_color:
        cli.ui = __import__('interface.ui', fromlist=['TerminalUI']).TerminalUI(no_color=True)
    if args.ascii:
        cli.ui = __import__('interface.ui', fromlist=['TerminalUI']).TerminalUI(ascii_only=True)

    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        engine.shutdown()


if __name__ == "__main__":
    main()
