import json
import time
from pathlib import Path

from otree.api import *

from pd_debate import bridge_client

doc = """
Ultimatum game for MiroFish agents.

Fixed pairs, fixed roles, NUM_ROUNDS rounds. The first person proposes how
many of PIE points go to the second person; the second person accepts
(split as proposed) or rejects (both 0). Subgame-perfect equilibrium:
the smallest offer, accepted. Humans offer 40-50 %, and offers below
about 20 % are often rejected.

Sequential, like trust: /stage_complete after the proposals.
"""

BARRIER_LOG = Path(__file__).parent / "barrier_log.jsonl"


class C(BaseConstants):
    NAME_IN_URL = 'ultimatum'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
    PIE = 20


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    offer = models.IntegerField()
    accepted = models.BooleanField()


class Player(BasePlayer):
    agent_id = models.IntegerField()
    offer = models.IntegerField(min=0, max=C.PIE, blank=True, label="Points for the second person")
    response = models.StringField(choices=['accept', 'reject'], blank=True)
    decision_source = models.StringField(blank=True)
    decision_reason = models.LongStringField(blank=True)
    decision_latency_sec = models.FloatField(blank=True)
    decision_missing = models.BooleanField(initial=False, blank=True)


def role_of(player):
    return 1 if player.id_in_group == 1 else 2


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
            agents += [dict(agent_id=p.agent_id, group_agent_ids=members, role=role_of(p))
                       for p in group.get_players()]
        bridge_client.configure_game(subsession.session, 'ultimatum', dict(pie=C.PIE),
                                     agents, C.NUM_ROUNDS, BARRIER_LOG)


def on_first_moves(subsession: Subsession):
    for group in subsession.get_groups():
        group.offer = group.get_player_by_id(1).offer
    if bridge_client.enabled():
        bridge_client.notify_stage_complete(subsession.session.code, subsession.round_number, [
            dict(agent_id=g.get_player_by_id(1).agent_id, choice=str(g.offer)) for g in subsession.get_groups()])


def set_payoffs(group: Group):
    first, second = group.get_player_by_id(1), group.get_player_by_id(2)
    group.accepted = second.response == 'accept'
    first.payoff = C.PIE - group.offer if group.accepted else 0
    second.payoff = group.offer if group.accepted else 0


def on_round_complete(subsession: Subsession):
    players = subsession.get_players()
    groups = subsession.get_groups()
    record = dict(event="round_complete", session_code=subsession.session.code,
                  round_number=subsession.round_number, n_players=len(players),
                  mean_offer=sum(g.offer for g in groups) / len(groups),
                  acceptance_rate=sum(g.accepted for g in groups) / len(groups), timestamp=time.time())
    if bridge_client.enabled():
        record['bridge'] = bridge_client.notify_round_complete(
            subsession.session.code, subsession.round_number,
            dict(n_players=record['n_players'], mean_offer=record['mean_offer'], outcomes=[
                dict(agent_id=p.agent_id, choice=str(p.offer) if role_of(p) == 1 else p.response,
                     offer=p.group.offer, accepted=p.group.accepted, payoff=float(p.payoff), role=role_of(p),
                     source=p.field_maybe_none('decision_source'),
                     missing=p.field_maybe_none('decision_missing'))
                for p in players]))
    with BARRIER_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


class Propose(Page):
    form_model = 'player'
    form_fields = ['offer', 'decision_source', 'decision_reason', 'decision_latency_sec', 'decision_missing']

    @staticmethod
    def is_displayed(player):
        return role_of(player) == 1


class StageBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_first_moves


class Respond(Page):
    form_model = 'player'
    form_fields = ['response', 'decision_source', 'decision_reason', 'decision_latency_sec', 'decision_missing']

    @staticmethod
    def is_displayed(player):
        return role_of(player) == 2


class GroupWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    pass


class RoundBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_round_complete


page_sequence = [Propose, StageBarrier, Respond, GroupWaitPage, Results, RoundBarrier]


def custom_export(players):
    yield ['session_code', 'participant_label', 'agent_id', 'round_number', 'pair_id', 'role',
           'partner_agent_id', 'offer', 'accepted', 'payoff',
           'decision_source', 'decision_missing', 'decision_latency_sec', 'decision_reason']
    for p in players:
        if p.group.field_maybe_none('accepted') is None:
            continue
        yield [p.session.code, p.participant.label, p.agent_id, p.round_number, p.group.id_in_subsession,
               role_of(p), p.get_others_in_group()[0].agent_id, p.group.offer, int(p.group.accepted), p.payoff,
               p.field_maybe_none('decision_source'), p.field_maybe_none('decision_missing'),
               p.field_maybe_none('decision_latency_sec'), p.field_maybe_none('decision_reason')]
