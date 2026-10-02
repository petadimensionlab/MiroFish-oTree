# MiroFish-oTree

oTree apps that let [MiroFish-Offline](https://github.com/nikmcfly/MiroFish-Offline) LLM agents play behavioral-economics games, with debate rounds on MiroFish's simulated social network between game rounds.

The game side lives here (MIT). It talks to a MiroFish experiment bridge over HTTP only; the bridge, step-server and analysis tools are part of the MiroFish-Offline codebase (AGPL-3.0).

## Apps

| App | Purpose |
|---|---|
| `pd_debate` | Iterated prisoner's dilemma, 2-player fixed pairs × 10 rounds. Bots ask the bridge for decisions; a round barrier notifies the bridge once all pairs have submitted |
| `pgg` | Linear public goods game, fixed groups of 4 × 10 rounds, endowment 20, multiplier 1.6 (session config `pgg_multiplier`). Bots ask the bridge (`game='pgg'`) for contributions; export `pgg_custom.csv` |
| `beauty` | p-beauty contest, fixed groups of 4 × 10 rounds, guess 0–100, closest to 2/3 of the mean wins 20 points (`game='beauty'`) |
| `trust` | Trust (investment) game, fixed pairs and roles × 10 rounds, both get 10, amount sent tripled; sequential (`game='trust'`) |
| `ultimatum` | Ultimatum game, fixed pairs and roles × 10 rounds, pie 20; sequential (`game='ultimatum'`) |
| `mf_group`, `label_test`, `live_test` | Probes used to verify oTree 6 behavior (bot HTTP calls, wait-page barriers, `participant.label`, `live_method`) |

## `pd_debate`

- Payoffs (session config `pd_payoffs`): R=30, T=50, S=0, P=10
- Choices are stored as `A` = cooperate, `B` = defect; what agents see (letters or symbols, randomized) is decided by the bridge
- `bridge_client.py` never raises: timeouts, exhausted retries or an unreachable bridge fall back to a default choice flagged `decision_missing`
- Custom export `pd_debate_custom.csv`: one row per agent × round (choice, partner's choice, payoff, decision source, missing flag, reason, chat transcript)

Session configs in `settings.py`: `pd_debate` (fixed-strategy bots, no bridge needed), `pd_debate_faults`, `pd_debate_llm`, `pd_debate_llm_debate`, `pd_debate_llm_debate_topic`, `pd_debate_llm_opening`, `pd_debate_llm_debate_noinject`, `pd_debate_llm_debate_noinject_swap`, `pd_debate_llm_nochat`, and the reference-only `pd_debate_llm_chat` / `pd_debate_llm_chat_debate`. Bridge settings are passed as `bridge_<name>` keys.

Pair chat (`bridge_chat_turns > 0`): before each decision the two partners exchange private messages; the round's transcript is stored in `chat_transcript` (JSON) and exported. **It is a reference condition only**: the study asks whether platform discourse changes behavior, and a direct pair chat lets partners settle their choices between themselves, so study runs keep `chat_turns=0`.

## Sequential games and seating

In `trust` and `ultimatum` the first movers decide, a `StageBarrier` wait page (all groups) reports their decisions to the bridge (`/stage_complete`), and the second movers then get decisions that see the first move. Each app has `*_llm` session configs (no chat, no debate, no feed) and fixed-strategy bots without a bridge.

`MF_AGENT_IDS` (JSON list) sets which MiroFish agent sits in which participant slot for any session config; consecutive slots form the pairs / groups. Use it with MiroFish's `make_workplace_sim.py` `agent_order` to seat colleagues from the same company but different departments together.

## Network talk, channel dyads and replication seeds

Apps `pd_debate`, `pgg`, `beauty`, `trust`, `ultimatum` are described above; what was added since is on the session-config side (all in `settings.py`, bridge settings documented in MiroFish-Offline `docs/otree-integration/README.md` §11).

- **Network talk (MiroFish NOTES #54).** `pd_net_off` (control: same labelling, no talk), `pd_net_er`, `pd_net_ba`, `pd_net_ws`, `pd_net_ring`; `pgg_net_off`, `pgg_net_ba`, `pgg_net_er`. 16 participants, `NET_COMMON`: LLM policy, no feed, no result injection, session labels with `bridge_label_order_per_agent=True`, comprehension check and belief survey, mean degree 4, contact mean 1.0, dispersion 0.5, 2 turns. Participants talk one to one with graph neighbours who are never their PD partner / group mate.
- **Channel-compatible dyads and memory (NOTES #55).** Same 16 agents of `sim_workplace_ch_s1_n48` (`bridge_net_channels=True`): `pd_net_off_ch` (no talk, ledger written), `pd_net_ba_ch0` (β 0, every conversation answered), `pd_net_ba_ch` (β 1.0, reply model `reach`), `pd_net_ba_ch_mem` (adds `bridge_net_memory_mode='decay'`, half life 2, 3200 chars), optional `pd_net_ba_chsel` and `pd_net_ba_chrep`; pgg versions `pgg_net_off_ch`, `pgg_net_ba_ch0`, `pgg_net_ba_ch`, `pgg_net_ba_ch_mem`. `pd_net_ba_chsel` and `pd_net_ba_chrep` have not been run.
- **`network_transcript`** (`pd_debate` only): one JSON field per agent × round with that round's one-to-one conversations with non-partners (`conv_id`, `other_agent_id`, `initiator`, messages), next to `chat_transcript` in `pd_debate_custom.csv`.
- **`MF_BRIDGE_SEED`** (default 0): session config `bridge_seed`, the bridge's `seed` for labels, network graph, contact rates and contact draws. The LLM's own sampling is not seeded, so the same seed does not reproduce a run exactly; use different seeds for replication runs.
- **`MF_AGENT_IDS`** now seats agents in every app above (`agent_ids` in the session config).

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
