"""Navigation engine for V2 guided wizards.

Provides a reusable step-stack history with universal token interception
for Back (b/back), Cancel (c/cancel), and Help (?) navigation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class StepResult:
    """Encapsulates the outcome of a wizard configuration step."""
    value: Any
    action: str  # "NEXT", "BACK", "CANCEL"


@dataclass(frozen=True)
class WizardStep:
    """Represents an interactive step with prompt, validation, and contextual help."""
    name: str
    prompt_text: str
    help_text: str
    validator: Callable[[str], Any]


class NavigationEngine:
    """Manages the step history stack and user input loop."""

    # Navigation tokens (case-insensitive)
    BACK_TOKENS = {"b", "back"}
    CANCEL_TOKENS = {"c", "cancel"}
    HELP_TOKENS = {"?", "help"}

    def __init__(self) -> None:
        self._history: list[WizardStep] = []
        self._values: dict[str, Any] = {}

    def push_step(self, step: WizardStep) -> None:
        """Push a new step onto the history stack."""
        self._history.append(step)

    def pop_step(self) -> Optional[WizardStep]:
        """Pop and return the previous step, or None if at stack bottom."""
        if not self._history:
            return None
        return self._history.pop()

    def current_step(self) -> Optional[WizardStep]:
        """Return the current step without removing it."""
        if not self._history:
            return None
        return self._history[-1]

    def history_depth(self) -> int:
        """Return the number of steps in history."""
        return len(self._history)

    def store_value(self, key: str, value: Any) -> None:
        """Store a value associated with a step name."""
        self._values[key] = value

    def get_value(self, key: str) -> Any:
        """Retrieve a stored value by key."""
        return self._values.get(key)

    def clear_values(self) -> None:
        """Clear all stored values."""
        self._values.clear()

    @staticmethod
    def _normalize_token(raw: str) -> str:
        """Normalize input token for comparison."""
        return raw.strip().lower()

    def _is_back(self, raw: str) -> bool:
        return self._normalize_token(raw) in self.BACK_TOKENS

    def _is_cancel(self, raw: str) -> bool:
        return self._normalize_token(raw) in self.CANCEL_TOKENS

    def _is_help(self, raw: str) -> bool:
        return self._normalize_token(raw) in self.HELP_TOKENS

    def _display_help(self, step: WizardStep) -> None:
        """Display contextual help for the current step."""
        print(f"\n  Help: {step.help_text}\n")

    def prompt_step(self, step: WizardStep) -> StepResult:
        """Prompt for a single step with validation and navigation token handling.

        Loops until valid input is received or a navigation action occurs.
        """
        self.push_step(step)

        while True:
            try:
                raw = input(f"{step.prompt_text}: ").strip()
            except EOFError:
                return StepResult(value=None, action="CANCEL")

            # Check navigation tokens first
            if self._is_back(raw):
                self.pop_step()  # Remove current step
                prev = self.pop_step()  # Remove and return previous step
                if prev is None:
                    # At root - re-prompt current step
                    self.push_step(step)
                    print("  (Already at first step)")
                    continue
                return StepResult(value=None, action="BACK")

            if self._is_cancel(raw):
                self.clear_values()
                self._history.clear()
                return StepResult(value=None, action="CANCEL")

            if self._is_help(raw):
                self._display_help(step)
                continue

            # Validate input
            try:
                validated = step.validator(raw)
            except ValueError as exc:
                print(f"  Error: {exc}")
                continue

            # Store the validated value and advance
            self.store_value(step.name, validated)
            return StepResult(value=validated, action="NEXT")

    def prompt_choice(
        self,
        prompt: str,
        options: list[str],
        default: int = 1,
        help_text: str = ""
    ) -> StepResult:
        """Prompt for a choice from a numbered list with navigation support.

        Args:
            prompt: The prompt text to display.
            options: List of option descriptions (1-indexed for display).
            default: Default option number (1-indexed).
            help_text: Contextual help text for this choice.

        Returns:
            StepResult with the selected option index (0-based) as value.
        """
        step = WizardStep(
            name=f"choice_{len(self._history)}",
            prompt_text=prompt,
            help_text=help_text,
            validator=lambda x: x  # Will validate manually
        )
        self.push_step(step)

        while True:
            # Display options
            print(f"\n{prompt}")
            for i, opt in enumerate(options, 1):
                suffix = " (default)" if i == default else ""
                print(f"  {i}. {opt}{suffix}")

            try:
                raw = input(f"Select [1-{len(options)}] [{default}]: ").strip()
            except EOFError:
                return StepResult(value=None, action="CANCEL")

            # Check navigation tokens
            if self._is_back(raw):
                self.pop_step()
                prev = self.pop_step()
                if prev is None:
                    self.push_step(step)
                    print("  (Already at first step)")
                    continue
                return StepResult(value=None, action="BACK")

            if self._is_cancel(raw):
                self.clear_values()
                self._history.clear()
                return StepResult(value=None, action="CANCEL")

            if self._is_help(raw):
                self._display_help(step)
                continue

            # Handle empty input (use default)
            if not raw:
                selected = default - 1
                self.store_value(step.name, selected)
                return StepResult(value=selected, action="NEXT")

            # Parse numeric choice
            try:
                choice = int(raw)
            except ValueError:
                print(f"  Enter a number between 1 and {len(options)}")
                continue

            if not 1 <= choice <= len(options):
                print(f"  Enter a number between 1 and {len(options)}")
                continue

            selected = choice - 1
            self.store_value(step.name, selected)
            return StepResult(value=selected, action="NEXT")

    def prompt_yes_no(
        self,
        prompt: str,
        default_yes: bool = True,
        help_text: str = ""
    ) -> StepResult:
        """Prompt for a yes/no confirmation with navigation support.

        Args:
            prompt: The prompt text.
            default_yes: Whether 'Y' is the default (True) or 'N' (False).
            help_text: Contextual help text.

        Returns:
            StepResult with boolean value (True for yes, False for no).
        """
        default_char = "Y" if default_yes else "N"
        other_char = "n" if default_yes else "y"
        hint = f"[{default_char}/{other_char}]"

        step = WizardStep(
            name=f"confirm_{len(self._history)}",
            prompt_text=f"{prompt} {hint}",
            help_text=help_text,
            validator=lambda x: x
        )
        self.push_step(step)

        while True:
            try:
                raw = input(f"{prompt} {hint}: ").strip().lower()
            except EOFError:
                return StepResult(value=None, action="CANCEL")

            if self._is_back(raw):
                self.pop_step()
                prev = self.pop_step()
                if prev is None:
                    self.push_step(step)
                    print("  (Already at first step)")
                    continue
                return StepResult(value=None, action="BACK")

            if self._is_cancel(raw):
                self.clear_values()
                self._history.clear()
                return StepResult(value=None, action="CANCEL")

            if self._is_help(raw):
                self._display_help(step)
                continue

            if not raw:
                result = default_yes
                self.store_value(step.name, result)
                return StepResult(value=result, action="NEXT")

            if raw in ("y", "yes"):
                result = True
            elif raw in ("n", "no"):
                result = False
            else:
                print("  Enter 'y' or 'n'")
                continue

            self.store_value(step.name, result)
            return StepResult(value=result, action="NEXT")