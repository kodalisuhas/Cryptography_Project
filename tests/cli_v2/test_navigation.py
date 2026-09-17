"""Tests for the V2 navigation engine."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.cli_v2.navigation import (
    NavigationEngine,
    StepResult,
    WizardStep,
)


class TestNavigationEngine:
    """Test suite for NavigationEngine step-stack behavior."""

    def test_push_and_pop_step(self):
        """Test pushing and popping steps from history stack."""
        engine = NavigationEngine()
        step1 = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)
        step2 = WizardStep("step2", "Prompt 2", "Help 2", lambda x: x)

        engine.push_step(step1)
        engine.push_step(step2)

        assert engine.history_depth() == 2
        assert engine.current_step() == step2

        popped = engine.pop_step()
        assert popped == step2
        assert engine.history_depth() == 1
        assert engine.current_step() == step1

    def test_pop_empty_stack_returns_none(self):
        """Test that popping from empty stack returns None."""
        engine = NavigationEngine()
        assert engine.pop_step() is None
        assert engine.current_step() is None

    def test_store_and_get_value(self):
        """Test storing and retrieving values by key."""
        engine = NavigationEngine()
        engine.store_value("key1", "value1")
        engine.store_value("key2", 42)

        assert engine.get_value("key1") == "value1"
        assert engine.get_value("key2") == 42
        assert engine.get_value("missing") is None

    def test_clear_values(self):
        """Test clearing all stored values."""
        engine = NavigationEngine()
        engine.store_value("key1", "value1")
        engine.clear_values()
        assert engine.get_value("key1") is None

    def test_valid_input_progression(self):
        """Test valid input advances to NEXT action."""
        engine = NavigationEngine()
        step = WizardStep("test", "Enter value", "Help text", lambda x: x.upper())

        with patch("builtins.input", return_value="hello"):
            result = engine.prompt_step(step)

        assert result.action == "NEXT"
        assert result.value == "HELLO"
        assert engine.get_value("test") == "HELLO"

    def test_invalid_input_retry_loop(self):
        """Test that invalid input triggers retry without advancing."""
        engine = NavigationEngine()
        call_count = 0

        def validator(x: str) -> str:
            nonlocal call_count
            call_count += 1
            if x != "valid":
                raise ValueError("Must be 'valid'")
            return x

        step = WizardStep("test", "Enter 'valid'", "Help", validator)

        with patch("builtins.input", side_effect=["invalid", "also_invalid", "valid"]):
            result = engine.prompt_step(step)

        assert result.action == "NEXT"
        assert result.value == "valid"
        assert call_count == 3

    def test_back_token_lowercase(self):
        """Test lowercase 'b' triggers BACK action."""
        engine = NavigationEngine()
        step1 = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)
        step2 = WizardStep("step2", "Prompt 2", "Help 2", lambda x: x)

        engine.push_step(step1)
        engine.push_step(step2)

        with patch("builtins.input", return_value="b"):
            result = engine.prompt_step(step2)

        assert result.action == "BACK"
        # Should return to step1
        assert engine.current_step() == step1

    def test_back_token_uppercase(self):
        """Test uppercase 'B' triggers BACK action."""
        engine = NavigationEngine()
        step1 = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)
        step2 = WizardStep("step2", "Prompt 2", "Help 2", lambda x: x)

        engine.push_step(step1)
        engine.push_step(step2)

        with patch("builtins.input", return_value="B"):
            result = engine.prompt_step(step2)

        assert result.action == "BACK"

    def test_back_token_back_word(self):
        """Test 'back' word triggers BACK action."""
        engine = NavigationEngine()
        step1 = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)
        step2 = WizardStep("step2", "Prompt 2", "Help 2", lambda x: x)

        engine.push_step(step1)
        engine.push_step(step2)

        with patch("builtins.input", return_value="back"):
            result = engine.prompt_step(step2)

        assert result.action == "BACK"

    def test_back_at_root_reprompts(self):
        """Test BACK at first step re-prompts with message."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)

        # Don't push step first - prompt_step does that internally
        with patch("builtins.input", side_effect=["b", "valid"]):
            result = engine.prompt_step(step)

        assert result.action == "NEXT"
        assert result.value == "valid"

    def test_cancel_token_lowercase(self):
        """Test lowercase 'c' triggers CANCEL action."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)

        engine.push_step(step)
        engine.store_value("key", "value")

        with patch("builtins.input", return_value="c"):
            result = engine.prompt_step(step)

        assert result.action == "CANCEL"
        assert engine.history_depth() == 0
        assert engine.get_value("key") is None

    def test_cancel_token_uppercase(self):
        """Test uppercase 'C' triggers CANCEL action."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)

        engine.push_step(step)

        with patch("builtins.input", return_value="C"):
            result = engine.prompt_step(step)

        assert result.action == "CANCEL"

    def test_cancel_token_cancel_word(self):
        """Test 'cancel' word triggers CANCEL action."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)

        engine.push_step(step)

        with patch("builtins.input", return_value="cancel"):
            result = engine.prompt_step(step)

        assert result.action == "CANCEL"

    def test_help_token_question_mark(self):
        """Test '?' triggers help display and re-prompts."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help text here", lambda x: x)

        engine.push_step(step)

        with patch("builtins.input", side_effect=["?", "valid"]):
            result = engine.prompt_step(step)

        assert result.action == "NEXT"
        assert result.value == "valid"

    def test_help_token_help_word(self):
        """Test 'help' word triggers help display."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help text here", lambda x: x)

        engine.push_step(step)

        with patch("builtins.input", side_effect=["help", "valid"]):
            result = engine.prompt_step(step)

        assert result.action == "NEXT"

    def test_eof_triggers_cancel(self):
        """Test EOF (Ctrl+D) triggers CANCEL action."""
        engine = NavigationEngine()
        step = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)

        engine.push_step(step)

        with patch("builtins.input", side_effect=EOFError()):
            result = engine.prompt_step(step)

        assert result.action == "CANCEL"

    def test_prompt_choice_valid_selection(self):
        """Test prompt_choice with valid numeric selection."""
        engine = NavigationEngine()
        options = ["Option A", "Option B", "Option C"]

        with patch("builtins.input", return_value="2"):
            result = engine.prompt_choice("Choose:", options, default=1)

        assert result.action == "NEXT"
        assert result.value == 1  # 0-based index

    def test_prompt_choice_default_on_empty(self):
        """Test prompt_choice uses default on empty input."""
        engine = NavigationEngine()
        options = ["Option A", "Option B"]

        with patch("builtins.input", return_value=""):
            result = engine.prompt_choice("Choose:", options, default=2)

        assert result.action == "NEXT"
        assert result.value == 1  # default=2 -> index 1

    def test_prompt_choice_invalid_then_valid(self):
        """Test prompt_choice retries on invalid input."""
        engine = NavigationEngine()
        options = ["A", "B"]

        with patch("builtins.input", side_effect=["5", "0", "abc", "1"]):
            result = engine.prompt_choice("Choose:", options, default=1)

        assert result.action == "NEXT"
        assert result.value == 0

    def test_prompt_choice_back_navigation(self):
        """Test prompt_choice supports BACK navigation."""
        engine = NavigationEngine()
        step1 = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)
        engine.push_step(step1)
        options = ["A", "B"]

        with patch("builtins.input", side_effect=["b", "1"]):
            # First call returns BACK
            result = engine.prompt_choice("Choose:", options)
            assert result.action == "BACK"

            # Second call (after pushing step1 again) succeeds
            engine.push_step(step1)
            with patch("builtins.input", return_value="2"):
                result2 = engine.prompt_choice("Choose:", options)
                assert result2.action == "NEXT"
                assert result2.value == 1

    def test_prompt_choice_cancel_navigation(self):
        """Test prompt_choice supports CANCEL navigation."""
        engine = NavigationEngine()
        options = ["A", "B"]

        with patch("builtins.input", return_value="c"):
            result = engine.prompt_choice("Choose:", options)

        assert result.action == "CANCEL"
        assert engine.history_depth() == 0

    def test_prompt_choice_help_display(self):
        """Test prompt_choice displays help on '?' token."""
        engine = NavigationEngine()
        options = ["A", "B"]

        with patch("builtins.input", side_effect=["?", "1"]):
            result = engine.prompt_choice("Choose:", options, help_text="Helpful hint")

        assert result.action == "NEXT"

    def test_prompt_yes_no_default_yes(self):
        """Test prompt_yes_no with default Yes."""
        engine = NavigationEngine()

        with patch("builtins.input", return_value=""):
            result = engine.prompt_yes_no("Continue?", default_yes=True)

        assert result.action == "NEXT"
        assert result.value is True

    def test_prompt_yes_no_default_no(self):
        """Test prompt_yes_no with default No."""
        engine = NavigationEngine()

        with patch("builtins.input", return_value=""):
            result = engine.prompt_yes_no("Continue?", default_yes=False)

        assert result.action == "NEXT"
        assert result.value is False

    def test_prompt_yes_no_explicit_yes(self):
        """Test prompt_yes_no with explicit 'y'."""
        engine = NavigationEngine()

        with patch("builtins.input", return_value="y"):
            result = engine.prompt_yes_no("Continue?")

        assert result.action == "NEXT"
        assert result.value is True

    def test_prompt_yes_no_explicit_no(self):
        """Test prompt_yes_no with explicit 'n'."""
        engine = NavigationEngine()

        with patch("builtins.input", return_value="n"):
            result = engine.prompt_yes_no("Continue?")

        assert result.action == "NEXT"
        assert result.value is False

    def test_prompt_yes_no_case_insensitive(self):
        """Test prompt_yes_no accepts Y/y/N/n case-insensitively."""
        engine = NavigationEngine()

        with patch("builtins.input", side_effect=["Y", "N", "Yes", "No"]):
            r1 = engine.prompt_yes_no("Q1?")
            r2 = engine.prompt_yes_no("Q2?")
            r3 = engine.prompt_yes_no("Q3?")
            r4 = engine.prompt_yes_no("Q4?")

        assert r1.value is True
        assert r2.value is False
        assert r3.value is True
        assert r4.value is False

    def test_prompt_yes_no_invalid_then_valid(self):
        """Test prompt_yes_no retries on invalid input."""
        engine = NavigationEngine()

        with patch("builtins.input", side_effect=["maybe", "y"]):
            result = engine.prompt_yes_no("Continue?")

        assert result.action == "NEXT"
        assert result.value is True

    def test_prompt_yes_no_back_navigation(self):
        """Test prompt_yes_no supports BACK navigation."""
        engine = NavigationEngine()
        step1 = WizardStep("step1", "Prompt 1", "Help 1", lambda x: x)
        engine.push_step(step1)

        with patch("builtins.input", side_effect=["b", "y"]):
            result = engine.prompt_yes_no("Continue?")
            assert result.action == "BACK"

    def test_prompt_yes_no_cancel_navigation(self):
        """Test prompt_yes_no supports CANCEL navigation."""
        engine = NavigationEngine()

        with patch("builtins.input", return_value="c"):
            result = engine.prompt_yes_no("Continue?")

        assert result.action == "CANCEL"
        assert engine.history_depth() == 0

    def test_prompt_yes_no_help_display(self):
        """Test prompt_yes_no displays help on '?' token."""
        engine = NavigationEngine()

        with patch("builtins.input", side_effect=["?", "y"]):
            result = engine.prompt_yes_no("Continue?", help_text="Confirm action")

        assert result.action == "NEXT"
        assert result.value is True


class TestWizardStep:
    """Test WizardStep dataclass."""

    def test_wizard_step_creation(self):
        """Test WizardStep can be created with all fields."""
        def validator(x: str) -> str:
            return x.strip()

        step = WizardStep(
            name="test_step",
            prompt_text="Enter something:",
            help_text="This is help",
            validator=validator
        )

        assert step.name == "test_step"
        assert step.prompt_text == "Enter something:"
        assert step.help_text == "This is help"
        assert step.validator(" hello ") == "hello"


class TestStepResult:
    """Test StepResult dataclass."""

    def test_step_result_creation(self):
        """Test StepResult can be created with value and action."""
        result = StepResult(value="test", action="NEXT")
        assert result.value == "test"
        assert result.action == "NEXT"

    def test_step_result_cancel_no_value(self):
        """Test StepResult for CANCEL can have None value."""
        result = StepResult(value=None, action="CANCEL")
        assert result.value is None
        assert result.action == "CANCEL"