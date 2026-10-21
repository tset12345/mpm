import asyncio

import pytest

from app.services.cache import AsyncTTLCache


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def run(coro):
    return asyncio.run(coro)


def make(ttl=10, **kw):
    clock = Clock()
    return AsyncTTLCache(ttl, clock=clock, **kw), clock


def counting_loader(values):
    calls = {"n": 0}

    async def loader():
        i = calls["n"]
        calls["n"] += 1
        v = values[min(i, len(values) - 1)]
        if isinstance(v, Exception):
            raise v
        return v

    return loader, calls


def test_hit_within_ttl_and_reload_after():
    cache, clock = make(ttl=10)
    loader, calls = counting_loader(["a", "b"])

    async def go():
        r1 = await cache.get_or_load("k", loader)
        clock.t += 9
        r2 = await cache.get_or_load("k", loader)
        clock.t += 2
        r3 = await cache.get_or_load("k", loader)
        return r1, r2, r3

    assert run(go()) == ("a", "a", "b")
    assert calls["n"] == 2


def test_concurrent_requests_share_one_load():
    cache, _ = make()
    state = {"n": 0}

    async def loader():
        state["n"] += 1
        await asyncio.sleep(0.02)
        return "v"

    async def go():
        return await asyncio.gather(*[cache.get_or_load("k", loader) for _ in range(20)])

    assert run(go()) == ["v"] * 20
    assert state["n"] == 1


def test_concurrent_requests_share_failure():
    cache, _ = make()
    state = {"n": 0}

    async def loader():
        state["n"] += 1
        await asyncio.sleep(0.01)
        raise RuntimeError("down")

    async def go():
        return await asyncio.gather(*[cache.get_or_load("k", loader) for _ in range(5)], return_exceptions=True)

    results = run(go())
    assert all(isinstance(r, RuntimeError) for r in results)
    assert state["n"] == 1


def test_failure_serves_stale_within_window_only():
    cache, clock = make(ttl=10, stale_ttl=100)
    loader, _ = counting_loader(["good", RuntimeError("down"), RuntimeError("down")])

    async def go():
        first = await cache.get_or_load("k", loader)
        clock.t += 50
        stale = await cache.get_or_load("k", loader)
        clock.t += 100
        with pytest.raises(RuntimeError):
            await cache.get_or_load("k", loader)
        return first, stale

    assert run(go()) == ("good", "good")


def test_failure_without_stale_raises():
    cache, _ = make(stale_ttl=0)
    loader, _ = counting_loader([RuntimeError("x")])
    with pytest.raises(RuntimeError):
        run(cache.get_or_load("k", loader))


def test_should_cache_skips_empty_results():
    cache, _ = make()
    loader, calls = counting_loader([[], [1]])

    async def go():
        a = await cache.get_or_load("k", loader, should_cache=bool)
        b = await cache.get_or_load("k", loader, should_cache=bool)
        c = await cache.get_or_load("k", loader, should_cache=bool)
        return a, b, c

    assert run(go()) == ([], [1], [1])
    assert calls["n"] == 2


def test_keys_are_independent():
    cache, _ = make()

    async def go():
        a = await cache.get_or_load("a", lambda: asyncio.sleep(0, "A"))
        b = await cache.get_or_load("b", lambda: asyncio.sleep(0, "B"))
        return a, b

    assert run(go()) == ("A", "B")


def test_max_size_evicts_oldest():
    cache, clock = make(ttl=1000, max_size=3)

    async def go():
        for k in ["a", "b", "c", "d"]:
            clock.t += 1
            await cache.get_or_load(k, lambda k=k: asyncio.sleep(0, k))

    run(go())
    assert len(cache) == 3
    assert cache.peek("a") is None
    assert cache.peek("d") == "d"


def test_invalidate_single_and_all():
    cache, _ = make()
    loader, calls = counting_loader(["x", "y", "z"])

    async def go():
        await cache.get_or_load("k", loader)
        cache.invalidate("k")
        b = await cache.get_or_load("k", loader)
        cache.invalidate()
        c = await cache.get_or_load("k", loader)
        return b, c

    assert run(go()) == ("y", "z")


def test_waiter_cancellation_does_not_cancel_shared_load():
    cache, _ = make()
    state = {"n": 0}

    async def loader():
        state["n"] += 1
        await asyncio.sleep(0.05)
        return "done"

    async def go():
        t1 = asyncio.create_task(cache.get_or_load("k", loader))
        await asyncio.sleep(0.01)
        t2 = asyncio.create_task(cache.get_or_load("k", loader))
        await asyncio.sleep(0.01)
        t1.cancel()
        result = await t2
        return result

    assert run(go()) == "done"
    assert state["n"] == 1
