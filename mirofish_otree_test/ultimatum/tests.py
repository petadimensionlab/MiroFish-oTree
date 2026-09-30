from otree.api import Bot, Submission, expect
from . import Propose, Respond, Results, C, role_of
from pd_debate import bridge_client


def parse_response(raw):
    return raw if raw in ('accept', 'reject') else None


class PlayerBot(Bot):
    def play_round(self):
        first = role_of(self.player) == 1
        if bridge_client.enabled():
            parse = bridge_client.int_parser(0, C.PIE) if first else parse_response
            d = bridge_client.decide_value(self.session.code, self.round_number, self.player.agent_id, [],
                                           parse, default=C.PIE // 2 if first else 'accept')
            value = d['value']
            prov = dict(decision_source=d['source'], decision_reason=d['reason'],
                        decision_latency_sec=d['latency_sec'], decision_missing=d['missing'])
        else:
            # without a bridge: offer 4 in odd rounds (rejected: < 5), 8 in even rounds (accepted)
            value = (4 if self.round_number % 2 else 8) if first else (
                'accept' if self.group.offer >= 5 else 'reject')
            prov = dict(decision_source='bot_fixed', decision_reason='', decision_latency_sec=0.0,
                        decision_missing=False)
        if first:
            yield Submission(Propose, dict(offer=value, **prov), check_html=False)
        else:
            yield Submission(Respond, dict(response=value, **prov), check_html=False)
        if not bridge_client.enabled():
            expect(self.group.accepted, self.round_number % 2 == 0)
        yield Results
