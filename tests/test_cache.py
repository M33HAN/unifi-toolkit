"""Tests for caching module."""
import time
from datetime import datetime, timezone, timedelta

import pytest

from shared import cache


class TestGatewayInfoCache:
    """Tests for gateway info caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate_all()

    def test_get_gateway_info_returns_none_when_empty(self):
        """Should return None when cache is empty."""
        result = cache.get_gateway_info()
        assert result is None

    def test_set_gateway_info_stores_data(self):
        """Should store gateway info in cache."""
        data = {
            "has_gateway": True,
            "gateway_model": "UDM",
            "gateway_name": "Dream Machine",
            "supports_ids_ips": True,
        }

        cache.set_gateway_info(data)
        result = cache.get_gateway_info()

        assert result == data

    def test_gateway_info_expires_after_ttl(self):
        """Gateway info should expire after TTL."""
        data = {"has_gateway": True}
        cache.set_gateway_info(data)

        # Manually expire the cache entry
        cache._cache["gateway_info"]["timestamp"] = (
            datetime.now(timezone.utc) - timedelta(seconds=cache.CACHE_TTL_SECONDS + 1)
        )

        result = cache.get_gateway_info()
        assert result is None

    def test_gateway_info_available_within_ttl(self):
        """Gateway info should be available within TTL window."""
        data = {"has_gateway": True}
        cache.set_gateway_info(data)

        # Set timestamp to just before expiration
        cache._cache["gateway_info"]["timestamp"] = (
            datetime.now(timezone.utc) - timedelta(seconds=cache.CACHE_TTL_SECONDS - 1)
        )

        result = cache.get_gateway_info()
        assert result == data


class TestIpsSettingsCache:
    """Tests for IPS settings caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate_all()

    def test_get_ips_settings_returns_none_when_empty(self):
        """Should return None when cache is empty."""
        result = cache.get_ips_settings()
        assert result is None

    def test_set_ips_settings_stores_data(self):
        """Should store IPS settings in cache."""
        data = {
            "ips_mode": "ips",
            "ips_enabled": True,
            "honeypot_enabled": False,
        }

        cache.set_ips_settings(data)
        result = cache.get_ips_settings()

        assert result == data

    def test_ips_settings_expires_after_ttl(self):
        """IPS settings should expire after TTL."""
        data = {"ips_mode": "disabled"}
        cache.set_ips_settings(data)

        # Manually expire
        cache._cache["ips_settings"]["timestamp"] = (
            datetime.now(timezone.utc) - timedelta(seconds=cache.CACHE_TTL_SECONDS + 1)
        )

        result = cache.get_ips_settings()
        assert result is None


class TestSystemStatusCache:
    """Tests for system status caching."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate_all()

    def test_get_system_status_returns_none_when_empty(self):
        """Should return None when cache is empty."""
        result = cache.get_system_status()
        assert result is None

    def test_set_system_status_stores_data(self):
        """Should store system status in cache."""
        data = {
            "gateway_info": {"has_gateway": True},
            "clients_count": 42,
            "health": "good",
        }

        cache.set_system_status(data)
        result = cache.get_system_status()

        assert result == data


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate_all()

    def test_invalidate_all_clears_cache(self):
        """Should clear all cache entries."""
        cache.set_gateway_info({"has_gateway": True})
        cache.set_ips_settings({"ips_mode": "ips"})
        cache.set_system_status({"health": "good"})

        cache.invalidate_all()

        assert cache.get_gateway_info() is None
        assert cache.get_ips_settings() is None
        assert cache.get_system_status() is None

    def test_invalidate_specific_key(self):
        """Should invalidate only the specified key."""
        cache.set_gateway_info({"has_gateway": True})
        cache.set_ips_settings({"ips_mode": "ips"})

        cache.invalidate("gateway_info")

        assert cache.get_gateway_info() is None
        assert cache.get_ips_settings() is not None

    def test_invalidate_nonexistent_key_no_error(self):
        """Should not error when invalidating non-existent key."""
        cache.invalidate("nonexistent_key")
        # Should complete without error


class TestCacheAge:
    """Tests for cache age tracking."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate_all()

    def test_get_cache_age_returns_none_for_empty_cache(self):
        """Should return None for non-existent cache entry."""
        age = cache.get_cache_age("gateway_info")
        assert age is None

    def test_get_cache_age_returns_seconds(self):
        """Should return age in seconds."""
        cache.set_gateway_info({"has_gateway": True})

        age = cache.get_cache_age("gateway_info")

        assert age is not None
        assert isinstance(age, float)
        assert age >= 0
        assert age < 1  # Should be very recent

    def test_cache_age_increases_over_time(self):
        """Cache age should increase as time passes."""
        cache.set_gateway_info({"has_gateway": True})

        age1 = cache.get_cache_age("gateway_info")
        time.sleep(0.1)  # Wait 100ms
        age2 = cache.get_cache_age("gateway_info")

        assert age2 > age1


class TestCacheBehavior:
    """Tests for overall cache behavior."""

    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate_all()

    def test_cache_entries_independent(self):
        """Different cache entries should be independent."""
        gateway_data = {"has_gateway": True}
        ips_data = {"ips_mode": "ips"}

        cache.set_gateway_info(gateway_data)
        cache.set_ips_settings(ips_data)

        # Invalidate one
        cache.invalidate("gateway_info")

        # Only the invalidated one should be None
        assert cache.get_gateway_info() is None
        assert cache.get_ips_settings() == ips_data

    def test_cache_overwrites_existing_data(self):
        """Setting cache should overwrite existing data."""
        old_data = {"has_gateway": False}
        new_data = {"has_gateway": True, "gateway_model": "UDM"}

        cache.set_gateway_info(old_data)
        cache.set_gateway_info(new_data)

        result = cache.get_gateway_info()
        assert result == new_data

    def test_cache_handles_empty_dict(self):
        """Should handle empty dict as valid cache data."""
        empty_data = {}

        cache.set_gateway_info(empty_data)
        result = cache.get_gateway_info()

        assert result == empty_data

    def test_cache_handles_nested_data(self):
        """Should handle nested dictionary data."""
        nested_data = {
            "gateway": {
                "model": "UDM",
                "features": ["ips", "ids", "firewall"],
                "config": {"enabled": True, "mode": "auto"},
            }
        }

        cache.set_system_status(nested_data)
        result = cache.get_system_status()

        assert result == nested_data
