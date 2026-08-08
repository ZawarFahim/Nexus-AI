"""Tests for asset downloading.

The interesting behaviour here is all failure behaviour: resuming a partial
file, coping with a server that ignores ``Range``, retrying a connection that
dies mid-transfer, and never leaving a truncated file where a complete one
belongs. None of it is exercised by a download that succeeds first time, which
is the only kind that happens while developing.

The network is replaced by a fake ``urlopen`` that serves a known payload and
can be told to fail after N bytes.
"""

from __future__ import annotations

import urllib.error
from pathlib import Path

import pytest

from nexus.core import assets

PAYLOAD = bytes(range(256)) * 400  # 102,400 bytes of recognisable data

# A real socket returns far less than was asked for. Serving the whole payload
# in a single read would make "fail after N bytes" unreachable, and every
# resume test would silently pass without resuming anything.
WIRE_CHUNK = 4_096


class FakeResponse:
    """Serves a slice of a payload, optionally dying partway through."""

    def __init__(self, body: bytes, status: int, fail_after: int | None = None) -> None:
        self.status = status
        self._body = body
        self._fail_after = fail_after
        self._sent = 0

    def read(self, size: int) -> bytes:
        if self._fail_after is not None and self._sent >= self._fail_after:
            raise TimeoutError("connection stalled")

        chunk = self._body[self._sent : self._sent + min(size, WIRE_CHUNK)]
        self._sent += len(chunk)
        return chunk

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeServer:
    """A stand-in for ``urllib.request.urlopen``.

    Attributes:
        requests: Range header of every request, ``None`` when absent. Lets a
            test assert that a retry actually resumed rather than restarting.
    """

    def __init__(
        self,
        payload: bytes = PAYLOAD,
        *,
        fail_after: int | None = None,
        fail_times: int = 0,
        honour_range: bool = True,
    ) -> None:
        self._payload = payload
        self._fail_after = fail_after
        self._fail_times = fail_times
        self._honour_range = honour_range
        self.requests: list[str | None] = []

    def __call__(self, request, timeout: float | None = None) -> FakeResponse:
        header = request.get_header("Range")
        self.requests.append(header)

        offset = 0
        if header and self._honour_range:
            offset = int(header.removeprefix("bytes=").rstrip("-"))

        status = 206 if (header and self._honour_range) else 200
        fail_after = self._fail_after if len(self.requests) <= self._fail_times else None
        return FakeResponse(self._payload[offset:], status, fail_after)


@pytest.fixture
def asset(tmp_path: Path) -> assets.Asset:
    return assets.Asset("test", "https://example.invalid/file.bin", tmp_path / "file.bin")


@pytest.fixture
def serve(monkeypatch):
    def install(server: FakeServer) -> FakeServer:
        monkeypatch.setattr(assets.urllib.request, "urlopen", server)
        monkeypatch.setattr(assets, "RETRY_BACKOFF_SECONDS", 0.0)
        return server

    return install


def test_downloads_a_file(asset, serve):
    serve(FakeServer())
    assets.install([asset])

    assert asset.target.read_bytes() == PAYLOAD
    assert not asset.partial.exists()


def test_skips_an_installed_asset(asset, serve):
    asset.target.write_bytes(b"already here")
    server = serve(FakeServer())

    assets.install([asset])

    assert server.requests == []
    assert asset.target.read_bytes() == b"already here"


def test_resumes_from_a_partial_file(asset, serve):
    asset.partial.write_bytes(PAYLOAD[:40_000])
    server = serve(FakeServer())

    assets.install([asset])

    assert server.requests == ["bytes=40000-"]
    assert asset.target.read_bytes() == PAYLOAD


def test_retries_and_resumes_after_a_stall(asset, serve):
    # Dies 30 KB in on the first attempt, then succeeds.
    server = serve(FakeServer(fail_after=30_000, fail_times=1))

    assets.install([asset])

    assert len(server.requests) == 2
    # The second request must continue rather than start over, or a slow link
    # can never finish a large file.
    assert server.requests[0] is None
    assert server.requests[1] is not None
    assert server.requests[1].startswith("bytes=")
    assert asset.target.read_bytes() == PAYLOAD


def test_resuming_reports_the_bytes_already_on_disk(asset, serve):
    """A resumed download must *look* resumed.

    Counting the existing prefix only after the transfer finishes leaves the
    bar opening at zero and climbing, which is indistinguishable from starting
    over -- the download is correct and the display says it is not.
    """
    asset.partial.write_bytes(PAYLOAD[:80_000])
    serve(FakeServer())
    sized = assets.Asset(asset.label, asset.url, asset.target, len(PAYLOAD))

    seen: list[assets.Progress] = []
    assets.install([sized], on_progress=seen.append)

    assert seen[0].done_bytes == 80_000
    assert seen[0].fraction > 0.75


