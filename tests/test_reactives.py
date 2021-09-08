#!/usr/bin/env python

"""Tests for `shiny.reactives` and `shiny.reactcore`."""

import pytest
import asyncio

import shiny.reactcore as reactcore
from shiny.reactives import *


def test_flush_runs_newly_invalidated():
    """
    Make sure that a flush will also run any reactives that were invalidated
    during the flush.
    """

    v1 = ReactiveVal(1)
    v2 = ReactiveVal(2)

    v2_result = None
    # In practice, on the first flush, Observers run in the order that they were
    # created. Our test checks that o2 runs _after_ o1.
    @Observer
    def o2():
        nonlocal v2_result
        v2_result = v2()
    @Observer
    def o1():
        v2(v1())

    asyncio.run(reactcore.flush())
    assert(v2_result == 1)
    assert(o2._exec_count == 2)
    assert(o1._exec_count == 1)


def test_flush_runs_newly_invalidated_async():
    """
    Make sure that a flush will also run any reactives that were invalidated
    during the flush. (Same as previous test, but async.)
    """

    v1 = ReactiveVal(1)
    v2 = ReactiveVal(2)

    v2_result = None
    # In practice, on the first flush, Observers run in the order that they were
    # created. Our test checks that o2 runs _after_ o1.
    @ObserverAsync
    async def o2():
        nonlocal v2_result
        v2_result = v2()
    @ObserverAsync
    async def o1():
        v2(v1())

    asyncio.run(reactcore.flush())
    assert(v2_result == 1)
    assert(o2._exec_count == 2)
    assert(o1._exec_count == 1)

# ======================================================================
# Setting ReactiveVal to same value doesn't invalidate downstream
# ======================================================================

def test_reactive_val_same_no_invalidate():
    v = ReactiveVal(1)

    @Observer
    def o():
        v()

    asyncio.run(reactcore.flush())
    assert(o._exec_count == 1)

    v(1)
    asyncio.run(reactcore.flush())
    assert(o._exec_count == 1)

test_reactive_val_same_no_invalidate()

# ======================================================================
# Recursive calls to reactives
# ======================================================================
def test_recursive_reactive():
    v = ReactiveVal(5)

    @Reactive
    def r():
        if v() == 0:
            return 0
        v(v() - 1)
        r()

    @Observer
    def o():
        r()

    asyncio.run(reactcore.flush())
    assert o._exec_count == 2
    assert r._exec_count == 6
    assert isolate(v) == 0


def test_recursive_reactive_async():
    v = ReactiveVal(5)

    @ReactiveAsync
    async def r():
        if v() == 0:
            return 0
        v(v() - 1)
        await r()

    @ObserverAsync
    async def o():
        await r()

    asyncio.run(reactcore.flush())
    assert o._exec_count == 2
    assert r._exec_count == 6
    assert isolate(v) == 0

# ======================================================================
# Concurrent async
# ======================================================================
def test_async_concurrent():
    x = ReactiveVal(1)

    exec_order: list[str] = []
    results: list[int] = []

    async def react_chain(n: int):

        @ReactiveAsync
        async def r():
            nonlocal exec_order
            exec_order.append(f"r{n}-1")
            await asyncio.sleep(0)
            exec_order.append(f"r{n}-2")
            return x() + 10

        @ObserverAsync
        async def _():
            nonlocal exec_order
            exec_order.append(f"o{n}-1")
            await asyncio.sleep(0)
            exec_order.append(f"o{n}-2")
            val = await r()
            exec_order.append(f"o{n}-3")
            results.append(val + n * 100)


    async def go():
        await asyncio.gather(
            react_chain(1),
            react_chain(2)
        )

        await reactcore.flush()

        x(5)
        await reactcore.flush()


    asyncio.run(go())

    assert results == [111, 211, 115, 215]

    # This is the order of execution if async observers are run with separate
    # (interleaved) tasks. When it hits an `asyncio.sleep(0)`, it will yield
    # control and then the other observer in the other task will run.
    assert exec_order == [
        'o1-1', 'o2-1',
        'o1-2', 'o2-2',
        'r1-1', 'r2-1',
        'r1-2', 'r2-2',
        'o1-3', 'o2-3',
        'o1-1', 'o2-1',
        'o1-2', 'o2-2',
        'r1-1', 'r2-1',
        'r1-2', 'r2-2',
        'o1-3', 'o2-3'
    ]

    # This is the order of execution if the async observers are run
    # sequentially. The `asyncio.sleep(0)` still yields control, but since there
    # are no other observers scheduled, it will simply resume at the same point.
    # assert exec_order == [
    #     'o1-1', 'o1-2', 'r1-1', 'r1-2', 'o1-3',
    #     'o2-1', 'o2-2', 'r2-1', 'r2-2', 'o2-3',
    #     'o1-1', 'o1-2', 'r1-1', 'r1-2', 'o1-3',
    #     'o2-1', 'o2-2', 'r2-1', 'r2-2', 'o2-3'
    # ]


# ======================================================================
# isolate()
# ======================================================================
def test_isolate_basic_value():
    # isolate() returns basic value
    assert isolate(lambda: 123) == 123
    assert isolate(lambda: None) is None

def test_isolate_basic_without_context():
    # isolate() works with Reactive and ReactiveVal; allows executing without a
    # reactive context.
    v = ReactiveVal(1)
    @Reactive
    def r():
        return v() + 10

    def get_r():
        return r()

    assert isolate(lambda: v()) == 1
    assert isolate(v) == 1
    assert isolate(lambda: r()) == 11
    assert isolate(r) == 11
    assert isolate(get_r) == 11

def test_isolate_prevents_dependency():
    v = ReactiveVal(1)
    @Reactive
    def r():
        return v() + 10

    v_dep = ReactiveVal(1)  # Use this only for invalidating the observer
    o_val = None
    @Observer
    def o():
        nonlocal o_val
        v_dep()
        o_val = isolate(lambda: r())

    asyncio.run(reactcore.flush())
    assert o_val == 11

    # Changing v() shouldn't invalidate o
    v(2)
    asyncio.run(reactcore.flush())
    assert o_val == 11
    assert o._exec_count == 1

    # v_dep() should invalidate the observer
    v_dep(2)
    asyncio.run(reactcore.flush())
    assert o_val == 12
    assert o._exec_count == 2

# ======================================================================
# isolate_async()
# ======================================================================
def test_isolate_async_basic_value():
    async def f():
        return 123
    async def go():
        assert await isolate_async(f) == 123
    asyncio.run(go())


def test_isolate_async_basic_without_context():
    # isolate_async() works with Reactive and ReactiveVal; allows executing
    # without a reactive context.
    v = ReactiveVal(1)
    @ReactiveAsync
    async def r():
        return v() + 10
    async def get_r():
        return await r()
    async def go():
        assert await isolate_async(r) == 11
        assert await isolate_async(get_r) == 11
    asyncio.run(go())


def test_isolate_async_prevents_dependency():
    v = ReactiveVal(1)
    @ReactiveAsync
    async def r():
        return v() + 10

    v_dep = ReactiveVal(1)  # Use this only for invalidating the observer
    o_val = None
    @ObserverAsync
    async def o():
        nonlocal o_val
        v_dep()
        o_val = await isolate_async(r)

    asyncio.run(reactcore.flush())
    assert o_val == 11

    # Changing v() shouldn't invalidate o
    v(2)
    asyncio.run(reactcore.flush())
    assert o_val == 11
    assert o._exec_count == 1

    # v_dep() should invalidate the observer
    v_dep(2)
    asyncio.run(reactcore.flush())
    assert o_val == 12
    assert o._exec_count == 2
