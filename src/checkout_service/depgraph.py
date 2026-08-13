"""Runtime service-dependency discovery.

The project originally read its call graph from a hand-authored `topology.json`. That
contradicts the premise the literature review is built on — Winchester et al. (2024) show
runtime topologies deviate substantially from any static view — so the graph is instead
observed here: every outbound call a service makes is counted and published, and the edge
set E_t is reconstructed from those counts over a time window.

Implementation notes:
  * `install()` patches requests.Session.request, which is the single chokepoint every
    `requests.get/post/delete(...)` call funnels through, so no call sites need editing.
  * Counts are cumulative, matching Prometheus counter semantics, so a window's edge
    weight is `increase(service_dependency_calls_total[window])`.
  * Metrics go to the Pushgateway already deployed for the traffic generator. Each service
    pushes under its own grouping key so services don't overwrite one another.
  * Nothing here may raise into the request path — a telemetry failure must never take
    down the service it is observing.
"""
import collections
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

SERVICE_NAME = os.getenv("SERVICE_NAME", "unknown")
PUSHGATEWAY_URL = os.getenv(
    "PUSHGATEWAY_URL",
    "http://prometheus-prometheus-pushgateway.monitoring.svc.cluster.local:9091",
)
PUSH_INTERVAL_SECONDS = int(os.getenv("DEPGRAPH_PUSH_INTERVAL", "10"))

_counts = collections.Counter()
_lock = threading.Lock()


def _classify(url):
    """Map an outbound URL to the canonical name of the service it addresses.

    Returns None for anything that isn't a recognised in-cluster peer (localhost
    fallbacks, the Pushgateway itself), so those never become spurious edges.
    """
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except Exception:
        return None
    if not host:
        return None
    # Kubernetes DNS gives either "stylehub-cart-service" or the FQDN form
    # "stylehub-cart-service.default.svc.cluster.local"; both reduce to the first label.
    name = host.split(".")[0]
    if name.startswith("stylehub-"):
        return name
    if name in ("redis", "stylehub-redis"):
        return "stylehub-redis"
    return None


def record(target):
    """Record one observed call to `target` (a canonical service name)."""
    if not target:
        return
    with _lock:
        _counts[target] += 1


def _render():
    with _lock:
        snapshot = dict(_counts)
    lines = [
        "# TYPE service_dependency_calls_total counter",
        "# HELP service_dependency_calls_total Outbound calls observed from source to target.",
    ]
    for target, n in sorted(snapshot.items()):
        lines.append(
            f'service_dependency_calls_total{{source="{SERVICE_NAME}",target="{target}"}} {n}'
        )
    return "\n".join(lines) + "\n"


def _push_once():
    body = _render().encode()
    url = f"{PUSHGATEWAY_URL}/metrics/job/depgraph/instance/{urllib.parse.quote(SERVICE_NAME)}"
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "text/plain")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status


def _push_loop():
    while True:
        time.sleep(PUSH_INTERVAL_SECONDS)
        try:
            _push_once()
        except Exception:
            # Deliberately swallowed: the observed service must survive an unreachable
            # Pushgateway. Counts keep accumulating and the next push catches up.
            pass


def install():
    """Patch `requests` so every outbound call is counted, then start pushing."""
    try:
        import requests

        original = requests.Session.request

        def instrumented(self, method, url, *args, **kwargs):
            try:
                record(_classify(url))
            except Exception:
                pass
            return original(self, method, url, *args, **kwargs)

        requests.Session.request = instrumented
    except Exception:
        pass

    threading.Thread(target=_push_loop, daemon=True).start()
