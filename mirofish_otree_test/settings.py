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
