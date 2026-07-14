"""Thin client wrapping wordle.WordleGame for CLI drivers and, later, a solver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from wordle import GuessResult, InvalidGuessError, LetterStatus, WordleGame

__all__ = ["GameClient", "GuessFeedback", "InvalidGuessError"]


@dataclass(frozen=True)
class GuessFeedback:
    """A guess and its per-letter feedback, shaped for a solver to consume."""

    guess: str
    letters: tuple  # tuple[tuple[str, LetterStatus], ...], one entry per letter position
    is_win: bool

    @classmethod
    def from_result(cls, result: GuessResult) -> "GuessFeedback":
        return cls(guess=result.guess, letters=tuple(zip(result.guess, result.statuses)), is_win=result.is_win)

    def as_string(self) -> str:
        symbols = {LetterStatus.CORRECT: "G", LetterStatus.PRESENT: "Y", LetterStatus.ABSENT: "X"}
        return "".join(symbols[status] for _, status in self.letters)


class GameClient:
    """Request/response wrapper around a WordleGame round."""

    def __init__(self, answer: Optional[str] = None, max_attempts: int = 6):
        self._game = WordleGame(answer=answer, max_attempts=max_attempts)
        self.history: list = []

    @property
    def attempts_left(self) -> int:
        return self._game.attempts_left

    @property
    def is_won(self) -> bool:
        return self._game.is_won

    @property
    def is_over(self) -> bool:
        return self._game.is_over

    @property
    def answer(self) -> str:
        return self._game.answer

    def submit_guess(self, word: str) -> GuessFeedback:
        feedback = GuessFeedback.from_result(self._game.guess(word))
        self.history.append(feedback)
        return feedback
