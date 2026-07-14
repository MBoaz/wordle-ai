"""Bayesian filter solver for Wordle.

Feedback is a deterministic function of (guess, answer), so the Bayesian
update has a closed form: a candidate's likelihood is 1 if it would have
produced the observed feedback and 0 otherwise. Applying Bayes' rule with a
0/1 likelihood against a uniform prior collapses to filtering out
inconsistent candidates and renormalizing the survivors to uniform.

Guess selection maximizes expected information gain: for each candidate
guess, we compute the Shannon entropy (in bits) of the distribution of
feedback patterns it would induce over the current belief, and pick the
guess whose feedback is hardest to predict in advance -- the one that on
average narrows the belief the most.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Iterable, Optional, Tuple

from wordle import LetterStatus, score_guess
from wordle_ai.client import GuessFeedback

Belief = Dict[str, float]
Pattern = Tuple[LetterStatus, ...]


def initial_belief(word_pool: Iterable[str]) -> Belief:
    """Uniform prior over the candidate word pool."""
    pool = sorted(set(word_pool))
    if not pool:
        raise ValueError("word_pool must not be empty")
    prior = 1.0 / len(pool)
    return {word: prior for word in pool}


def update_belief(belief: Belief, feedback: GuessFeedback) -> Belief:
    """Bayesian update given the observed feedback for feedback.guess.

    Likelihood is 1 for candidates whose simulated feedback matches what was
    observed, 0 otherwise, so this reduces to filter-and-renormalize.
    """
    observed: Pattern = tuple(status for _, status in feedback.letters)

    survivors = {
        word: prob
        for word, prob in belief.items()
        if prob > 0 and score_guess(feedback.guess, word) == observed
    }
    if not survivors:
        raise ValueError("no candidates remain consistent with observed feedback")

    total = sum(survivors.values())
    return {word: prob / total for word, prob in survivors.items()}


def expected_information_gain(guess: str, belief: Belief) -> float:
    """Entropy (bits) of the feedback-pattern distribution `guess` induces
    over `belief`. Higher means the guess is expected to narrow the belief
    more, since its outcome is less predictable in advance."""
    pattern_mass: Dict[Pattern, float] = defaultdict(float)
    for candidate, prob in belief.items():
        if prob <= 0:
            continue
        pattern_mass[score_guess(guess, candidate)] += prob

    return -sum(p * math.log2(p) for p in pattern_mass.values() if p > 0)


def best_guess(belief: Belief, guess_pool: Optional[Iterable[str]] = None) -> str:
    """The guess (from guess_pool, defaulting to the belief's own candidates)
    that maximizes expected information gain against the current belief."""
    candidates = sorted(guess_pool) if guess_pool is not None else sorted(belief)
    return max(candidates, key=lambda g: (expected_information_gain(g, belief), -belief.get(g, 0.0), g))


class BayesianSolver:
    """Drives guess selection via a belief over the answer, updated via
    update_belief() after each round of feedback."""

    def __init__(self, word_pool: Iterable[str]):
        self.belief: Belief = initial_belief(word_pool)

    @property
    def candidates_remaining(self) -> int:
        return len(self.belief)

    @property
    def most_likely(self) -> str:
        return max(self.belief, key=lambda w: (self.belief[w], w))

    def next_guess(self) -> str:
        return best_guess(self.belief)

    def observe(self, feedback: GuessFeedback) -> None:
        self.belief = update_belief(self.belief, feedback)
