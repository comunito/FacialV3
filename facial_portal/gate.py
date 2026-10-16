from __future__ import annotations

import requests

from .config import GateConfig


class Gate:
    def __init__(self, config: GateConfig):
        self.config = config

    def pulse(self, reason: str) -> tuple[bool, str]:
        if not self.config.enabled or not self.config.allow_physical:
            return False, "dry-run: physical gate disabled"
        if self.config.mode != "http" or not self.config.url:
            return False, "gate is not configured"
        headers = {"Authorization": f"Bearer {self.config.token}"} if self.config.token else {}
        response = requests.post(self.config.url.rstrip("/") + "/pulse", json={"reason": reason, "pulse_ms": self.config.pulse_ms}, headers=headers, timeout=5)
        response.raise_for_status()
        return True, "pulse sent"
