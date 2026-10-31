from rate_limiter import RateLimiter


def test_allows_calls_up_to_the_limit():
    limiter = RateLimiter(max_calls=2)

    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_window_resets_after_the_period():
    limiter = RateLimiter(max_calls=1, period_seconds=0)

    assert limiter.allow() is True
    assert limiter.allow() is True


def test_zero_means_no_limit():
    limiter = RateLimiter(max_calls=0)

    assert all(limiter.allow() for _ in range(100))
