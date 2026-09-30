from otree.api import Bot, Submission, expect
from . import Guess, Results, C
from pd_debate import bridge_client

# Without a bridge: level-0 (50), level-1 (33), level-2 (22), and 0
FIXED = [50, 33, 22, 0]


class PlayerBot(Bot):
    def play_round(self):
        if bridge_client.enabled():
            history = [dict(round_number=p.round_number, own=p.guess,
                            others=[q.guess for q in p.get_others_in_group()],
                            target=p.group.target, payoff=p.earnings)
                       for p in self.player.in_previous_rounds()]
            d = bridge_client.decide_value(self.session.code, self.round_number, self.player.agent_id, history,
                                           bridge_client.int_parser(0, C.MAX_GUESS), default=C.MAX_GUESS // 2)
            fields = dict(guess=d['value'], decision_source=d['source'], decision_reason=d['reason'],
                          decision_latency_sec=d['latency_sec'], decision_missing=d['missing'])
        else:
            fields = dict(guess=FIXED[(self.player.id_in_group - 1) % len(FIXED)], decision_source='bot_fixed',
                          decision_reason='', decision_latency_sec=0.0, decision_missing=False)
        yield Submission(Guess, fields, check_html=False)
        if not bridge_client.enabled():
            # target = 2/3 * 26.25 = 17.5 -> 22 is closest
            expect(self.player.is_winner, self.player.guess == 22)
        yield Results
