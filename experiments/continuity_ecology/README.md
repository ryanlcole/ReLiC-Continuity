# 𓋹 ReLiC — Autonomous Ecology Experiment v0.1

Status: **independent, deterministic experiment; NONCANONICAL**. Not a reconstruction of private ReLiC, RuneCore, WaveCore, or Shaelvien source. Python 3.11+, standard library only. Synthetic data only.

## What this tests

After an initial world is created, a Python program—not a ChatGPT conversation—advances time, maintains organism identities, grows stationary plants, processes local water/carbon and simplified sunlight/lunar cycles, and gives mobile organisms energy/water needs, reproduction conditions, resource use, and bounded Q-learning. Two adults (`A`, `B`) begin with offspring `C`, which follows whichever parent survives, then explores independently if both are unavailable. No consciousness or real biochemical emergence is claimed. Observer predictions use deep copies and are labeled HYPOTHESIS.

## Run independently

```bash
python experiments/continuity_ecology/run.py init --seed 19
python experiments/continuity_ecology/run.py tick --ticks 250
python experiments/continuity_ecology/run.py inspect
python experiments/continuity_ecology/run.py imagine --ticks 50
python -m unittest discover -s tests -p 'test_ecology.py' -v
```

`init` refuses to overwrite an existing saved world. `tick` is bounded to 1000 steps per invocation and the world stops automatically after 20,000 ticks. A single `state.json` is written atomically and holds the full chain of observations and Q tables. Every event is SHA-256 hash chained (tamper-evident, **not** externally anchored or proof of physical truth). The data model retains deleted/dead identities and provenance, and no private records are used.

An explicitly synthetic lifecycle test may use `python experiments/continuity_ecology/run.py delete --id A`; deletion does not erase a record. Do **not** delete living entities when seeking unbiased emergence data; it is a controlled intervention.

## Optional unattended host

`.github/workflows/autonomous-ecology.yml` has a GitHub Actions scheduled trigger, independent of ChatGPT. **Once this contribution is reviewed and merged to the default branch**, GitHub Actions can advance 12 steps approximately every 20 minutes and commit only synthetic state to an isolated branch, `experiment-autonomous-ecology-state`. The viewer reads that branch and can also open a downloaded `state.json` locally. It never directly modifies the canonical Shaelvien world or the ReLiC ledger.

**Availability limitations:** GitHub schedules can be delayed/skipped. Public-repository schedules may disable after inactivity. Actions permission settings must permit `contents: write`; otherwise the state cannot persist. Github-hosted runners are ephemeral, **not** permanent processes. No claim that hosting is already enabled or a scheduled run completed. Scheduled state commits are intentionally segregated from main; verify after the first actual execution.

## Scientific limitations

This is a toy agent-based system, not an atom-by-atom Earth/Sun/Moon/periodic-table model, not an LLM, and not evidence of awareness, morality, or subjective feelings. Environmental sensing is a simplified four-bit local observation; learned navigation uses Q-values, and parent-following is an explicit rule. The observer is read-only and can produce counterfactual hypotheses, not perform unsanctioned world actions. Birth/death/cycle outcomes may reveal patterns *within these modeled rules* only.

## Continuity rules

ID ≠ representation; representation ≠ truth; unknown ≠ fact; memory ≠ canon. Here all events are classified VERIFIED_SIMULATION_RESULT, never as verified real-world events. Imagined outcomes are HYPOTHESIS. Human project authority remains separate. **AI-assisted code: ChatGPT, sponsored for human review; local tests run before PR.**
