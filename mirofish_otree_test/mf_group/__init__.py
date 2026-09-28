import json
import time
from pathlib import Path

from otree.api import *

doc = """
MiroFish Phase 0 test app: 2-player group, plain form field page (not live),
a WaitPage that requires both group members, and 2 rounds so we can test
round-by-round barrier semantics.
"""

MARKER_FILE = Path(__file__).parent / "barrier_markers.jsonl"


class C(BaseConstants):
    NAME_IN_URL = 'mf_group'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 2


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    contribution = models.IntegerField(min=0, max=100, label="How much do you contribute?")


# PAGES
class Contribute(Page):
    form_model = 'player'
    form_fields = ['contribution']


class ResultsWaitPage(WaitPage):
    body_text = "Waiting for the other participant in your group."

    @staticmethod
    def after_all_players_arrive(group: Group):
        # This only runs once BOTH players in the group have submitted
        # Contribute for this round. We log it to a file so the test
        # harness can verify (outside the DB) that the barrier fired,
        # and so we can prove "all N participants of a group have
        # submitted round r" is detectable server-side.
        contributions = [p.contribution for p in group.get_players()]
        record = {
            "event": "after_all_players_arrive",
            "round_number": group.round_number,
            "group_id_in_subsession": group.id_in_subsession,
            "contributions": contributions,
            "timestamp": time.time(),
        }
        with MARKER_FILE.open("a") as f:
            f.write(json.dumps(record) + "\n")


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            group_contributions=[p.contribution for p in player.group.get_players()]
        )


page_sequence = [Contribute, ResultsWaitPage, Results]
