"""
interface/ui.py - Terminal UI for JARVIS-Lite.
Provides all visual output, animations, and state management.

Source of truth: frontend_guidelines.md (verbatim implementation)
"""

import time
import threading
import textwrap
from typing import Optional, List, Callable


# ============================================================================
# COLOR DEFINITIONS (ANSI 256-color)
# ============================================================================

class Colors:
    """Terminal color codes - 256 color mode"""

    # Core UI Colors
    PRIMARY = '\033[38;5;39m'      # Bright Blue
    SUCCESS = '\033[38;5;35m'      # Green
    WARNING = '\033[38;5;214m'     # Orange
    ERROR = '\033[38;5;196m'       # Red
    INFO = '\033[38;5;245m'        # Gray

    # State Colors
    LISTENING = '\033[38;5;51m'    # Cyan
    PROCESSING = '\033[38;5;141m'  # Purple
    EXECUTING = '\033[38;5;226m'   # Yellow

    # Text Colors
    TEXT = '\033[38;5;252m'        # Light Gray
    DIM = '\033[38;5;242m'         # Dark Gray
    BRIGHT = '\033[38;5;231m'      # White

    # Formatting
    RESET = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    @classmethod
    def disable(cls):
        """Disable colors (for non-TTY or --no-color flag)"""
        for attr in dir(cls):
            if not attr.startswith('_') and attr.isupper():
                setattr(cls, attr, '')


# ============================================================================
# ICONS & SYMBOLS
# ============================================================================

class Icons:
    """Unicode icons for visual feedback"""

    # Status
    SUCCESS = '✓'
    ERROR = '✗'
    WARNING = '⚠'
    INFO = 'ℹ'

    # States
    LISTENING = '🎤'
    PROCESSING = '⚙'
    EXECUTING = '▶'
    SPEAKING = '🔊'
    LIGHTBULB = '💡'

    # Spinners
    SPINNER_DOTS = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    @classmethod
    def disable(cls):
        """Disable icons (for ASCII-only terminals)"""
        cls.SUCCESS = '+'
        cls.ERROR = 'x'
        cls.WARNING = '!'
        cls.INFO = 'i'
        cls.LISTENING = '>'
        cls.PROCESSING = '*'
        cls.EXECUTING = '>'
        cls.SPEAKING = ')'
        cls.LIGHTBULB = '*'
        cls.SPINNER_DOTS = ['|', '/', '-', '\\']


# ============================================================================
# BOX DRAWING
# ============================================================================

class Box:
    """Box drawing characters"""
    TL = '┌'
    TR = '┐'
    BL = '└'
    BR = '┘'
    H = '─'
    V = '│'
    DTL = '╔'
    DTR = '╗'
    DBL = '╚'
    DBR = '╝'
    DH = '═'
    DV = '║'
    L = '├'
    R = '┤'
    T = '┬'
    B = '┴'
    C = '┼'

    @classmethod
    def disable(cls):
        """Disable box drawing (for ASCII-only terminals)"""
        cls.TL = cls.TR = cls.BL = cls.BR = '+'
        cls.H = cls.DH = '-'
        cls.V = cls.DV = '|'
        cls.DTL = cls.DTR = cls.DBL = cls.DBR = '+'
        cls.L = cls.R = '+'


# ============================================================================
# MAIN UI CLASS
# ============================================================================

