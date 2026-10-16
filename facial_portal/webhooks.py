from __future__ import annotations

import requests


def send(urls: list[str], payload: dict) -> list[str]:
    errors = []
    for url in urls:
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc.__class__.__name__}")
    return errors
