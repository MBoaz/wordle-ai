"""Interactive harness that drives a wordle.WordleGame through GameClient.

Proves the wordle-ai <-> wordle-clone interface works end to end. Guess
selection is manual for now; a solver will replace the input() call later.
"""
from __future__ import annotations

import sys

from wordle import LetterStatus

from wordle_ai.client import GameClient, GuessFeedback, InvalidGuessError

_COLOR = {
    LetterStatus.CORRECT: "\033[42m\033[30m",
    LetterStatus.PRESENT: "\033[43m\033[30m",
    LetterStatus.ABSENT: "\033[100m\033[37m",
}
_RESET = "\033[0m"


def render(feedback: GuessFeedback) -> str:
    return "".join(f"{_COLOR[status]} {ch.upper()} {_RESET}" for ch, status in feedback.letters)


def main() -> int:
    client = GameClient()
    print(f"wordle-ai harness -- {client.attempts_left} attempts. Type a 5-letter guess.")

    while not client.is_over:
        raw = input(f"[{client.attempts_left} left] guess: ").strip()
        try:
            feedback = client.submit_guess(raw)
        except InvalidGuessError as exc:
            print(f"  {exc}")
            continue
        print("  " + render(feedback))

    if client.is_won:
        print(f"Solved in {len(client.history)} guesses! The word was {client.answer.upper()}.")
        return 0
    print(f"Out of attempts. The word was {client.answer.upper()}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
