import sys

from otree.api import Bot
from . import LivePage, AsyncGenLivePage, AsyncDefLivePage


class PlayerBot(Bot):
    def play_round(self):
        yield LivePage
        yield AsyncGenLivePage
        yield AsyncDefLivePage


def call_live_method(method, *, page_class, group, **kwargs):
    # Explicit hook: this is what makes `otree test` exercise live_method at
    # all. Without this function defined in tests.py, live_method is never
    # invoked by the CLI bot runner even though the bot yields the live page.
    #
    # `method(id_in_group, data)` returns an async generator regardless of
    # whether live_method itself is sync, an async generator, or a plain
    # coroutine function -- it's always wrapped by
    # otree.live.call_live_method_compat. It must be driven with asyncio,
    # otherwise the underlying live_method body never executes.
    import asyncio

    async def drive():
        for player in group.get_players():
            async for _ in method(player.id_in_group, {"value": 99}):
                pass

    if page_class.__name__ == 'AsyncDefLivePage':
        # Item 4 negative case: plain `async def` (coroutine, no yield)
        # live_method. Expected to raise LiveMethodBadReturnValue.
        try:
            asyncio.run(drive())
            print("DEBUG AsyncDefLivePage: no exception raised", file=sys.stderr)
        except Exception as exc:
            print(f"DEBUG AsyncDefLivePage raised: {exc!r}", file=sys.stderr)
    else:
        asyncio.run(drive())
