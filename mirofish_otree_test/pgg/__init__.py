import json
import os
import time
from pathlib import Path

from otree.api import *

from pd_debate import bridge_client

doc = """
Linear public goods game for MiroFish agents.

Fixed groups of 4 for NUM_ROUNDS rounds. Each round every member gets
ENDOWMENT points and chooses a contribution 0..ENDOWMENT; the group total
is multiplied (session config 'pgg_multiplier', default 1.6, i.e. MPCR 0.4)
and shared equally. Contributing nothing is the dominant strategy; the
subgame-perfect equilibrium of the finitely repeated game is zero in every
round, full contribution is the social optimum. Agents only; decisions come
from the MiroFish bridge (game='pgg') or fixed-strategy bots.
"""

BARRIER_LOG = Path(__file__).parent / "barrier_log.jsonl"


class C(BaseConstants):
    NAME_IN_URL = 'pgg'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 10
    ENDOWMENT = 20
    DEFAULT_MULTIPLIER = 1.6


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    total_contribution = models.IntegerField()


class Player(BasePlayer):
    agent_id = models.IntegerField()
    contribution = models.IntegerField(min=0, max=C.ENDOWMENT, label="How many points do you put into the project?")
    # Exact round points; oTree's payoff is rounded to whole points
    earnings = models.FloatField()
    decision_source = models.StringField(blank=True)
    decision_reason = models.LongStringField(blank=True)
    decision_latency_sec = models.FloatField(blank=True)
    decision_missing = models.BooleanField(initial=False, blank=True)


def multiplier(session):
    return session.config.get('pgg_multiplier', C.DEFAULT_MULTIPLIER)


def pgg_points(own, total, session):
    return round(C.ENDOWMENT - own + multiplier(session) * total / C.PLAYERS_PER_GROUP, 4)


# Module-level function: as a Subsession method oTree 6 ignores it
# (MiroFish docs/otree-integration/phase0-otree.md, finding 5).
def creating_session(subsession: Subsession):
    agent_ids = subsession.session.config.get('agent_ids')
    for player in subsession.get_players():
        idx = player.participant.id_in_session - 1
        player.agent_id = agent_ids[idx] if agent_ids else idx
        if subsession.round_number == 1:
            player.participant.label = f"agent_{player.agent_id}"

    if subsession.round_number == 1 and bridge_client.enabled():
        agents = []
        for group in subsession.get_groups():
            members = [p.agent_id for p in group.get_players()]
            agents += [dict(agent_id=a, group_agent_ids=members) for a in members]
        bridge_client.configure_game(
            subsession.session, 'pgg',
            dict(endowment=C.ENDOWMENT, multiplier=multiplier(subsession.session),
                 group_size=C.PLAYERS_PER_GROUP),
            agents, C.NUM_ROUNDS, BARRIER_LOG)


def set_payoffs(group: Group):
    players = group.get_players()
    group.total_contribution = sum(p.contribution for p in players)
    for p in players:
        p.earnings = pgg_points(p.contribution, group.total_contribution, group.session)
        p.payoff = p.earnings


def on_round_complete(subsession: Subsession):
    players = subsession.get_players()
    record = dict(
        event="round_complete",
        session_code=subsession.session.code,
        round_number=subsession.round_number,
        n_players=len(players),
        mean_contribution=sum(p.contribution for p in players) / len(players),
        timestamp=time.time(),
    )
    if bridge_client.enabled():
        record['bridge'] = bridge_client.notify_round_complete(
            subsession.session.code, subsession.round_number,
            dict(
                n_players=record['n_players'],
                mean_contribution=record['mean_contribution'],
                outcomes=[
                    dict(agent_id=p.agent_id, choice=str(p.contribution), payoff=p.earnings,
                         group_total=p.group.total_contribution,
                         group_agent_ids=[q.agent_id for q in p.group.get_players()],
                         source=p.field_maybe_none('decision_source'),
                         missing=p.field_maybe_none('decision_missing'))
                    for p in players
                ],
            ),
        )
    with BARRIER_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


class Contribute(Page):
    form_model = 'player'
    form_fields = ['contribution', 'decision_source', 'decision_reason',
                   'decision_latency_sec', 'decision_missing']

    @staticmethod
    def vars_for_template(player: Player):
        return dict(multiplier=multiplier(player.session))


class GroupWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    pass


class RoundBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_round_complete


page_sequence = [Contribute, GroupWaitPage, Results, RoundBarrier]


def custom_export(players):
    yield [
        'session_code', 'participant_label', 'agent_id', 'round_number', 'group_id', 'id_in_group',
        'contribution', 'others_contributions', 'group_total', 'earnings',
        'decision_source', 'decision_missing', 'decision_latency_sec', 'decision_reason',
    ]
    for p in players:
        if p.field_maybe_none('contribution') is None:
            continue
        others = [q.field_maybe_none('contribution') for q in p.get_others_in_group()]
        yield [
            p.session.code, p.participant.label, p.agent_id, p.round_number, p.group.id_in_subsession,
            p.id_in_group, p.contribution, json.dumps(others), p.group.field_maybe_none('total_contribution'),
            p.field_maybe_none('earnings'),
            p.field_maybe_none('decision_source'), p.field_maybe_none('decision_missing'),
            p.field_maybe_none('decision_latency_sec'), p.field_maybe_none('decision_reason'),
        ]