class TerminalUI:
    """Complete terminal UI system for JARVIS-Lite."""

    def __init__(self, no_color: bool = False, ascii_only: bool = False):
        self.width = 62
        self.no_color = no_color
        self.ascii_only = ascii_only

        if no_color:
            Colors.disable()
        if ascii_only:
            Icons.disable()
            Box.disable()

        # Animation state
        self._animation_active = False
        self._animation_thread: Optional[threading.Thread] = None

    # ========================================================================
    # SCREEN MANAGEMENT
    # ========================================================================

    def clear_screen(self):
        print('\033[2J\033[H', end='', flush=True)

    def clear_line(self):
        print('\r\033[K', end='', flush=True)

    def move_cursor_up(self, lines: int = 1):
        print(f'\033[{lines}A', end='', flush=True)

    # ========================================================================
    # STARTUP SCREEN
    # ========================================================================

    def show_startup(self):
        """Display startup screen with logo."""
        self.clear_screen()
        logo = f"""
{Colors.PRIMARY}{Box.DTL}{'═' * 60}{Box.DTR}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.RESET}{'':^60}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.BRIGHT}  ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗  {Colors.RESET}{'':>14}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.BRIGHT}  ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝  {Colors.RESET}{'':>14}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.BRIGHT}  ██║███████║██████╔╝██║   ██║██║███████╗  {Colors.RESET}{'':>14}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.BRIGHT}  ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║  {Colors.RESET}{'':>14}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.BRIGHT}  ██║██║  ██║██║  ██║ ╚████╔╝ ██║███████║  {Colors.RESET}{'':>14}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.BRIGHT}  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝  {Colors.RESET}{'':>14}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.RESET}{'':^60}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.DIM}           Voice Assistant v1.0            {Colors.RESET}{'':>16}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DV}{Colors.RESET}{'':^60}{Colors.PRIMARY}{Box.DV}{Colors.RESET}
{Colors.PRIMARY}{Box.DBL}{'═' * 60}{Box.DBR}{Colors.RESET}
"""
        print(logo)
        print()

    def show_loading_step(self, message: str, duration: float = 0.5):
        """Show a loading step with spinner animation."""
        print(f"{Colors.DIM}[{Icons.PROCESSING}] {message}...{Colors.RESET}",
              end='', flush=True)
        time.sleep(duration)
        self.clear_line()
        print(f"{Colors.SUCCESS}[{Icons.SUCCESS}] {message}{Colors.RESET}")

    def show_startup_complete(self):
        print()
        print(f"{Colors.PRIMARY}{Box.H * self.width}{Colors.RESET}")
        print()

    # ========================================================================
    # MAIN STATES
    # ========================================================================

    def show_idle_prompt(self):
        """Display idle state prompt."""
        print()
        print(f"{Colors.DIM}{Box.H * self.width}{Colors.RESET}")
        print(f"{Colors.PRIMARY}JARVIS{Colors.RESET} Ready")
        print(f"{Colors.DIM}Press {Colors.BRIGHT}SPACE{Colors.RESET}"
              f"{Colors.DIM} to speak | Type command | "
              f"'{Colors.BRIGHT}help{Colors.RESET}{Colors.DIM}' for info{Colors.RESET}")
        print(f"{Colors.DIM}{Box.H * self.width}{Colors.RESET}")
        print()
        print(f"{Colors.BRIGHT}>{Colors.RESET} ", end='', flush=True)

    def show_listening(self):
        self._start_animation(self._animate_listening)

    def show_processing(self, message: str = "Processing"):
        self._start_animation(lambda: self._animate_spinner(message))

    def show_executing(self, action: str):
        print(f"\r{Colors.EXECUTING}{Icons.EXECUTING} {action}...{Colors.RESET}",
              end='', flush=True)

    # ========================================================================
    # ADVANCED UI STATES
    # ========================================================================

    def show_stt_cancel_window(self, transcribed_text: str):
        """Display the 1.5s STT cancellation window (F1.7)."""
        print(f"\r{Colors.LISTENING}{Icons.INFO} I heard: "
              f"'{transcribed_text}'  (Press ESC to cancel){Colors.RESET}",
              end='', flush=True)

    def show_permission_prompt(self, skill_name: str, capability: str):
        """Display manifest permission warning."""
        print(f"\n{Colors.ERROR}{Icons.WARNING} SECURITY ALERT{Colors.RESET}")
        print(f"Skill '{skill_name}' is requesting "
              f"{Colors.BOLD}{capability}{Colors.RESET} access.")
        print("Allow? (Y/n): ", end='', flush=True)

    def show_undo_feedback(self, action_name: str):
        """Display undo feedback."""
        print(f"\n{Colors.INFO}{Icons.SUCCESS} Undid action: {action_name}{Colors.RESET}")

    def show_complete(self, message: str):
        self.clear_line()
        print(f"{Colors.SUCCESS}{Icons.SUCCESS} {message}{Colors.RESET}")

    # ========================================================================
    # USER INPUT/OUTPUT
    # ========================================================================

    def show_user_input(self, text: str):
        self.clear_line()
        print(f"{Colors.BRIGHT}You:{Colors.RESET} {text}")

    def show_response(self, text: str):
        print(f"{Colors.BRIGHT}{Icons.SPEAKING} JARVIS:{Colors.RESET} {text}")

    # ========================================================================
    # ERROR HANDLING
    # ========================================================================

    def show_error(self, error_type: str, message: str,
                   suggestion: Optional[str] = None):
        """Display formatted error message in a box."""
        self.clear_line()
        print()

        width = 60
        print(f"{Colors.ERROR}{Box.DTL}{Box.DH * (width - 2)}{Box.DTR}{Colors.RESET}")

        header = f"{Icons.ERROR} ERROR: {error_type}"
        padding = max(0, width - len(header) - 4)
        print(f"{Colors.ERROR}{Box.DV}{Colors.RESET} {Colors.ERROR}{header}"
              f"{' ' * padding}{Colors.ERROR}{Box.DV}{Colors.RESET}")

        print(f"{Colors.ERROR}{Box.L}{Box.DH * (width - 2)}{Box.R}{Colors.RESET}")

        for line in textwrap.fill(message, width=width - 4).split('\n'):
            padding = max(0, width - len(line) - 4)
            print(f"{Colors.ERROR}{Box.DV}{Colors.RESET} {line}"
                  f"{' ' * padding} {Colors.ERROR}{Box.DV}{Colors.RESET}")

        if suggestion:
            print(f"{Colors.ERROR}{Box.L}{Box.DH * (width - 2)}{Box.R}{Colors.RESET}")
            sug_header = f"{Icons.LIGHTBULB} Suggestion:"
            padding = max(0, width - len(sug_header) - 4)
            print(f"{Colors.ERROR}{Box.DV}{Colors.RESET} {Colors.WARNING}{sug_header}"
                  f"{Colors.RESET}{' ' * padding} {Colors.ERROR}{Box.DV}{Colors.RESET}")
            for line in textwrap.fill(suggestion, width=width - 4).split('\n'):
                padding = max(0, width - len(line) - 4)
                print(f"{Colors.ERROR}{Box.DV}{Colors.RESET} {line}"
                      f"{' ' * padding} {Colors.ERROR}{Box.DV}{Colors.RESET}")

        print(f"{Colors.ERROR}{Box.DBL}{Box.DH * (width - 2)}{Box.DBR}{Colors.RESET}")
        print()

    def show_warning(self, message: str):
        print(f"{Colors.WARNING}{Icons.WARNING} {message}{Colors.RESET}")

    def show_info(self, message: str):
        print(f"{Colors.INFO}{Icons.INFO} {message}{Colors.RESET}")

    # ========================================================================
    # CLARIFICATION
    # ========================================================================

    def show_clarification(self, question: str, options: List[str] = None):
        """Display clarification prompt with numbered options."""
        print()
        print(f"{Colors.WARNING}{Icons.WARNING} {question}{Colors.RESET}")
        print()
        if options:
            for i, option in enumerate(options, 1):
                print(f"  {Colors.BRIGHT}{i}.{Colors.RESET} {option}")
            print()
            print(f"{Colors.DIM}Say the number or name{Colors.RESET}")
        print()

    # ========================================================================
    # HELP SCREEN
    # ========================================================================

    def show_help(self):
        """Display help screen with all commands."""
        self.clear_screen()
        print(f"{Colors.PRIMARY}{'═' * self.width}{Colors.RESET}")
        print(f"{Colors.BRIGHT}  JARVIS-Lite Commands{Colors.RESET}")
        print(f"{Colors.PRIMARY}{'═' * self.width}{Colors.RESET}")
        print()

        commands = [
            ("File Operations", [
                ("open <file>", "Open file in default application"),
                ("find <query>", "Search for files by name"),
                ("create <name>", "Create new text file"),
            ]),
            ("Application Control", [
                ("open <app>", "Launch application (chrome, vscode, etc.)"),
                ("close <app>", "Close running application"),
            ]),
            ("System Commands", [
                ("volume up/down", "Adjust system volume"),
                ("screenshot", "Take screenshot"),
                ("lock screen", "Lock computer"),
                ("system info", "Show CPU/RAM/Disk usage"),
            ]),
            ("Action Modifiers", [
                ("undo", "Reverse last action"),
                ("repeat / do that again", "Re-execute last command"),
                ("run <macro>", "Execute a named macro"),
            ]),
            ("Assistant", [
                ("help", "Show this help screen"),
                ("exit / quit", "Exit JARVIS-Lite"),
            ]),
        ]

        for category, cmds in commands:
            print(f"{Colors.BRIGHT}{category}:{Colors.RESET}")
            for cmd, desc in cmds:
                print(f"  {Colors.PRIMARY}{cmd:28}{Colors.RESET} "
                      f"{Colors.DIM}{desc}{Colors.RESET}")
            print()

        print(f"{Colors.PRIMARY}{'═' * self.width}{Colors.RESET}")
        print(f"{Colors.DIM}Press Enter to continue...{Colors.RESET}")

    # ========================================================================
    # PROGRESS
    # ========================================================================

    def show_progress(self, message: str, percent: int):
        """Show loading progress bar during initialization."""
        filled = int(percent / 5)
        bar = '█' * filled + '░' * (20 - filled)
        print(f"\r{Colors.PRIMARY}[{bar}]{Colors.RESET} {percent}% {message}",
              end='', flush=True)

    def show_state(self, state):
        """Update display for current state machine state."""
        from models import State
        state_displays = {
            State.IDLE: self.show_idle_prompt,
            State.LISTENING: self.show_listening,
            State.TRANSCRIBING: lambda: self.show_processing("Processing speech"),
            State.PARSING: lambda: self.show_processing("Understanding command"),
            State.EXECUTING: lambda: self.show_executing("Running command"),
        }
        display_fn = state_displays.get(state)
        if display_fn:
            display_fn()

    # ========================================================================
    # ANIMATIONS (PRIVATE)
    # ========================================================================

    def _start_animation(self, animation_func: Callable):
        self._stop_animation()
        self._animation_active = True
        self._animation_thread = threading.Thread(target=animation_func, daemon=True)
        self._animation_thread.start()

    def _stop_animation(self):
        self._animation_active = False
        if self._animation_thread:
            self._animation_thread.join(timeout=0.5)
            self._animation_thread = None

    def _animate_listening(self):
        frames = [
            "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁",
            "▂▃▄▅▆▇█▇▆▅▄▃▂▁▂",
            "▃▄▅▆▇█▇▆▅▄▃▂▁▂▃",
            "▄▅▆▇█▇▆▅▄▃▂▁▂▃▄",
            "▅▆▇█▇▆▅▄▃▂▁▂▃▄▅",
            "▆▇█▇▆▅▄▃▂▁▂▃▄▅▆",
        ]
        idx = 0
        while self._animation_active:
            frame = frames[idx % len(frames)]
            print(f"\r{Colors.LISTENING}{Icons.LISTENING} LISTENING... "
                  f"{frame}{Colors.RESET}", end='', flush=True)
            idx += 1
            time.sleep(0.1)

    def _animate_spinner(self, message: str):
        spinner = Icons.SPINNER_DOTS
        idx = 0
        while self._animation_active:
            char = spinner[idx % len(spinner)]
            print(f"\r{Colors.PROCESSING}{char} {message}...{Colors.RESET}",
                  end='', flush=True)
            idx += 1
            time.sleep(0.08)

    def stop_all_animations(self):
        self._stop_animation()
        self.clear_line()

    def print_separator(self, char: str = None):
        char = char or Box.H
        print(f"{Colors.DIM}{char * self.width}{Colors.RESET}")
