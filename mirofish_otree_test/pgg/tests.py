import json

from otree.api import Bot, Submission, expect
from . import Contribute, Results, C, pgg_points
from pd_debate import bridge_client

# Fixed strategies by id_in_group when no bridge: full, zero, conditional, half
STRATEGIES = ['full', 'zero', 'conditional', 'half']


def choose(strategy, others_last):
    if strategy == 'full':
        return C.ENDOWMENT
    if strategy == 'zero':
        return 0
    if strategy == 'half':
        return C.ENDOWMENT // 2
    if strategy == 'conditional':
        return round(sum(others_last) / len(others_last)) if others_last else C.ENDOWMENT
    raise ValueError(strategy)


class PlayerBot(Bot):
    def play_round(self):
        previous = self.player.in_previous_rounds()
        if bridge_client.enabled():
            history = [
                dict(round_number=p.round_number, own=p.contribution,
                     others=[q.contribution for q in p.get_others_in_group()],
                     total=p.group.total_contribution, payoff=p.earnings)
                for p in previous
            ]
            d = bridge_client.decide_contribution(
                self.session.code, self.round_number, self.player.agent_id, history,
                endowment=C.ENDOWMENT, default=C.ENDOWMENT // 2)
            fields = dict(contribution=d['contribution'], decision_source=d['source'],
                          decision_reason=d['reason'], decision_latency_sec=d['latency_sec'],
                          decision_missing=d['missing'])
        else:
            strategy = STRATEGIES[(self.player.id_in_group - 1) % len(STRATEGIES)]
            others_last = [q.contribution for q in previous[-1].get_others_in_group()] if previous else []
            fields = dict(contribution=choose(strategy, others_last), decision_source=f"bot_fixed:{strategy}",
                          decision_reason="", decision_latency_sec=0.0, decision_missing=False)
        yield Submission(Contribute, fields, check_html=False)
        expect(self.player.earnings, pgg_points(self.player.contribution, self.group.total_contribution, self.session))
        yield Results
