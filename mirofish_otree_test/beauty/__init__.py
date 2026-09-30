import json
import time
from pathlib import Path

from otree.api import *

from pd_debate import bridge_client

doc = """
p-beauty contest (guessing game, Nagel 1995) for MiroFish agents.

Fixed groups of 4 for NUM_ROUNDS rounds. Each member picks a whole number
0..MAX_GUESS; the target is P x the group average; the member closest to the
target gets PRIZE points (split on ties), the others 0. Iterated deletion of
dominated strategies leaves 0: the unique equilibrium is everyone picking 0.
Humans start around 35 and move toward 0 over rounds.
"""

BARRIER_LOG = Path(__file__).parent / "barrier_log.jsonl"


class C(BaseConstants):
    NAME_IN_URL = 'beauty'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS = 10
    MAX_GUESS = 100
    P = 2 / 3
    P_TEXT = 'two thirds'
    PRIZE = 20


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    mean_guess = models.FloatField()
    target = models.FloatField()


class Player(BasePlayer):
    agent_id = models.IntegerField()
    guess = models.IntegerField(min=0, max=C.MAX_GUESS, label="Your number")
    is_winner = models.BooleanField()
    earnings = models.FloatField()
    decision_source = models.StringField(blank=True)
    decision_reason = models.LongStringField(blank=True)
    decision_latency_sec = models.FloatField(blank=True)
    decision_missing = models.BooleanField(initial=False, blank=True)


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
            subsession.session, 'beauty',
            dict(p=C.P, p_text=C.P_TEXT, max_guess=C.MAX_GUESS, prize=C.PRIZE, group_size=C.PLAYERS_PER_GROUP),
            agents, C.NUM_ROUNDS, BARRIER_LOG)


def set_payoffs(group: Group):
    players = group.get_players()
    group.mean_guess = sum(p.guess for p in players) / len(players)
    group.target = C.P * group.mean_guess
    best = min(abs(p.guess - group.target) for p in players)
    winners = [p for p in players if abs(abs(p.guess - group.target) - best) < 1e-9]
    for p in players:
        p.is_winner = p in winners
        p.earnings = C.PRIZE / len(winners) if p.is_winner else 0.0
        p.payoff = p.earnings


def on_round_complete(subsession: Subsession):
    players = subsession.get_players()
    record = dict(event="round_complete", session_code=subsession.session.code,
                  round_number=subsession.round_number, n_players=len(players),
                  mean_guess=sum(p.guess for p in players) / len(players), timestamp=time.time())
    if bridge_client.enabled():
        record['bridge'] = bridge_client.notify_round_complete(
            subsession.session.code, subsession.round_number,
            dict(n_players=record['n_players'], mean_guess=record['mean_guess'], outcomes=[
                dict(agent_id=p.agent_id, choice=str(p.guess), payoff=p.earnings,
                     target=p.group.target, source=p.field_maybe_none('decision_source'),
                     missing=p.field_maybe_none('decision_missing'))
                for p in players]))
    with BARRIER_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


class Guess(Page):
    form_model = 'player'
    form_fields = ['guess', 'decision_source', 'decision_reason', 'decision_latency_sec', 'decision_missing']


class GroupWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    pass


class RoundBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_round_complete


page_sequence = [Guess, GroupWaitPage, Results, RoundBarrier]


def custom_export(players):
    yield ['session_code', 'participant_label', 'agent_id', 'round_number', 'group_id', 'guess',
           'others_guesses', 'mean_guess', 'target', 'is_winner', 'earnings',
           'decision_source', 'decision_missing', 'decision_latency_sec', 'decision_reason']
    for p in players:
        if p.field_maybe_none('guess') is None:
            continue
        yield [p.session.code, p.participant.label, p.agent_id, p.round_number, p.group.id_in_subsession,
               p.guess, json.dumps([q.field_maybe_none('guess') for q in p.get_others_in_group()]),
               p.group.field_maybe_none('mean_guess'), p.group.field_maybe_none('target'),
               p.field_maybe_none('is_winner'), p.field_maybe_none('earnings'),
               p.field_maybe_none('decision_source'), p.field_maybe_none('decision_missing'),
               p.field_maybe_none('decision_latency_sec'), p.field_maybe_none('decision_reason')]
