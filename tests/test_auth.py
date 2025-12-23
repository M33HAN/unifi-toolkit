"""Tests for authentication module."""
import os
import bcrypt
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.routers.auth import (
    is_auth_enabled,
    verify_password,
    create_session,
    verify_session,
    check_rate_limit,
    record_login_attempt,
    _sessions,
    _login_attempts,
)


class TestAuthEnabled:
    """Tests for auth enabled check."""

    def test_auth_disabled_in_local_mode(self):
        """Should return False when deployment type is local."""
        with patch.dict(os.environ, {"DEPLOYMENT_TYPE": "local"}):
            assert is_auth_enabled() is False

    def test_auth_enabled_in_production_mode(self):
        """Should return True when deployment type is production."""
        with patch.dict(os.environ, {"DEPLOYMENT_TYPE": "production"}):
            assert is_auth_enabled() is True

    def test_auth_disabled_by_default(self):
        """Should default to False when DEPLOYMENT_TYPE not set."""
        env = os.environ.copy()
        if "DEPLOYMENT_TYPE" in env:
            del env["DEPLOYMENT_TYPE"]

        with patch.dict(os.environ, env, clear=True):
            assert is_auth_enabled() is False


class TestPasswordVerification:
    """Tests for password verification."""

    def test_verify_correct_password(self):
        """Should return True for correct password."""
        password = "MySecurePass123"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        assert verify_password(password, password_hash) is True

    def test_verify_incorrect_password(self):
        """Should return False for incorrect password."""
        correct_password = "MySecurePass123"
        wrong_password = "WrongPassword456"
        password_hash = bcrypt.hashpw(correct_password.encode(), bcrypt.gensalt()).decode()

        assert verify_password(wrong_password, password_hash) is False

    def test_verify_empty_password(self):
        """Should handle empty password correctly."""
        password = ""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        assert verify_password(password, password_hash) is True
        assert verify_password("not-empty", password_hash) is False

    def test_verify_password_case_sensitive(self):
        """Password verification should be case sensitive."""
        password = "MyPassword123"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        assert verify_password("mypassword123", password_hash) is False
        assert verify_password("MYPASSWORD123", password_hash) is False

    def test_verify_invalid_hash_returns_false(self):
        """Should return False for invalid password hash."""
        password = "test"
        invalid_hash = "not-a-valid-bcrypt-hash"

        assert verify_password(password, invalid_hash) is False


class TestSessionManagement:
    """Tests for session creation and verification."""

    def setup_method(self):
        """Clear sessions before each test."""
        _sessions.clear()

    def test_create_session_returns_token(self):
        """Should return a session token string."""
        token = create_session("testuser")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_session_stores_username(self):
        """Should store username in session."""
        username = "testuser"
        token = create_session(username)

        assert token in _sessions
        assert _sessions[token]["username"] == username

    def test_create_session_sets_expiration(self):
        """Should set session expiration to 7 days."""
        token = create_session("testuser")

        session = _sessions[token]
        assert "expires_at" in session

        # Should expire in approximately 7 days
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        actual_expiry = session["expires_at"]

        # Allow 1 minute difference for test execution time
        time_diff = abs((actual_expiry - expected_expiry).total_seconds())
        assert time_diff < 60

    def test_create_session_generates_unique_tokens(self):
        """Should generate different tokens for each session."""
        token1 = create_session("user1")
        token2 = create_session("user2")

        assert token1 != token2

    def test_verify_session_returns_session_data(self):
        """Should return session data for valid token."""
        username = "testuser"
        token = create_session(username)

        session = verify_session(token)

        assert session is not None
        assert session["username"] == username

    def test_verify_session_returns_none_for_invalid_token(self):
        """Should return None for invalid token."""
        session = verify_session("invalid-token-12345")

        assert session is None

    def test_verify_session_removes_expired_sessions(self):
        """Should remove and return None for expired sessions."""
        token = create_session("testuser")

        # Manually expire the session
        _sessions[token]["expires_at"] = datetime.utcnow() - timedelta(hours=1)

        session = verify_session(token)

        assert session is None
        assert token not in _sessions


class TestRateLimiting:
    """Tests for login rate limiting."""

    def setup_method(self):
        """Clear login attempts before each test."""
        _login_attempts.clear()

    def test_check_rate_limit_allows_first_attempt(self):
        """Should allow first login attempt."""
        is_allowed, wait_seconds = check_rate_limit("192.168.1.100")

        assert is_allowed is True
        assert wait_seconds == 0

    def test_check_rate_limit_allows_less_than_max_failures(self):
        """Should allow attempts when under the limit."""
        ip = "192.168.1.100"

        # Record 4 failed attempts (limit is 5)
        for _ in range(4):
            record_login_attempt(ip, success=False)

        is_allowed, wait_seconds = check_rate_limit(ip)

        assert is_allowed is True
        assert wait_seconds == 0

    def test_check_rate_limit_blocks_after_max_failures(self):
        """Should block after 5 failed attempts."""
        ip = "192.168.1.100"

        # Record 5 failed attempts
        for _ in range(5):
            record_login_attempt(ip, success=False)

        is_allowed, wait_seconds = check_rate_limit(ip)

        assert is_allowed is False
        assert wait_seconds > 0

    def test_check_rate_limit_ignores_successful_attempts(self):
        """Should only count failed attempts for rate limiting."""
        ip = "192.168.1.100"

        # Record mix of failed and successful attempts
        for _ in range(10):
            record_login_attempt(ip, success=True)
        for _ in range(4):
            record_login_attempt(ip, success=False)

        is_allowed, wait_seconds = check_rate_limit(ip)

        # Should still be allowed (only 4 failures)
        assert is_allowed is True

    def test_check_rate_limit_different_ips_independent(self):
        """Rate limiting should be per-IP address."""
        ip1 = "192.168.1.100"
        ip2 = "192.168.1.101"

        # Block IP1
        for _ in range(5):
            record_login_attempt(ip1, success=False)

        # IP2 should still be allowed
        is_allowed, _ = check_rate_limit(ip2)
        assert is_allowed is True

        # IP1 should be blocked
        is_allowed, _ = check_rate_limit(ip1)
        assert is_allowed is False

    def test_record_login_attempt_cleans_old_attempts(self):
        """Should remove login attempts older than the rate limit window."""
        ip = "192.168.1.100"

        # Record old attempts (simulate by manipulating the list)
        old_timestamp = datetime.utcnow() - timedelta(seconds=400)  # Older than 5min window
        _login_attempts[ip] = [(old_timestamp, False)] * 5

        # Record new attempt
        record_login_attempt(ip, success=False)

        # Old attempts should be cleaned up
        recent_attempts = [ts for ts, _ in _login_attempts[ip]]
        assert all(ts > datetime.utcnow() - timedelta(seconds=300) for ts in recent_attempts)

    def test_rate_limit_wait_seconds_decreases_over_time(self):
        """Wait seconds should decrease as time passes."""
        ip = "192.168.1.100"

        # Block the IP
        for _ in range(5):
            record_login_attempt(ip, success=False)

        _, wait_seconds_1 = check_rate_limit(ip)

        # Wait a bit (simulate with smaller window check)
        import time
        time.sleep(1)

        _, wait_seconds_2 = check_rate_limit(ip)

        # Second check should have fewer wait seconds
        assert wait_seconds_2 <= wait_seconds_1
