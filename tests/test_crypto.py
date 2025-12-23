"""Tests for encryption utilities."""
import pytest
from cryptography.fernet import Fernet, InvalidToken

from shared.crypto import (
    encrypt_password,
    decrypt_password,
    encrypt_api_key,
    decrypt_api_key,
    generate_key,
)


class TestPasswordEncryption:
    """Tests for password encryption/decryption."""

    def test_encrypt_password_returns_bytes(self):
        """Should return bytes when encrypting a password."""
        password = "my-secure-password"
        encrypted = encrypt_password(password)

        assert isinstance(encrypted, bytes)
        assert encrypted != password.encode()

    def test_decrypt_password_returns_original(self):
        """Should decrypt password back to original string."""
        password = "my-secure-password"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == password
        assert isinstance(decrypted, str)

    def test_encrypt_empty_password(self):
        """Should handle empty password."""
        password = ""
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == password

    def test_encrypt_special_characters(self):
        """Should handle passwords with special characters."""
        password = "p@ssw0rd!#$%^&*(){}[]|\\:;\"'<>,.?/~`"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == password

    def test_encrypt_unicode_characters(self):
        """Should handle passwords with unicode characters."""
        password = "пароль密码パスワード🔒"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        assert decrypted == password

    def test_different_passwords_produce_different_ciphertext(self):
        """Should produce different ciphertext for different passwords."""
        password1 = "password1"
        password2 = "password2"

        encrypted1 = encrypt_password(password1)
        encrypted2 = encrypt_password(password2)

        assert encrypted1 != encrypted2

    def test_same_password_produces_different_ciphertext_each_time(self):
        """Should produce different ciphertext each time (due to IV/nonce)."""
        password = "same-password"

        encrypted1 = encrypt_password(password)
        encrypted2 = encrypt_password(password)

        # Fernet includes timestamp/random IV, so ciphertext differs
        assert encrypted1 != encrypted2

        # But both decrypt to same value
        assert decrypt_password(encrypted1) == password
        assert decrypt_password(encrypted2) == password

    def test_decrypt_invalid_data_raises_error(self):
        """Should raise error when decrypting invalid data."""
        invalid_data = b"not-valid-encrypted-data"

        with pytest.raises(InvalidToken):
            decrypt_password(invalid_data)


class TestApiKeyEncryption:
    """Tests for API key encryption/decryption."""

    def test_api_key_encryption_uses_same_mechanism(self):
        """API key encryption should be an alias for password encryption."""
        assert encrypt_api_key is encrypt_password
        assert decrypt_api_key is decrypt_password

    def test_encrypt_api_key_works(self):
        """Should encrypt and decrypt API keys correctly."""
        api_key = "abcdef1234567890-api-key-token"
        encrypted = encrypt_api_key(api_key)
        decrypted = decrypt_api_key(encrypted)

        assert decrypted == api_key


class TestKeyGeneration:
    """Tests for encryption key generation."""

    def test_generate_key_returns_string(self):
        """Should return a string key."""
        key = generate_key()

        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_is_valid_fernet_key(self):
        """Generated key should be valid for Fernet."""
        key = generate_key()

        # Should not raise an error
        cipher = Fernet(key.encode())
        assert cipher is not None

    def test_generate_key_produces_different_keys(self):
        """Should generate different keys each time."""
        key1 = generate_key()
        key2 = generate_key()

        assert key1 != key2

    def test_generated_key_can_encrypt_decrypt(self):
        """Generated key should work for encryption/decryption."""
        key = generate_key()
        cipher = Fernet(key.encode())

        message = "test message"
        encrypted = cipher.encrypt(message.encode())
        decrypted = cipher.decrypt(encrypted).decode()

        assert decrypted == message
