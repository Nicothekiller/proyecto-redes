from __future__ import annotations

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from client.config import PROBE_TIMEOUT_S

RTT_RE = re.compile(r"time=([\d.]+) ms")


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    rtt_ms: float | None = None


def probe(overlay_ip: str) -> ProbeResult:
    result = subprocess.run(
        ["ping", "-c", "1", "-W", str(PROBE_TIMEOUT_S), overlay_ip],
        capture_output=True,
        text=True,
        check=False,
    )
    match = RTT_RE.search(result.stdout)
    if result.returncode != 0 or match is None:
        return ProbeResult(ok=False)
    return ProbeResult(ok=True, rtt_ms=float(match.group(1)))


def probe_all(overlay_ips: list[str]) -> dict[str, ProbeResult]:
    if not overlay_ips:
        return {}
    with ThreadPoolExecutor(max_workers=len(overlay_ips)) as pool:
        return dict(zip(overlay_ips, pool.map(probe, overlay_ips), strict=True))
