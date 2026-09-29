"""
HTTP client for the MiroFish experiment bridge (backend/app/api/experiment.py).

Enabled when MF_BRIDGE_URL is set, e.g. http://127.0.0.1:5001/api/experiment.
Nothing here raises: an uncaught exception in a bot or a WaitPage hook
aborts the whole `otree test` run (phase0-otree.md, finding 4), so every
failure degrades to a default decision flagged as missing.
"""

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


def configure(session_code, **settings):
    data, error, _ = _post('/configure', {'session_code': session_code, **settings})
    return data if error is None else {'error': error}


def decide(session_code, round_number, agent_id, history, default_choice):
    """Returns dict(choice, reason, source, latency_sec, missing, attempts, chat)."""
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
        )
    return dict(
        choice=default_choice,
        reason=f"bridge failed: {error or 'invalid choice ' + repr(data)}",
        source='default',
        latency_sec=latency,
        missing=True,
        attempts=attempts,
        chat=None,
    )


def notify_round_complete(session_code, round_number, summary):
    data, error, _ = _post('/round_complete', {
        'session_code': session_code,
        'round_number': round_number,
        **summary,
    })
    return data if error is None else {'error': error}