def test_restarting_does_not_double_count(asset, serve):
    """Bytes given back when a server ignores Range must leave the bar honest."""
    asset.partial.write_bytes(PAYLOAD[:80_000])
    serve(FakeServer(honour_range=False))
    sized = assets.Asset(asset.label, asset.url, asset.target, len(PAYLOAD))

    seen: list[assets.Progress] = []
    assets.install([sized], on_progress=seen.append)

    assert asset.target.read_bytes() == PAYLOAD
    # Without the refund the run would report ~180 KB of a 102 KB file.
    assert seen[-1].total_bytes == len(PAYLOAD)


def test_restarts_when_the_server_ignores_range(asset, serve):
    """A 200 response to a Range request carries the whole file.

    Appending it to the existing prefix would produce a file that is the right
    kind of wrong -- too long, and corrupt in the middle.
    """
    asset.partial.write_bytes(PAYLOAD[:40_000])
    serve(FakeServer(honour_range=False))

    assets.install([asset])

    assert asset.target.read_bytes() == PAYLOAD


def test_gives_up_after_the_attempt_limit(asset, serve):
    server = serve(FakeServer(fail_after=1_000, fail_times=99))

    with pytest.raises(assets.AssetError, match="Could not download"):
        assets.install([asset], attempts=3)

    assert len(server.requests) == 3
    # The prefix survives so a later run can continue from it.
    assert asset.partial.stat().st_size > 0
    assert not asset.target.exists()


def test_never_leaves_a_truncated_target(asset, serve):
    serve(FakeServer(fail_after=1_000, fail_times=99))

    with pytest.raises(assets.AssetError):
        assets.install([asset], attempts=2)

    assert not asset.target.exists(), "a partial download must not look complete"


def test_cancelling_stops_and_keeps_the_prefix(asset, serve):
    serve(FakeServer())

    with pytest.raises(assets.AssetError, match="cancelled"):
        assets.install([asset], should_cancel=lambda: True)

    assert not asset.target.exists()


def test_survives_a_connection_error(asset, serve, monkeypatch):
    calls = []

    def flaky(request, timeout=None):
        calls.append(request.get_header("Range"))
        if len(calls) == 1:
            raise urllib.error.URLError("name resolution failed")
        return FakeResponse(PAYLOAD, 200)

    monkeypatch.setattr(assets.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(assets, "RETRY_BACKOFF_SECONDS", 0.0)

    assets.install([asset])

    assert asset.target.read_bytes() == PAYLOAD


def test_progress_reaches_one_and_never_exceeds_it(asset, serve):
    serve(FakeServer())
    # Deliberately half the real size, the way a hardcoded estimate goes stale.
    understated = assets.Asset(asset.label, asset.url, asset.target, len(PAYLOAD) // 2)

    seen: list[float] = []
    assets.install([understated], on_progress=lambda p: seen.append(p.fraction))

    assert seen
    assert max(seen) == pytest.approx(1.0)
    assert all(0.0 <= fraction <= 1.0 for fraction in seen)


def test_progress_spans_multiple_assets(tmp_path, serve):
    serve(FakeServer())
    pair = [
        assets.Asset("first", "https://example.invalid/a", tmp_path / "a", len(PAYLOAD)),
        assets.Asset("second", "https://example.invalid/b", tmp_path / "b", len(PAYLOAD)),
    ]

    seen: list[assets.Progress] = []
    assets.install(pair, on_progress=seen.append)

    labels = [p.label for p in seen]
    assert "first" in labels and "second" in labels
    # Bytes accumulate across files rather than resetting, or the bar would
    # jump backwards when the second file starts.
    byte_counts = [p.done_bytes for p in seen]
    assert byte_counts == sorted(byte_counts)
    assert seen[-1].fraction == pytest.approx(1.0)


# -- what Nexus asks for -------------------------------------------------------


def test_required_lists_nothing_once_everything_is_present(tmp_path, monkeypatch):
    monkeypatch.setattr(assets.paths, "models_dir", lambda: tmp_path / "models")
    monkeypatch.setattr(assets.paths, "voices_dir", lambda: tmp_path / "voices")

    missing = assets.required(model="base.en", voice="en_US-ryan-medium")
    assert missing

    for item in missing:
        item.target.parent.mkdir(parents=True, exist_ok=True)
        item.target.write_bytes(b"x")

    assert assets.required(model="base.en", voice="en_US-ryan-medium") == []


def test_unknown_voice_is_rejected():
    with pytest.raises(assets.AssetError, match="Unknown voice"):
        assets.voice_assets("en_US-nobody-medium")


def test_unknown_model_defers_to_faster_whisper():
    """An unrecognised model is not an error; the library can still fetch it."""
    assert assets.whisper_assets("large-v9") == []
