"""Exponential-backoff retry helper."""

from __future__ import annotations

import pytest

from foodanalyzer.services.retry import RetryPolicy, retry_call, retry_call_async


class Boom(Exception):
    pass


def test_succeeds_first_try():
    calls = []
    out = retry_call(lambda: calls.append(1) or "ok", retry_on=(Boom,), sleep=lambda _: None)
    assert out == "ok"
    assert len(calls) == 1


def test_retries_then_succeeds():
    state = {"n": 0}
    delays: list[float] = []

    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise Boom("nope")
        return state["n"]

    out = retry_call(
        flaky,
        retry_on=(Boom,),
        policy=RetryPolicy(max_attempts=5, base_delay=1, max_delay=10, jitter=0),
        sleep=delays.append,
    )
    assert out == 3
    assert delays == [1, 2]  # backoff doubles


def test_gives_up_and_reraises():
    def always_fails():
        raise Boom("still nope")

    with pytest.raises(Boom):
        retry_call(
            always_fails,
            retry_on=(Boom,),
            policy=RetryPolicy(max_attempts=3, base_delay=0, jitter=0),
            sleep=lambda _: None,
        )


def test_does_not_retry_unlisted_exception():
    calls = []

    def wrong_error():
        calls.append(1)
        raise ValueError("different")

    with pytest.raises(ValueError):
        retry_call(wrong_error, retry_on=(Boom,), sleep=lambda _: None)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_async_retries_then_succeeds():
    state = {"n": 0}

    async def flaky():
        state["n"] += 1
        if state["n"] < 2:
            raise Boom("nope")
        return "done"

    async def no_sleep(_):
        return None

    out = await retry_call_async(
        flaky,
        retry_on=(Boom,),
        policy=RetryPolicy(max_attempts=3, base_delay=0, jitter=0),
        sleep=no_sleep,
    )
    assert out == "done"
