"""Prometheus metrics (exposed at /metrics)."""

from prometheus_client import REGISTRY, Counter, Gauge, Histogram

labs_running = Gauge(
    "netlab_labs_running", "Lab sessions currently deployed"
)
lab_boot_seconds = Histogram(
    "netlab_lab_boot_seconds",
    "Seconds from deploy request to all nodes ready",
    ["driver"],
    buckets=(5, 15, 30, 60, 120, 300, 600, 900),
)
console_latency_seconds = Histogram(
    "netlab_console_latency_seconds",
    "Console proxy round-trip latency",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
)
grade_checks_total = Counter(
    "netlab_grade_checks_total",
    "Grading checks run, by result",
    ["result"],
)
deploy_total = Counter(
    "netlab_deploys_total", "Lab deploys, by outcome", ["outcome"]
)


def metrics_registry():
    return REGISTRY
