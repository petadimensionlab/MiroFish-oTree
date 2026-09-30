import json
import time
from pathlib import Path

from otree.api import *

from pd_debate import bridge_client

doc = """
Trust (investment) game (Berg, Dickhaut & McCabe 1995) for MiroFish agents.

Fixed pairs, fixed roles, NUM_ROUNDS rounds. Both get ENDOWMENT points;
the first person sends 0..ENDOWMENT, which is multiplied by MULTIPLIER; the
second person returns 0..(received). Subgame-perfect equilibrium of the
finitely repeated game: nothing returned, so nothing sent, in every round.
Humans send about half and get roughly what they sent back.

Sequential: after all first movers have decided (StageBarrier) the bridge
is told (/stage_complete) and prefetches the second movers' decisions.
"""

BARRIER_LOG = Path(__file__).parent / "barrier_log.jsonl"


class C(BaseConstants):
    NAME_IN_URL = 'trust'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
    ENDOWMENT = 10
    MULTIPLIER = 3


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    sent = models.IntegerField()
    returned = models.IntegerField()


class Player(BasePlayer):
    agent_id = models.IntegerField()
    send = models.IntegerField(min=0, max=C.ENDOWMENT, blank=True, label="Points to send")
    send_back = models.IntegerField(min=0, blank=True, label="Points to send back")
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
        bridge_client.configure_game(subsession.session, 'trust',
                                     dict(endowment=C.ENDOWMENT, multiplier=C.MULTIPLIER),
                                     agents, C.NUM_ROUNDS, BARRIER_LOG)


def send_back_max(player):
    return C.MULTIPLIER * player.group.sent


def on_first_moves(subsession: Subsession):
    for group in subsession.get_groups():
        group.sent = group.get_player_by_id(1).send
    if bridge_client.enabled():
        bridge_client.notify_stage_complete(subsession.session.code, subsession.round_number, [
            dict(agent_id=g.get_player_by_id(1).agent_id, choice=str(g.sent)) for g in subsession.get_groups()])


def set_payoffs(group: Group):
    first, second = group.get_player_by_id(1), group.get_player_by_id(2)
    group.returned = second.send_back
    first.payoff = C.ENDOWMENT - group.sent + group.returned
    second.payoff = C.ENDOWMENT + C.MULTIPLIER * group.sent - group.returned


def on_round_complete(subsession: Subsession):
    players = subsession.get_players()
    groups = subsession.get_groups()
    record = dict(event="round_complete", session_code=subsession.session.code,
                  round_number=subsession.round_number, n_players=len(players),
                  mean_sent=sum(g.sent for g in groups) / len(groups), timestamp=time.time())
    if bridge_client.enabled():
        record['bridge'] = bridge_client.notify_round_complete(
            subsession.session.code, subsession.round_number,
            dict(n_players=record['n_players'], mean_sent=record['mean_sent'], outcomes=[
                dict(agent_id=p.agent_id, choice=str(p.send if role_of(p) == 1 else p.send_back),
                     sent=p.group.sent, returned=p.group.returned, payoff=float(p.payoff), role=role_of(p),
                     source=p.field_maybe_none('decision_source'),
                     missing=p.field_maybe_none('decision_missing'))
                for p in players]))
    with BARRIER_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


class FirstMove(Page):
    form_model = 'player'
    form_fields = ['send', 'decision_source', 'decision_reason', 'decision_latency_sec', 'decision_missing']

    @staticmethod
    def is_displayed(player):
        return role_of(player) == 1


class StageBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_first_moves


class SecondMove(Page):
    form_model = 'player'
    form_fields = ['send_back', 'decision_source', 'decision_reason', 'decision_latency_sec', 'decision_missing']

    @staticmethod
    def is_displayed(player):
        return role_of(player) == 2

    @staticmethod
    def error_message(player, values):
        if values['send_back'] is None or values['send_back'] > send_back_max(player):
            return f"Send back between 0 and {send_back_max(player)} points"


class GroupWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    pass


class RoundBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_round_complete


page_sequence = [FirstMove, StageBarrier, SecondMove, GroupWaitPage, Results, RoundBarrier]


def custom_export(players):
    yield ['session_code', 'participant_label', 'agent_id', 'round_number', 'pair_id', 'role',
           'partner_agent_id', 'sent', 'received', 'returned', 'payoff',
           'decision_source', 'decision_missing', 'decision_latency_sec', 'decision_reason']
    for p in players:
        if p.group.field_maybe_none('returned') is None:
            continue
        yield [p.session.code, p.participant.label, p.agent_id, p.round_number, p.group.id_in_subsession,
               role_of(p), p.get_others_in_group()[0].agent_id, p.group.sent, C.MULTIPLIER * p.group.sent,
               p.group.returned, p.payoff, p.field_maybe_none('decision_source'),
               p.field_maybe_none('decision_missing'), p.field_maybe_none('decision_latency_sec'),
               p.field_maybe_none('decision_reason')]
