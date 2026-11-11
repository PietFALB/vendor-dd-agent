"""HTTP GET with retries for temporary failures only."""
import time

import requests

RETRY_STATUS = {429, 500, 502, 503, 504}
ATTEMPTS = 3


def get_with_retry(url: str, **kwargs) -> requests.Response:
    """GET with up to 3 attempts on connection errors, timeouts, 429 and 5xx.
    Other responses (200, 401, 404, ...) are returned at once: retrying won't change them."""
    kwargs.setdefault("timeout", 15)
    last_error = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            r = requests.get(url, **kwargs)
            if r.status_code not in RETRY_STATUS or attempt == ATTEMPTS:
                return r
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt == ATTEMPTS:
                raise
        time.sleep(attempt)  # 1s, then 2s
    raise last_error  # not reached in practice
