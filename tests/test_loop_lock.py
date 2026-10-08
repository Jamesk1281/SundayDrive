"""Loop planning must never make a driver wait (review finding K-1).

A loop build is refused with a 503 rather than queued when another is running,
and the mid-drive loop rejoin (`via`) has a planner and a lock of its own, so
it is neither queued behind loop builds nor refused. docs/loop-lock-contention.md.

Every request that could block runs on a worker thread joined with a timeout,
so a regression fails here instead of hanging the suite.
"""

import sys
import threading
from datetime import date

import pytest

from conftest import DATA, ROOT, ROUTER_DATA

NEEDHAM = "42.2809,-71.2378"
BOSTON = "42.3551,-71.0657"
WORCESTER = "42.2626,-71.8023"
REJOIN = {"from": NEEDHAM, "to": BOSTON, "via": WORCESTER, "pref": "1.00"}
PLAN = {"from": WORCESTER, "to": BOSTON, "pref": "0.5"}


@pytest.fixture(scope="module")
def server():
    missing = [f for f in ROUTER_DATA if not (DATA / f).exists()]
    if missing:
        pytest.skip(f"built graph missing ({', '.join(missing)})")
    import os
    os.environ.setdefault("SUNDAYDRIVE_DATA", str(DATA))
    sys.path.insert(0, str(ROOT / "server"))
    import app as server_app
    server_app.app.config["TESTING"] = True
    return server_app


@pytest.fixture
def client(server, monkeypatch):
    monkeypatch.setattr(server, "_today", lambda: date(2027, 7, 15))
    return server.app.test_client()


def _post(client, path, data, timeout=120):
    """POST on a worker thread; the response, or None if it never came back."""
    box = {}
    worker = threading.Thread(
        target=lambda: box.setdefault("r", client.post(path, data=data)),
        daemon=True)
    worker.start()
    worker.join(timeout)
    return box.get("r")


def _held(lock):
    """Hold `lock` from another thread until the returned event is set, the
    way a running loop build holds it."""
    acquired, done = threading.Event(), threading.Event()

    def hold():
        with lock:
            acquired.set()
            done.wait(120)
    threading.Thread(target=hold, daemon=True).start()
    assert acquired.wait(10)
    return done


class TestTheRejoin:
    def test_is_not_blocked_by_a_running_loop_build(self, server, client):
        done = _held(server.LOOP_LOCK)
        try:
            response = _post(client, "/api/route", REJOIN)
        finally:
            done.set()
        assert response is not None, "the rejoin queued behind a loop build"
        assert response.status_code == 200
        assert set(response.get_json()) == {"fastest", "scenic"}

    def test_is_never_refused_as_busy(self, server, client, monkeypatch):
        """Trap 1: a refusal mid-drive is booked as the server's "no", which
        climbs the reroute backoff and puts the words under the trip card."""
        monkeypatch.setattr(server, "LOOP_BUSY_WAIT_S", 0.0)
        done = _held(server.LOOP_LOCK)
        try:
            for data in (REJOIN, {**PLAN, "heading": "90"}, {**PLAN, "pref": "0"}):
                response = _post(client, "/api/route", data)
                assert response is not None and response.status_code == 200, data
        finally:
            done.set()

    def test_uses_its_own_planner(self, server):
        assert server.REJOINER is not server.LOOPER
        assert server.REJOIN_LOCK is not server.LOOP_LOCK


class TestALoopBuild:
    def test_is_refused_with_json_while_another_runs(self, server, client,
                                                     monkeypatch):
        monkeypatch.setattr(server, "LOOP_BUSY_WAIT_S", 0.05)
        done = _held(server.LOOP_LOCK)
        try:
            response = _post(client, "/api/loop",
                             {"from": NEEDHAM, "km": "47", "sector": "W"})
        finally:
            done.set()
        assert response is not None, "the loop build queued instead of refusing"
        assert response.status_code == 503
        assert response.get_json() == {"error": server.LOOP_BUSY}
        assert server.IN_FLIGHT == 0

    def test_waits_for_a_build_that_ends_inside_the_wait(self, server, client,
                                                         monkeypatch):
        """The usual overlap is one person releasing the slider twice; their
        second request should wait for their first, not be told it is busy."""
        monkeypatch.setattr(server, "LOOP_BUSY_WAIT_S", 5.0)
        done = _held(server.LOOP_LOCK)
        threading.Timer(0.2, done.set).start()
        response = _post(client, "/api/loop", {"from": NEEDHAM, "km": "41"})
        assert response is not None and response.status_code == 200

    def test_a_cached_loop_is_served_while_another_build_runs(self, server, client,
                                                              monkeypatch):
        """Trap 3: going back to the direction you liked costs nothing, and is
        never refused."""
        params = {"from": NEEDHAM, "km": "36", "sector": "N"}
        first = client.post("/api/loop", data=params)
        assert first.status_code == 200
        monkeypatch.setattr(server, "LOOP_BUSY_WAIT_S", 0.0)
        done = _held(server.LOOP_LOCK)
        try:
            again = _post(client, "/api/loop", params, timeout=10)
        finally:
            done.set()
        assert again is not None and again.status_code == 200
        assert again.get_json() == first.get_json()


class TestTheOptionsBusyGuard:
    """Trap 4: options give way to a driver, so `_not_alone()` must still see
    both a loop build and a rejoin."""

    def test_sees_a_loop_build(self, server):
        done = _held(server.LOOP_LOCK)
        try:
            assert server._not_alone()
        finally:
            done.set()

    def test_sees_a_running_rejoin(self, server, client, monkeypatch):
        entered, release = threading.Event(), threading.Event()
        resume = server.REJOINER.resume

        def slow_resume(*args, **kwargs):
            entered.set()
            release.wait(60)
            return resume(*args, **kwargs)
        monkeypatch.setattr(server.REJOINER, "resume", slow_resume)
        box = {}
        worker = threading.Thread(
            target=lambda: box.setdefault("r", client.post("/api/route",
                                                           data=REJOIN)),
            daemon=True)
        worker.start()
        try:
            assert entered.wait(60)
            # Counted through `_computing()`, not only through its lock.
            assert server.IN_FLIGHT == 1
            assert server._not_alone()
            monkeypatch.setattr(server, "ROUTE_OPTIONS", True)
            plan = _post(client, "/api/route", {**PLAN, "options": "1"})
            assert plan is not None and plan.status_code == 200
            assert "options" not in plan.get_json()
        finally:
            release.set()
            worker.join(120)
        assert box["r"].status_code == 200
        assert server.IN_FLIGHT == 0
