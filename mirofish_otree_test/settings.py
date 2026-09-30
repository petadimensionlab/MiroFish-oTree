import json
from os import environ

# Network communication study (MiroFish NOTES #54): every agent talks one to one with graph
# neighbours who are never its PD partner / group member (#51). Same labelling in the control
# (pd_net_off) so the conditions differ only in the network.
NET_COMMON = dict(
    bridge_policy='llm',
    bridge_include_feed=False,
    bridge_inject_results='none',
    bridge_label_unit='session',
    bridge_label_order_per_agent=True,
    bridge_comprehension_check=True,
    bridge_belief_survey=True,
    bridge_net_mean_degree=4,
    bridge_net_contact_mean=1.0,
    bridge_net_contact_dispersion=0.5,
    bridge_net_turns=2,
)
PGG_BELIEF = (
    "When you are in the same group again and again, it is better to contribute to what "
    "benefits everyone than to look out for yourself first."
)

SESSION_CONFIGS = [
    dict(
        name='mf_group',
        app_sequence=['mf_group'],
        num_demo_participants=2,
    ),
    dict(
        name='label_test',
        app_sequence=['label_test'],
        num_demo_participants=3,
    ),
    dict(
        name='pd_debate',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="Iterated PD, 24 fixed pairs x 10 rounds, agents only",
    ),
    dict(
        name='pd_debate_faults',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="pd_debate with bridge fault injection (Phase 2 robustness test)",
        bridge_policy='tft',
        bridge_inject_error_rate=0.3,
    ),
    dict(
        name='pd_debate_llm',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="pd_debate with LLM decisions via the step-server (set MF_SIMULATION_DIR or bridge_simulation_id). Pure baseline: no debate, no result posts",
        bridge_policy='llm',
        bridge_inject_results='none',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
    ),
    dict(
        name='pd_debate_llm_debate',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="LLM decisions with a debate phase between rounds (closed loop, Phase 4)",
        bridge_policy='llm',
        bridge_debate_rounds=2,
        bridge_inject_results='each',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
        bridge_opening_post=(
            "Question for everyone: when you deal with the same person again and again, "
            "is it smarter to trust them or to look out for yourself first? Why?"
        ),
    ),
    dict(
        name='pd_debate_llm_debate_topic',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="pd_debate_llm_debate + topic post repeated before every debate phase + per-agent labels (NOTES #43, #44)",
        bridge_policy='llm',
        bridge_debate_rounds=2,
        bridge_inject_results='each',
        bridge_opening_post=(
            "Question for everyone: when you deal with the same person again and again, "
            "is it smarter to trust them or to look out for yourself first? Why?"
        ),
        bridge_repeat_opening=True,
        bridge_label_unit='agent',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
    ),
    dict(
        name='pd_debate_llm_opening',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="Isolates the opening topic post (NOTES #35): opening post only, no debate rounds, no result posts",
        bridge_policy='llm',
        bridge_debate_rounds=0,
        bridge_inject_results='none',
        bridge_opening_post=(
            "Question for everyone: when you deal with the same person again and again, "
            "is it smarter to trust them or to look out for yourself first? Why?"
        ),
        bridge_belief_survey=True,
    ),
    dict(
        name='pd_debate_llm_debate_noinject',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="Debate rounds between game rounds, no result posts, no opening post (NOTES #35)",
        bridge_policy='llm',
        bridge_debate_rounds=2,
        bridge_inject_results='none',
        bridge_belief_survey=True,
    ),
    dict(
        name='pd_debate_llm_debate_noinject_swap',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="Same as pd_debate_llm_debate_noinject with A/B swapped for agents (NOTES #38: label leak test)",
        bridge_policy='llm',
        bridge_debate_rounds=2,
        bridge_inject_results='none',
        bridge_belief_survey=True,
        bridge_swap_labels=True,
        bridge_label_scheme='letters',
        bridge_label_randomize=False,
    ),
    dict(
        name='pd_debate_llm_chat',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        # NOT for the actual experiments (MiroFish NOTES.md #51): with a direct pair chat the
        # partners settle their choices between themselves, leaving nothing for the platform
        # discourse to affect. Use chat_turns=0 configs (pd_debate_llm_nochat, pd_debate_llm_debate*)
        # for the study; the chat configs are a check / reference condition only.
        doc=("REFERENCE ONLY, not the study condition (NOTES #51). "
             "Pair chat: before every round the two partners exchange private messages about the game "
             "(cheap talk, not binding), then decide. No debate rounds, no feed, no result posts. "
             "Labels shared within a pair, random across pairs"),
        bridge_policy='llm',
        bridge_chat_turns=4,
        bridge_include_feed=False,
        bridge_inject_results='none',
        bridge_label_unit='pair',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
    ),
    dict(
        name='pd_debate_llm_chat_debate',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="REFERENCE ONLY, not the study condition (NOTES #51). pd_debate_llm_chat + debate rounds with the repeated topic post and result posts (points only) on the platform",
        bridge_policy='llm',
        bridge_chat_turns=4,
        bridge_debate_rounds=2,
        bridge_inject_results='each',
        bridge_opening_post=(
            "Question for everyone: when you deal with the same person again and again, "
            "is it smarter to trust them or to look out for yourself first? Why?"
        ),
        bridge_repeat_opening=True,
        bridge_label_unit='pair',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
    ),
    dict(
        name='pd_debate_llm_nochat',
        app_sequence=['pd_debate'],
        num_demo_participants=48,
        doc="Control for pd_debate_llm_chat: same settings with chat_turns=0",
        bridge_policy='llm',
        bridge_chat_turns=0,
        bridge_include_feed=False,
        bridge_inject_results='none',
        bridge_label_unit='pair',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
    ),
    dict(
        name='pgg',
        app_sequence=['pgg'],
        num_demo_participants=16,
        doc="Public goods game, fixed groups of 4 x 10 rounds, endowment 20, multiplier 1.6 (MPCR 0.4); fixed-strategy bots, no bridge",
    ),
    dict(
        name='pgg_llm',
        app_sequence=['pgg'],
        num_demo_participants=16,
        doc=("Public goods game with LLM decisions via the step-server (MF_SIMULATION_DIR). "
             "No chat, no debate, no feed, no result posts (NOTES #51, #52)"),
        bridge_policy='llm',
        bridge_include_feed=False,
        bridge_inject_results='none',
        bridge_comprehension_check=True,
        bridge_belief_survey=True,
        bridge_belief_statement=(
            "When you are in the same group again and again, it is better to contribute to what "
            "benefits everyone than to look out for yourself first."
        ),
    ),
    dict(
        name='beauty',
        app_sequence=['beauty'],
        num_demo_participants=16,
        doc="p-beauty contest, fixed groups of 4 x 10 rounds, guess 0-100, target 2/3 of the mean, prize 20; fixed-strategy bots",
    ),
    dict(
        name='beauty_llm',
        app_sequence=['beauty'],
        num_demo_participants=16,
        doc="p-beauty contest with LLM decisions (no chat, no debate, no feed, no result posts)",
        bridge_policy='llm',
        bridge_include_feed=False,
        bridge_inject_results='none',
        bridge_comprehension_check=True,
    ),
    dict(
        name='trust',
        app_sequence=['trust'],
        num_demo_participants=16,
        doc="Trust (investment) game, fixed pairs and roles x 10 rounds, endowment 10, multiplier 3; fixed-strategy bots",
    ),
    dict(
        name='trust_llm',
        app_sequence=['trust'],
        num_demo_participants=16,
        doc="Trust game with LLM decisions (no chat, no debate, no feed, no result posts)",
        bridge_policy='llm',
        bridge_include_feed=False,
        bridge_inject_results='none',
        bridge_comprehension_check=True,
    ),
    dict(
        name='ultimatum',
        app_sequence=['ultimatum'],
        num_demo_participants=16,
        doc="Ultimatum game, fixed pairs and roles x 10 rounds, pie 20; fixed-strategy bots",
    ),
    dict(
        name='ultimatum_llm',
        app_sequence=['ultimatum'],
        num_demo_participants=16,
        doc="Ultimatum game with LLM decisions (no chat, no debate, no feed, no result posts)",
        bridge_policy='llm',
        bridge_include_feed=False,
        bridge_inject_results='none',
        bridge_comprehension_check=True,
    ),
    dict(
        name='pd_net_off',
        app_sequence=['pd_debate'],
        num_demo_participants=16,
        doc="Control for pd_net_*: same labelling (session symbols, per-agent listing order), no network talk. Study condition: partners never talk (NOTES #51, #54)",
        **{**NET_COMMON, 'bridge_net_topology': 'none'},
    ),
    *[
        dict(
            name=f'pd_net_{topo}',
            app_sequence=['pd_debate'],
            num_demo_participants=16,
            doc=(f"Network talk, topology {topo}: one-to-one conversations with neighbours, contact rate "
                 "gamma-Poisson (mean 1, dispersion 0.5). Study condition: partners never talk (NOTES #51, #54)"),
            **{**NET_COMMON, 'bridge_net_topology': topo},
        )
        for topo in ('er', 'ba', 'ws', 'ring')
    ],
    dict(
        name='pgg_net_off',
        app_sequence=['pgg'],
        num_demo_participants=16,
        doc="Control for pgg_net_*: public goods game, no network talk (NOTES #54)",
        bridge_belief_statement=PGG_BELIEF,
        **{**NET_COMMON, 'bridge_net_topology': 'none'},
    ),
    *[
        dict(
            name=f'pgg_net_{topo}',
            app_sequence=['pgg'],
            num_demo_participants=16,
            doc=(f"Public goods game with network talk, topology {topo}: conversations only with people "
                 "outside one's own group (NOTES #51, #54)"),
            bridge_belief_statement=PGG_BELIEF,
            **{**NET_COMMON, 'bridge_net_topology': topo},
        )
        for topo in ('ba', 'er')
    ],
    dict(
        name='live_test',
        app_sequence=['live_test'],
        num_demo_participants=2,
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc="",
    # Seating order: which MiroFish agent sits in which participant slot (pairs /
    # groups are consecutive), e.g. personas_meta.json "agent_order" of
    # make_workplace_sim.py. Unset: participant i is agent i-1.
    agent_ids=json.loads(environ['MF_AGENT_IDS']) if environ.get('MF_AGENT_IDS') else None,
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'USD'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = environ.get("OTREE_SECRET_KEY", "dev-only-not-secret")
