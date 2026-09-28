import os
import json
import time
from pathlib import Path

from otree.api import Bot, Submission, expect
from . import Contribute, Results, C

LOG_FILE = Path(__file__).parent / "bot_network_log.jsonl"

# A trivial local HTTP server (see ../network_test_server.py) that this bot
# will hit synchronously inside play_round, to test whether the CLI bot
# runner supports blocking outbound HTTP calls during a round.
SERVER_URL = os.environ.get("MF_TEST_SERVER_URL", "http://127.0.0.1:8765/agent-decision")
DO_NETWORK_CALL = os.environ.get("MF_TEST_DO_NETWORK_CALL", "0") == "1"

# Item 5 probe: does an UNCAUGHT exception inside play_round abort the whole
# `otree test` run, or does the runner just skip/continue? Gated on env var
# so normal runs are unaffected.
RAISE_UNCAUGHT = os.environ.get("MF_TEST_RAISE_UNCAUGHT", "0") == "1"


class PlayerBot(Bot):
    def play_round(self):
        if RAISE_UNCAUGHT and self.player.id_in_group == 1 and self.round_number == 1:
            raise RuntimeError("MF_TEST deliberate uncaught exception in play_round")

        contribution = 50
        status = "skipped"
        elapsed = 0.0

        if DO_NETWORK_CALL:
            import requests

            t0 = time.time()
            try:
                resp = requests.post(
                    SERVER_URL,
                    json={
                        "participant_code": self.participant.code,
                        "round_number": self.round_number,
                        "id_in_group": self.player.id_in_group,
                    },
                    timeout=10,
                )
                elapsed = time.time() - t0
                contribution = int(resp.json()["contribution"])
                status = "ok"
            except Exception as exc:  # noqa
                elapsed = time.time() - t0
                contribution = 50
                status = f"error:{exc!r}"

            with LOG_FILE.open("a") as f:
                f.write(
                    json.dumps(
                        {
                            "participant_code": self.participant.code,
                            "round_number": self.round_number,
                            "elapsed_seconds": elapsed,
                            "status": status,
                            "contribution": contribution,
                        }
                    )
                    + "\n"
                )

        yield Contribute, dict(contribution=contribution)
        yield Results
