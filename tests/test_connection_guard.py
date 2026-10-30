import pytest

from catchall.connection_guard import SessionLimiter, origin_allowed
from catchall.settings import ConnectionSettings


def test_missing_origin_is_allowed_because_browsers_always_send_one() -> None:
    assert origin_allowed(None, ("captions.example",))


def test_origin_must_match_the_requested_host() -> None:
    assert origin_allowed("https://captions.example", ("captions.example",))
    assert origin_allowed("HTTPS://Captions.Example/", ("captions.example",))
    assert origin_allowed("http://127.0.0.1:8000", ("127.0.0.1:8000",))
    assert not origin_allowed("https://elsewhere.example", ("captions.example",))
    assert not origin_allowed("http://127.0.0.1:9000", ("127.0.0.1:8000",))


def test_forwarded_host_counts_as_a_requested_host() -> None:
    assert origin_allowed(
        "https://captions.example",
        ("127.0.0.1:8000", "captions.example"),
    )


def test_opaque_and_malformed_origins_are_rejected() -> None:
    assert not origin_allowed("null", ("captions.example",))
    assert not origin_allowed("", ("captions.example",))
    assert not origin_allowed("https://captions.example", (None,))


def test_allow_list_replaces_the_host_comparison() -> None:
    allowed = ("https://portfolio.example",)

    assert origin_allowed("https://portfolio.example/", ("api.internal",), allowed)
    assert not origin_allowed("https://api.internal", ("api.internal",), allowed)


def test_session_limiter_enforces_capacity_and_releases() -> None:
    limiter = SessionLimiter(2)

    assert limiter.try_acquire()
    assert limiter.try_acquire()
    assert not limiter.try_acquire()
    assert limiter.active == 2

    limiter.release()

    assert limiter.active == 1
    assert limiter.try_acquire()


def test_session_limiter_rejects_invalid_use() -> None:
    with pytest.raises(ValueError):
        SessionLimiter(0)

    with pytest.raises(RuntimeError):
        SessionLimiter(1).release()


def test_connection_settings_defaults() -> None:
    settings = ConnectionSettings.from_environment({})

    assert settings.max_sessions == 2
    assert settings.allowed_origins == ()


def test_connection_settings_read_environment() -> None:
    settings = ConnectionSettings.from_environment(
        {
            "CATCHALL_MAX_SESSIONS": " 4 ",
            "CATCHALL_ALLOWED_ORIGINS": "https://Portfolio.example/, https://captions.example,,",
        }
    )

    assert settings.max_sessions == 4
    assert settings.allowed_origins == ("https://portfolio.example", "https://captions.example")


@pytest.mark.parametrize("value", ["0", "-1", "two", "1.5"])
def test_connection_settings_reject_invalid_session_limits(value: str) -> None:
    with pytest.raises(ValueError):
        ConnectionSettings.from_environment({"CATCHALL_MAX_SESSIONS": value})
