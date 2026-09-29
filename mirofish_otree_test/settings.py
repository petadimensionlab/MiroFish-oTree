from os import environ

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
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
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
