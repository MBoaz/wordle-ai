# Wordle AI

This is the Wordle solver I'm building to test out a Bayesian filter approach to optimizing guesses. It doesn't implement Wordle itself — it plays a real round against [wordle-clone](../wordle-clone), installed as an editable dependency, driving it entirely through its programmatic interface rather than typing into its CLI.

## How to Start

Set up the virtual environment and install both packages editable (only needs to be done once):

```bash
python -m venv .venv
.venv\Scripts\pip install -e ../wordle-clone
.venv\Scripts\pip install -e .
```

Then solve a round:

```bash
.venv\Scripts\python -m wordle_ai.cli
```

Pass `--answer` to fix the word instead of picking one at random, which is useful for testing:

```bash
.venv\Scripts\python -m wordle_ai.cli --answer chase
```

### Example
Solving -- 6 attempts, 552 candidate words. <BR>
[5 left] alert -> <span style="background-color: #c9b458; color: white; padding: 5px; font-weight: bold;">A</span><span style="background-color: #787c7e; color: white; padding: 5px; font-weight: bold;">L</span><span style="background-color: #c9b458; color: white; padding: 5px; font-weight: bold;">E</span><span style="background-color: #787c7e; color: white; padding: 5px; font-weight: bold;">R</span><span style="background-color: #787c7e; color: white; padding: 5px; font-weight: bold;">T</span> (21 candidates left) <BR>
[4 left] space -> <span style="background-color: #c9b458; color: white; padding: 5px; font-weight: bold;">S</span><span style="background-color: #787c7e; color: white; padding: 5px; font-weight: bold;">P</span><span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">A</span><span style="background-color: #c9b458; color: white; padding: 5px; font-weight: bold;">C</span><span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">E</span> (1 candidates left) <BR>
[3 left] chase -> <span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">C</span><span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">H</span><span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">A</span><span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">S</span><span style="background-color: #6aaa64; color: white; padding: 5px; font-weight: bold;">E</span> (1 candidates left) <BR>
Solved in 3 guesses! The word was CHASE.

## Code Overview

Everything lives under `wordle_ai/`:

- **`client.py`** — the thin adapter between this project and `wordle-clone`:
  - `GameClient` — wraps a `wordle.WordleGame`. `submit_guess(word)` forwards the guess to the underlying game and converts its `GuessResult` into a `GuessFeedback`; `attempts_left`, `is_won`, `is_over`, and `answer` just proxy the wrapped game's properties. This is the only place that talks to `wordle` directly for gameplay — everything else works through this client.
  - `GuessFeedback` — a solver-shaped view of a guess result: `letters` is a tuple of `(character, LetterStatus)` pairs (rather than the parallel `guess`/`statuses` tuples `GuessResult` uses), which is the shape `solver.py` expects when updating its belief. `as_string()` renders it as a `G`/`Y`/`X` pattern for display.

- **`solver.py`** — the Bayesian filter itself. Feedback is a deterministic function of (guess, answer), so a Bayesian update with a 0/1 likelihood collapses to filter-and-renormalize rather than needing real probability math:
  - `initial_belief(word_pool)` — builds a uniform prior: every word in the pool starts equally likely to be the answer.
  - `update_belief(belief, feedback)` — for each candidate still under consideration, replays `wordle.score_guess(feedback.guess, candidate)` and keeps only the candidates whose simulated feedback matches what was actually observed. The survivors' probabilities are renormalized back to sum to 1. Raises if a feedback pattern is inconsistent with every remaining candidate (a sign of a bug upstream, since real feedback always keeps at least the true answer alive).
  - `expected_information_gain(guess, belief)` — buckets the current belief's candidates by the feedback pattern `guess` would produce against each of them, then computes the Shannon entropy (bits) of that bucket distribution. A guess whose outcome is hard to predict in advance (probability mass spread evenly across many possible patterns) scores higher, because whichever pattern actually comes back will rule out more of the belief.
  - `best_guess(belief, guess_pool=None)` — picks the guess (by default, from the belief's own remaining candidates) with the highest expected information gain, breaking ties first by higher prior probability, then alphabetically, so results are reproducible.
  - `BayesianSolver` — stateful wrapper around the above: `next_guess()` proposes a word, `observe(feedback)` folds the result back into `belief`, `candidates_remaining` and `most_likely` expose the current state of the search.

- **`cli.py`** — the driver loop. Builds a `GameClient` and a `BayesianSolver` seeded from `wordle.VALID_WORDS`, then alternates `solver.next_guess()` -> `client.submit_guess()` -> `solver.observe()` until the round ends, printing each guess as colored terminal tiles alongside how many candidates remain. Takes an optional `--answer` flag for reproducible test runs.

- **`__init__.py`** — re-exports the public surface: `GameClient`, `GuessFeedback`, `BayesianSolver`, `best_guess`, `expected_information_gain`, `initial_belief`, `update_belief`.

## Programmatic Interface

`solver.py` doesn't touch `wordle_ai.client` at all — it only depends on `wordle.LetterStatus` and `wordle.score_guess` from the `wordle-clone` package. That keeps the belief-update math testable against hypothetical guess/answer pairs without ever spinning up a real `WordleGame`:

```python
from wordle import VALID_WORDS
from wordle_ai.solver import BayesianSolver

solver = BayesianSolver(VALID_WORDS)
guess = solver.next_guess()  # e.g. "alert"
```

`client.py` is the layer that bridges `GuessFeedback` (what the solver consumes) to `GuessResult` (what `wordle.WordleGame` produces), so swapping in a different game implementation later would only mean rewriting `client.py`, not `solver.py`.

## Future Work

1. Weight the prior by real-world word frequency instead of a uniform distribution over the word list
2. Widen `best_guess`'s candidate pool beyond the belief's own remaining words (a guess that can't itself be the answer can still be more informative)
3. Track and report solve-rate statistics across many random rounds
