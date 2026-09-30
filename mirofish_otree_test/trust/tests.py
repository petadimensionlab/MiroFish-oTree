from otree.api import Bot, Submission, expect
from . import FirstMove, SecondMove, Results, C, role_of, send_back_max
from pd_debate import bridge_client


def history_of(player):
    return [dict(round_number=p.round_number, sent=p.group.sent, returned=p.group.returned, payoff=float(p.payoff))
            for p in player.in_previous_rounds()]


class PlayerBot(Bot):
    def play_round(self):
        first = role_of(self.player) == 1
        page, field = (FirstMove, 'send') if first else (SecondMove, 'send_back')
        hi = C.ENDOWMENT if first else send_back_max(self.player)
        if bridge_client.enabled():
            d = bridge_client.decide_value(self.session.code, self.round_number, self.player.agent_id,
                                           history_of(self.player), bridge_client.int_parser(0, hi),
                                           default=hi // 2)
            fields = {field: d['value'], 'decision_source': d['source'], 'decision_reason': d['reason'],
                      'decision_latency_sec': d['latency_sec'], 'decision_missing': d['missing']}
        else:
            # without a bridge: send 5, return a third
            fields = {field: 5 if first else hi // 3, 'decision_source': 'bot_fixed', 'decision_reason': '',
                      'decision_latency_sec': 0.0, 'decision_missing': False}
        yield Submission(page, fields, check_html=False)
        if not bridge_client.enabled():
            expect(self.player.payoff, C.ENDOWMENT - 5 + 5 if first else C.ENDOWMENT + 15 - 5)
        yield Results
