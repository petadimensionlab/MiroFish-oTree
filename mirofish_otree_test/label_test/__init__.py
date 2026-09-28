from otree.api import *

doc = """
MiroFish Phase 0 test app: verifies that participant.label can be assigned
inside creating_session() for a headless bot run, and that the label shows
up in CSV export. Mirrors the intended mf_{agent_id} join-key scheme.
"""


class C(BaseConstants):
    NAME_IN_URL = 'label_test'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


def creating_session(subsession):
    import sys
    players = subsession.get_players()
    print(f"DEBUG creating_session round={subsession.round_number} num_players={len(players)}", file=sys.stderr)
    if subsession.round_number == 1:
        for i, p in enumerate(players):
            p.participant.label = f"mf_{i}"
            print(f"DEBUG set label mf_{i} on participant code={p.participant.code} readback={p.participant.label}", file=sys.stderr)


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass


class Intro(Page):
    pass


page_sequence = [Intro]
