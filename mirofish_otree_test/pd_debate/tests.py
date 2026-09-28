from otree.api import Bot, Submission, expect
from . import Decide, Results, COOPERATE, DEFECT, payoff_matrix, pd_payoff

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
        strategy = STRATEGIES[(self.participant.id_in_session - 1) % len(STRATEGIES)]
        partner_history = [
            p.get_others_in_group()[0].choice for p in self.player.in_previous_rounds()
        ]
        choice = choose(strategy, partner_history)

        yield Submission(
            Decide,
            dict(
                choice=choice,
                decision_source=f"bot_fixed:{strategy}",
                decision_reason="",
                decision_latency_sec=0.0,
                decision_missing=False,
            ),
            check_html=False,  # provenance fields are not rendered for humans
        )

        partner = self.player.get_others_in_group()[0]
        expected = pd_payoff(choice, partner.choice, payoff_matrix(self.session))
        expect(self.player.payoff, expected)
        expect(self.participant.label, f"agent_{self.player.agent_id}")
        yield Results
