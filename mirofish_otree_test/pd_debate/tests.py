from otree.api import Bot, Submission, expect
from . import Decide, Results, COOPERATE, DEFECT, payoff_matrix, pd_payoff, bridge_client

# Fixed strategies, assigned by participant.id_in_session so each pair gets
# a known matchup: (1,2) = tft vs alld, (3,4) = allc vs grim, then repeat.
STRATEGIES = ['tft', 'alld', 'allc', 'grim']


def choose(strategy, partner_history):
    if strategy == 'allc':
        return COOPERATE
    if strategy == 'alld':
        return DEFECT
    if strategy == 'tft':
        return partner_history[-1] if partner_history else COOPERATE
    if strategy == 'grim':
        return DEFECT if DEFECT in partner_history else COOPERATE
    raise ValueError(strategy)


class PlayerBot(Bot):
    def play_round(self):
        previous = self.player.in_previous_rounds()
        partner_history = [p.get_others_in_group()[0].choice for p in previous]

        if bridge_client.enabled():
            history = [
                dict(round_number=p.round_number, own=p.choice,
                     partner=p.get_others_in_group()[0].choice, payoff=float(p.payoff))
                for p in previous
            ]
            d = bridge_client.decide(
                self.session.code, self.round_number, self.player.agent_id, history,
                default_choice=self.session.config.get('bridge_default_choice', COOPERATE),
            )
            fields = dict(
                choice=d['choice'], decision_source=d['source'], decision_reason=d['reason'],
                decision_latency_sec=d['latency_sec'], decision_missing=d['missing'],
            )
        else:
            strategy = STRATEGIES[(self.participant.id_in_session - 1) % len(STRATEGIES)]
            fields = dict(
                choice=choose(strategy, partner_history),
                decision_source=f"bot_fixed:{strategy}",
                decision_reason="",
                decision_latency_sec=0.0,
                decision_missing=False,
            )
        choice = fields['choice']

        # provenance fields are not rendered for humans
        yield Submission(Decide, fields, check_html=False)

        partner = self.player.get_others_in_group()[0]
        expected = pd_payoff(choice, partner.choice, payoff_matrix(self.session))
        expect(self.player.payoff, expected)
        expect(self.participant.label, f"agent_{self.player.agent_id}")
        yield Results
