import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wordle import VALID_WORDS, score_guess

from wordle_ai.client import GuessFeedback
from wordle_ai.solver import BayesianSolver, best_guess, expected_information_gain, initial_belief, update_belief


def feedback_for(guess: str, answer: str) -> GuessFeedback:
    statuses = score_guess(guess, answer)
    return GuessFeedback(guess=guess, letters=tuple(zip(guess, statuses)), is_win=answer == guess)


class InitialBeliefTests(unittest.TestCase):
    def test_uniform_prior_sums_to_one(self):
        belief = initial_belief(["apple", "grape", "chase"])
        self.assertAlmostEqual(sum(belief.values()), 1.0)
        self.assertEqual(set(belief), {"apple", "grape", "chase"})
        for prob in belief.values():
            self.assertAlmostEqual(prob, 1 / 3)

    def test_empty_pool_raises(self):
        with self.assertRaises(ValueError):
            initial_belief([])


class UpdateBeliefTests(unittest.TestCase):
    def test_filters_out_inconsistent_candidates(self):
        belief = initial_belief(["apple", "grape", "chase", "place"])
        feedback = feedback_for("apple", "apple")  # all-correct win feedback
        updated = update_belief(belief, feedback)
        self.assertEqual(set(updated), {"apple"})
        self.assertAlmostEqual(updated["apple"], 1.0)

    def test_renormalizes_survivors_uniformly(self):
        # Neither "chase" nor "chose" contains a "z", so an all-absent
        # feedback for "zzzzz" is consistent with both and should renormalize
        # to a 50/50 belief between them.
        belief = initial_belief(["chase", "chose"])
        feedback = feedback_for("zzzzz", "chase")
        updated = update_belief(belief, feedback)
        self.assertEqual(set(updated), {"chase", "chose"})
        self.assertAlmostEqual(updated["chase"], 0.5)
        self.assertAlmostEqual(updated["chose"], 0.5)

    def test_no_survivors_raises(self):
        # All-correct feedback for "apple" is inconsistent with a belief that
        # only contains "grape".
        with self.assertRaises(ValueError):
            update_belief({"grape": 1.0}, feedback_for("apple", "apple"))


class InformationGainTests(unittest.TestCase):
    def test_perfectly_predictable_guess_has_zero_entropy(self):
        # If every remaining candidate produces the same feedback pattern for
        # a guess, that guess carries zero expected information.
        belief = initial_belief(["aaaaa"])
        self.assertEqual(expected_information_gain("bbbbb", belief), 0.0)

    def test_discriminating_guess_has_positive_entropy(self):
        belief = initial_belief(["apple", "grape"])
        gain = expected_information_gain("apple", belief)
        self.assertGreater(gain, 0.0)

    def test_best_guess_picks_max_entropy_candidate(self):
        # "aabbb" splits {"aaaaa","aaabb"} into two distinct feedback patterns
        # (full entropy); a guess with no letters in common splits them into one.
        belief = initial_belief(["aaaaa", "aaabb"])
        chosen = best_guess(belief, guess_pool=["zzzzz", "aabbb"])
        self.assertEqual(chosen, "aabbb")


class BayesianSolverEndToEndTests(unittest.TestCase):
    def test_converges_on_known_answers_within_six_guesses(self):
        pool = sorted(VALID_WORDS)
        sample = pool[::47]  # spread across the pool without testing all ~440 words
        for answer in sample:
            with self.subTest(answer=answer):
                solver = BayesianSolver(VALID_WORDS)
                for attempt in range(6):
                    guess = solver.next_guess()
                    feedback = feedback_for(guess, answer)
                    solver.observe(feedback)
                    if feedback.is_win:
                        break
                self.assertTrue(feedback.is_win, f"failed to solve {answer!r} within 6 guesses")
                self.assertEqual(solver.candidates_remaining, 1)

    def test_belief_narrows_monotonically(self):
        solver = BayesianSolver(VALID_WORDS)
        answer = "chase"
        previous = solver.candidates_remaining
        for _ in range(3):
            guess = solver.next_guess()
            feedback = feedback_for(guess, answer)
            solver.observe(feedback)
            if feedback.is_win:
                break
            self.assertLessEqual(solver.candidates_remaining, previous)
            previous = solver.candidates_remaining


if __name__ == "__main__":
    unittest.main()
