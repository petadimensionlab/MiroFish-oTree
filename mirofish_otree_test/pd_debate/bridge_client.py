"""
HTTP client for the MiroFish experiment bridge (backend/app/api/experiment.py).

Enabled when MF_BRIDGE_URL is set, e.g. http://127.0.0.1:5001/api/experiment.
Nothing here raises: an uncaught exception in a bot or a WaitPage hook
aborts the whole `otree test` run (phase0-otree.md, finding 4), so every
failure degrades to a default decision flagged as missing.
"""

import json
import os
import time

import requests

BRIDGE_URL = os.environ.get('MF_BRIDGE_URL', '').rstrip('/')
TIMEOUT_SEC = float(os.environ.get('MF_BRIDGE_TIMEOUT', '10'))
MAX_ATTEMPTS = int(os.environ.get('MF_BRIDGE_ATTEMPTS', '3'))
BACKOFF_SEC = float(os.environ.get('MF_BRIDGE_BACKOFF', '0.5'))


def enabled() -> bool:
    return bool(BRIDGE_URL)


def _post(path, payload, attempts=MAX_ATTEMPTS):
    """POST with retry. Returns (data, error, attempts_used)."""
    error = None
    for attempt in range(1, attempts + 1):
        try:
            resp = requests.post(f"{BRIDGE_URL}{path}", json=payload, timeout=TIMEOUT_SEC)
            body = resp.json()
            if resp.status_code == 200 and body.get('success'):
                return body['data'], None, attempt
            error = f"HTTP {resp.status_code}: {body.get('error')}"
            if 400 <= resp.status_code < 500:
                return None, error, attempt  # caller bug, retrying will not help
        except (requests.RequestException, ValueError) as e:
            error = f"{type(e).__name__}: {e}"
        if attempt < attempts:
            time.sleep(BACKOFF_SEC * attempt)
    return None, error, attempts


def net_settings(cfg):
    """Session config bridge_net_<name> keys -> the bridge's net_<name> settings (NOTES #54)."""
    return {k[7:]: v for k, v in cfg.items() if k.startswith('bridge_net_')}


def configure(session_code, **settings):
    data, error, _ = _post('/configure', {'session_code': session_code, **settings})
    return data if error is None else {'error': error}


def decide(session_code, round_number, agent_id, history, default_choice):
    """Returns dict(choice, reason, source, latency_sec, missing, attempts, chat, network_chat)."""
    t0 = time.time()
    data, error, attempts = _post('/decide', {
        'session_code': session_code,
        'round_number': round_number,
        'agent_id': agent_id,
        'history': history,
    })
    latency = round(time.time() - t0, 3)
    if error is None and data.get('choice') in ('A', 'B'):
        return dict(
            choice=data['choice'],
            reason=data.get('reason', ''),
            source=data.get('source', 'bridge'),
            latency_sec=latency,
            missing=bool(data.get('missing', False)),
            attempts=attempts,
            chat=data.get('chat'),
            network_chat=data.get('network_chat'),
        )
    return dict(
        choice=default_choice,
        reason=f"bridge failed: {error or 'invalid choice ' + repr(data)}",
        source='default',
        latency_sec=latency,
        missing=True,
        attempts=attempts,
        chat=None,
        network_chat=None,
    )


def decide_value(session_code, round_number, agent_id, history, parse, default):
    """Games other than the PD. parse(raw choice string) -> typed value or None.

    Returns dict(value, reason, source, latency_sec, missing, attempts).
    """
    t0 = time.time()
    data, error, attempts = _post('/decide', {
        'session_code': session_code,
        'round_number': round_number,
        'agent_id': agent_id,
        'history': history,
    })
    latency = round(time.time() - t0, 3)
    value = None
    if error is None:
        try:
            value = parse(data.get('choice'))
        except (TypeError, ValueError):
            value = None
    if value is not None:
        return dict(value=value, reason=data.get('reason', ''), source=data.get('source', 'bridge'),
                    latency_sec=latency, missing=bool(data.get('missing', False)), attempts=attempts)
    return dict(value=default, reason=f"bridge failed: {error or 'invalid choice ' + repr(data)}",
                source='default', latency_sec=latency, missing=True, attempts=attempts)


def int_parser(lo, hi):
    def parse(raw):
        v = int(raw)
        return v if lo <= v <= hi else None
    return parse


def decide_contribution(session_code, round_number, agent_id, history, endowment, default):
    """Public goods game: returns dict(contribution, reason, source, latency_sec, missing, attempts)."""
    d = decide_value(session_code, round_number, agent_id, history, int_parser(0, endowment), default)
    d['contribution'] = d.pop('value')
    return d


def notify_stage_complete(session_code, round_number, outcomes):
    """Sequential games: all first movers of the round have decided."""
    data, error, _ = _post('/stage_complete', {
        'session_code': session_code,
        'round_number': round_number,
        'outcomes': outcomes,
    })
    return data if error is None else {'error': error}


def notify_round_complete(session_code, round_number, summary):
    data, error, _ = _post('/round_complete', {
        'session_code': session_code,
        'round_number': round_number,
        **summary,
    })
    return data if error is None else {'error': error}


def configure_game(session, game, game_params, agents, num_rounds, barrier_log):
    """/configure for the games other than the PD, from the session config
    (bridge_<name> keys). agents: [{agent_id, group_agent_ids, role}].
    A failure is written to barrier_log; bots then run on defaults (missing)."""
    cfg = session.config
    result = configure(
        session.code,
        agents=agents,
        game=game,
        game_params=game_params,
        policy=cfg.get('bridge_policy', 'random'),
        seed=cfg.get('bridge_seed', 0),
        simulation_id=cfg.get('bridge_simulation_id', ''),
        simulation_dir=cfg.get('bridge_simulation_dir') or os.environ.get('MF_SIMULATION_DIR', ''),
        platform=cfg.get('bridge_platform', 'twitter'),
        include_feed=cfg.get('bridge_include_feed', False),
        num_rounds=num_rounds,
        debate_rounds=cfg.get('bridge_debate_rounds', 0),
        debate_players_only=cfg.get('bridge_debate_players_only', True),
        debate_ignore_hours=cfg.get('bridge_debate_ignore_hours', True),
        debate_min_active=cfg.get('bridge_debate_min_active', 2),
        inject_results=cfg.get('bridge_inject_results', 'none'),
        opening_post=cfg.get('bridge_opening_post', ''),
        repeat_opening=cfg.get('bridge_repeat_opening', False),
        belief_survey=cfg.get('bridge_belief_survey', False),
        belief_statement=cfg.get('bridge_belief_statement'),
        comprehension_check=cfg.get('bridge_comprehension_check', False),
        **net_settings(cfg),
    )
    if 'error' in result:
        with open(barrier_log, 'a') as f:
            f.write(json.dumps(dict(event="configure_failed", error=result['error'])) + "\n")
    return result
