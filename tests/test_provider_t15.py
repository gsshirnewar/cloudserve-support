import time

from src.llm.provider import DiskCache, LLMProvider, LLMRequest, RateLimiter, SimulationBackend


def test_same_call_twice_second_is_cache_hit_no_network(tmp_path):
    backend = SimulationBackend(mode="off", success_text='{"status":"ok"}')
    provider = LLMProvider(
        backend=backend,
        cache=DiskCache(cache_dir=tmp_path / "cache", enabled=True),
        rate_limiter=RateLimiter(max_concurrency=4),
        simulation_mode="off",
    )
    req = LLMRequest(prompt="classify ticket", model="test-model", prompt_version="P-CLS-001@v1.0.0", params={"temperature": 0})

    r1 = provider.generate(req)
    r2 = provider.generate(req)

    assert r1.ok is True and r1.cache_hit is False
    assert r2.ok is True and r2.cache_hit is True
    assert r2.text == r1.text
    assert backend.call_count == 1  # no network/provider call on cache hit


def test_simulated_429_retries_with_backoff_then_succeeds(tmp_path):
    backend = SimulationBackend(mode="rate_limit", success_text='{"ok":true}')
    provider = LLMProvider(
        backend=backend,
        cache=DiskCache(cache_dir=tmp_path / "cache", enabled=False),
        rate_limiter=RateLimiter(max_concurrency=2),
        simulation_mode="rate_limit",
    )
    req = LLMRequest(prompt="retry test", model="test-model", prompt_version="v1", params={})

    start = time.monotonic()
    result = provider.generate(req)
    elapsed = time.monotonic() - start

    assert result.ok is True
    assert result.degraded is False
    assert result.retries >= 1
    assert backend.call_count >= 2
    # Bounded by backoff logic (should be quick but allow jitter/scheduling)
    assert elapsed < 5.0


def test_simulated_outage_returns_degraded_result_within_bounded_time(tmp_path):
    backend = SimulationBackend(mode="unavailable")
    provider = LLMProvider(
        backend=backend,
        cache=DiskCache(cache_dir=tmp_path / "cache", enabled=False),
        rate_limiter=RateLimiter(max_concurrency=2),
        simulation_mode="unavailable",
    )
    req = LLMRequest(prompt="outage test", model="test-model", prompt_version="v1", params={})

    start = time.monotonic()
    result = provider.generate(req)
    elapsed = time.monotonic() - start

    assert result.ok is False
    assert result.degraded is True
    assert result.error_type in {"unavailable", "provider_error"}
    assert elapsed < 3.0
    # Must not raise to pipeline (if we got here, no exception escaped)


def test_100_consecutive_calls_do_not_crash_rate_limiter(tmp_path):
    backend = SimulationBackend(mode="off", success_text='{"n":1}')
    provider = LLMProvider(
        backend=backend,
        cache=DiskCache(cache_dir=tmp_path / "cache", enabled=False),
        rate_limiter=RateLimiter(max_concurrency=4, min_interval_seconds=0.0),
        simulation_mode="off",
    )

    results = []
    for i in range(100):
        req = LLMRequest(prompt=f"call-{i}", model="test-model", prompt_version="v1", params={"i": i})
        results.append(provider.generate(req))

    assert len(results) == 100
    assert all(r.ok for r in results)
    assert backend.call_count == 100
