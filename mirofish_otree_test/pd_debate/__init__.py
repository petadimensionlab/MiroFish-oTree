import json
import os
import time
from pathlib import Path

from otree.api import *

from . import bridge_client

doc = """
Iterated prisoner's dilemma for MiroFish agents (Phase 1).

Fixed 2-player pairs for NUM_ROUNDS rounds. Choices are shown with neutral
labels (A / B) to reduce training-data contamination; A = cooperate.
Between rounds, a subsession-wide barrier (DebateBarrier) marks where the
MiroFish debate phase will run (Phase 4). Agents only - no human pages.
"""

# Barrier events for tests / the future bridge hook
BARRIER_LOG = Path(__file__).parent / "barrier_log.jsonl"

COOPERATE = 'A'
DEFECT = 'B'


class C(BaseConstants):
    NAME_IN_URL = 'pd_debate'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
    # Defaults; override per session via session config key 'pd_payoffs'
    DEFAULT_PAYOFFS = dict(R=30, T=50, S=0, P=10)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    both_cooperated = models.BooleanField()


class Player(BasePlayer):
    agent_id = models.IntegerField()
    choice = models.StringField(
        choices=[[COOPERATE, 'Option A'], [DEFECT, 'Option B']],
        widget=widgets.RadioSelect,
        label="Which option do you choose?",
    )
    # Decision provenance, filled by the bot / bridge (Phase 2+)
    decision_source = models.StringField(blank=True)
    decision_reason = models.LongStringField(blank=True)
    decision_latency_sec = models.FloatField(blank=True)
    decision_missing = models.BooleanField(initial=False, blank=True)


# Must be a module-level function: as a Subsession method oTree 6 silently
# ignores it (docs/otree-integration/phase0-otree.md, finding 5).
def creating_session(subsession: Subsession):
    agent_ids = subsession.session.config.get('agent_ids')
    for player in subsession.get_players():
        idx = player.participant.id_in_session - 1
        agent_id = agent_ids[idx] if agent_ids else idx
        player.agent_id = agent_id
        if subsession.round_number == 1:
            player.participant.label = f"agent_{agent_id}"

    if subsession.round_number == 1 and bridge_client.enabled():
        cfg = subsession.session.config
        agents = []
        for group in subsession.get_groups():
            p1, p2 = group.get_players()
            agents.append(dict(agent_id=p1.agent_id, partner_agent_id=p2.agent_id))
            agents.append(dict(agent_id=p2.agent_id, partner_agent_id=p1.agent_id))
        result = bridge_client.configure(
            subsession.session.code,
            agents=agents,
            policy=cfg.get('bridge_policy', 'random'),
            seed=cfg.get('bridge_seed', 0),
            inject_delay_sec=cfg.get('bridge_inject_delay_sec', 0.0),
            inject_error_rate=cfg.get('bridge_inject_error_rate', 0.0),
            simulation_id=cfg.get('bridge_simulation_id', ''),
            simulation_dir=cfg.get('bridge_simulation_dir') or os.environ.get('MF_SIMULATION_DIR', ''),
            platform=cfg.get('bridge_platform', 'twitter'),
            include_feed=cfg.get('bridge_include_feed', True),
            feed_exclude_own=cfg.get('bridge_feed_exclude_own', False),
            num_rounds=C.NUM_ROUNDS,
            default_choice=cfg.get('bridge_default_choice', COOPERATE),
            swap_labels=cfg.get('bridge_swap_labels', False),
            payoffs=payoff_matrix(subsession.session),
            debate_rounds=cfg.get('bridge_debate_rounds', 0),
            debate_players_only=cfg.get('bridge_debate_players_only', True),
            debate_ignore_hours=cfg.get('bridge_debate_ignore_hours', True),
            debate_min_active=cfg.get('bridge_debate_min_active', 2),
            inject_results=cfg.get('bridge_inject_results', 'each'),
            announcer_agent_id=cfg.get('bridge_announcer_agent_id', -1),
            opening_post=cfg.get('bridge_opening_post', ''),
            opening_agent_id=cfg.get('bridge_opening_agent_id', -1),
            repeat_opening=cfg.get('bridge_repeat_opening', False),
            belief_survey=cfg.get('bridge_belief_survey', False),
            comprehension_check=cfg.get('bridge_comprehension_check', False),
        )
        if 'error' in result:
            # Bots still run (every decision falls back to the default), but
            # make the misconfiguration visible in the barrier log.
            with BARRIER_LOG.open("a") as f:
                f.write(json.dumps(dict(event="configure_failed", error=result['error'])) + "\n")


