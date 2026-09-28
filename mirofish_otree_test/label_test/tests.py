from otree.api import Bot
from . import Intro


class PlayerBot(Bot):
    def play_round(self):
        yield Intro
