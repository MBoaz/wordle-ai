"""CLI that drives a wordle.WordleGame with the Bayesian filter solver.

Each turn, the solver proposes the guess expected to narrow the candidate
set the most, submits it through GameClient, and updates its belief from
the returned feedback.
"""
from __future__ import annotations

import argparse
import sys

from wordle import LetterStatus, VALID_WORDS

from wordle_ai.client import GameClient, GuessFeedback, InvalidGuessError
from wordle_ai.solver import BayesianSolver

_COLOR = {
    LetterStatus.CORRECT: "\033[42m\033[30m",
    LetterStatus.PRESENT: "\033[43m\033[30m",
    LetterStatus.ABSENT: "\033[100m\033[37m",
}
_RESET = "\033[0m"


def render(feedback: GuessFeedback) -> str:
    return "".join(f"{_COLOR[status]} {ch.upper()} {_RESET}" for ch, status in feedback.letters)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Solve a Wordle round with the Bayesian filter solver.")
    parser.add_argument("--answer", help="fix the answer instead of picking one at random (for testing)")
    args = parser.parse_args(argv)

    client = GameClient(answer=args.answer)
    solver = BayesianSolver(VALID_WORDS)
    print(f"Solving -- {client.attempts_left} attempts, {solver.candidates_remaining} candidate words.")

    while not client.is_over:
        guess = solver.next_guess()
        try:
            feedback = client.submit_guess(guess)
        except InvalidGuessError as exc:
            print(f"  solver proposed an invalid guess {guess!r}: {exc}")
            return 2
        solver.observe(feedback)
        print(f"[{client.attempts_left} left] {guess} -> " + render(feedback) + f"  ({solver.candidates_remaining} candidates left)")

    if client.is_won:
        print(f"Solved in {len(client.history)} guesses! The word was {client.answer.upper()}.")
        return 0
    print(f"Out of attempts. The word was {client.answer.upper()}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