def payoff_matrix(session):
    return session.config.get('pd_payoffs', C.DEFAULT_PAYOFFS)


def pd_payoff(own: str, other: str, m: dict) -> int:
    if own == COOPERATE:
        return m['R'] if other == COOPERATE else m['S']
    return m['T'] if other == COOPERATE else m['P']


def set_payoffs(group: Group):
    p1, p2 = group.get_players()
    m = payoff_matrix(group.session)
    p1.payoff = pd_payoff(p1.choice, p2.choice, m)
    p2.payoff = pd_payoff(p2.choice, p1.choice, m)
    group.both_cooperated = p1.choice == COOPERATE and p2.choice == COOPERATE


def on_round_complete(subsession: Subsession):
    """All pairs have submitted this round. Phase 4 triggers the debate here."""
    players = subsession.get_players()
    record = dict(
        event="round_complete",
        session_code=subsession.session.code,
        round_number=subsession.round_number,
        n_players=len(players),
        cooperation_rate=sum(p.choice == COOPERATE for p in players) / len(players),
        timestamp=time.time(),
    )
    if bridge_client.enabled():
        record['bridge'] = bridge_client.notify_round_complete(
            subsession.session.code, subsession.round_number,
            dict(
                n_players=record['n_players'],
                cooperation_rate=record['cooperation_rate'],
                outcomes=[
                    dict(agent_id=p.agent_id, choice=p.choice, payoff=float(p.payoff),
                         partner_agent_id=p.get_others_in_group()[0].agent_id,
                         source=p.field_maybe_none('decision_source'),
                         missing=p.field_maybe_none('decision_missing'))
                    for p in players
                ],
            ),
        )
    with BARRIER_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")


# PAGES
class Decide(Page):
    form_model = 'player'
    form_fields = [
        'choice',
        'decision_source',
        'decision_reason',
        'decision_latency_sec',
        'decision_missing',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(m=payoff_matrix(player.session))


class PairWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return dict(partner=player.get_others_in_group()[0])


class DebateBarrier(WaitPage):
    wait_for_all_groups = True
    after_all_players_arrive = on_round_complete


page_sequence = [Decide, PairWaitPage, Results, DebateBarrier]


def custom_export(players):
    yield [
        'session_code', 'participant_code', 'participant_label', 'agent_id',
        'round_number', 'pair_id', 'id_in_pair', 'partner_agent_id',
        'choice', 'cooperated', 'partner_choice', 'payoff',
        'decision_source', 'decision_missing', 'decision_latency_sec', 'decision_reason',
    ]
    for p in players:
        if p.field_maybe_none('choice') is None:
            continue
        partner = p.get_others_in_group()[0]
        yield [
            p.session.code, p.participant.code, p.participant.label, p.agent_id,
            p.round_number, p.group.id_in_subsession, p.id_in_group, partner.agent_id,
            p.choice, int(p.choice == COOPERATE), partner.field_maybe_none('choice'),
            p.payoff,
            p.field_maybe_none('decision_source'), p.field_maybe_none('decision_missing'),
            p.field_maybe_none('decision_latency_sec'), p.field_maybe_none('decision_reason'),
        ]
