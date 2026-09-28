from otree.api import *

doc = """
MiroFish Phase 0 test app: has a live_method page, to determine whether
the headless bot runner (otree test) exercises live_method at all.
"""


class C(BaseConstants):
    NAME_IN_URL = 'live_test'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    live_method_called = models.BooleanField(initial=False)
    got_value = models.IntegerField(blank=True)
    asyncgen_live_method_called = models.BooleanField(initial=False)
    asyncdef_live_method_attempted = models.BooleanField(initial=False)


class LivePage(Page):
    @staticmethod
    def live_method(player: Player, data):
        # If the bot runner ever calls this, it will flip live_method_called
        # to True and we can see it in the exported CSV / DB.
        player.live_method_called = True
        player.got_value = data.get('value') if isinstance(data, dict) else None
        return {player.id_in_group: dict(echo=data)}


class AsyncGenLivePage(Page):
    @staticmethod
    async def live_method(player: Player, data):
        # Item 4: does oTree 6.0.15 support `async def` live_method as an
        # async *generator* (async def + yield, which is the documented
        # supported async form per otree/live.py's
        # ASYNC_OR_YIELD_ISSUE_MSG)?
        player.asyncgen_live_method_called = True
        yield {player.id_in_group: dict(echo=data)}


class AsyncDefLivePage(Page):
    @staticmethod
    async def live_method(player: Player, data):
        # Item 4 (negative case): a plain `async def` WITHOUT yield (a
        # coroutine function, not an async generator). otree/live.py
        # explicitly rejects this with LiveMethodBadReturnValue at
        # call_live_method_compat's `elif inspect.iscoroutinefunction(...)`
        # branch. We expect this to raise, not to run cleanly.
        player.asyncdef_live_method_attempted = True
        return {player.id_in_group: dict(echo=data)}


page_sequence = [LivePage, AsyncGenLivePage, AsyncDefLivePage]
