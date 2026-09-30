# MiroFish-oTree

oTree apps that let [MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline) LLM agents play behavioral-economics games, with debate rounds on MiroFish's simulated social network between game rounds.

The game side lives here (MIT). It talks to a MiroFish experiment bridge over HTTP only; the bridge, step-server and analysis tools are part of the MiroFish-Offline codebase (AGPL-3.0).

## Apps

| App | Purpose |
|---|---|
| `pd_debate` | Iterated prisoner's dilemma, 2-player fixed pairs × 10 rounds. Bots ask the bridge for decisions; a round barrier notifies the bridge once all pairs have submitted |
| `pgg` | Linear public goods game, fixed groups of 4 × 10 rounds, endowment 20, multiplier 1.6 (session config `pgg_multiplier`). Bots ask the bridge (`game='pgg'`) for contributions; export `pgg_custom.csv` |
| `mf_group`, `label_test`, `live_test` | Probes used to verify oTree 6 behavior (bot HTTP calls, wait-page barriers, `participant.label`, `live_method`) |

## `pd_debate`

- Payoffs (session config `pd_payoffs`): R=30, T=50, S=0, P=10
- Choices are stored as `A` = cooperate, `B` = defect; what agents see (letters or symbols, randomized) is decided by the bridge
- `bridge_client.py` never raises: timeouts, exhausted retries or an unreachable bridge fall back to a default choice flagged `decision_missing`
- Custom export `pd_debate_custom.csv`: one row per agent × round (choice, partner's choice, payoff, decision source, missing flag, reason, chat transcript)

Session configs in `settings.py`: `pd_debate` (fixed-strategy bots, no bridge needed), `pd_debate_faults`, `pd_debate_llm`, `pd_debate_llm_debate`, `pd_debate_llm_debate_topic`, `pd_debate_llm_opening`, `pd_debate_llm_debate_noinject`, `pd_debate_llm_debate_noinject_swap`, `pd_debate_llm_nochat`, and the reference-only `pd_debate_llm_chat` / `pd_debate_llm_chat_debate`. Bridge settings are passed as `bridge_<name>` keys.

Pair chat (`bridge_chat_turns > 0`): before each decision the two partners exchange private messages; the round's transcript is stored in `chat_transcript` (JSON) and exported. **It is a reference condition only**: the study asks whether platform discourse changes behavior, and a direct pair chat lets partners settle their choices between themselves, so study runs keep `chat_turns=0`.

## Running

```sh
python -m venv .venv && source .venv/bin/activate
pip install "otree==6.0.15" requests   # tested with Python 3.12
cd mirofish_otree_test

# fixed-strategy bots, no bridge
otree test pd_debate 48 --export ./export

# with a running MiroFish bridge
MF_BRIDGE_URL=http://127.0.0.1:5055/api/experiment MF_BRIDGE_TIMEOUT=1800 \
MF_SIMULATION_DIR=<sim_dir> otree test pd_debate_llm_debate 8 --export ./export
```

Client environment: `MF_BRIDGE_URL` (unset = fixed-strategy bots), `MF_BRIDGE_TIMEOUT` (default 10 s), `MF_BRIDGE_ATTEMPTS` (3), `MF_BRIDGE_BACKOFF` (0.5 s × attempt), `MF_SIMULATION_DIR`.

Set `OTREE_SECRET_KEY` and `OTREE_ADMIN_PASSWORD` for anything beyond local testing.

## License

MIT — see [LICENSE](LICENSE).
