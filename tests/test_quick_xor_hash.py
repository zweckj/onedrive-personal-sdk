"""Tests for QuickXorHash implementation."""

import os

import pytest

from onedrive_personal_sdk.util.quick_xor_hash import QuickXorHash


class TestQuickXorHashKnownValues:
    """Test QuickXorHash with known reference values."""

    def test_empty(self):
        h = QuickXorHash()
        assert h.base64() == "AAAAAAAAAAAAAAAAAAAAAAAAAAA="

    def test_hello_world(self):
        h = QuickXorHash()
        h.update(b"Hello, World!")
        assert h.base64() == "SCgDG9jwBhaA4ApvnQMbyBACAAA="

    def test_exactly_160_bytes(self):
        h = QuickXorHash()
        h.update(bytes(range(160)))
        assert h.base64() == "/+EGLlnQi0dVs5OErXWhEnz5wg4="

    def test_large_data(self):
        h = QuickXorHash()
        h.update(bytes(range(256)) * 10)
        assert h.base64() == "AAAAAAAAAAAAAAAAAAoAAAAAAAA="

    def test_single_byte(self):
        h = QuickXorHash()
        h.update(b"A")
        assert h.base64() == "QQAAAAAAAAAAAAAAAQAAAAAAAAA="

    def test_all_zeros(self):
        h = QuickXorHash()
        h.update(b"\x00" * 500)
        assert h.base64() == "AAAAAAAAAAAAAAAA9AEAAAAAAAA="

    def test_52_bytes(self):
        h = QuickXorHash()
        h.update(b"test" * 13)
        assert h.base64() == "h20E9t562EZg763H3jY6X3SsbqM="

    def test_320_bytes(self):
        h = QuickXorHash()
        h.update(bytes(range(256)) + bytes(range(64)))
        assert h.base64() == "HOc4x3nOc56znOUs5zjNaY5znOM="


class TestQuickXorHashMultiUpdate:
    """Test that multi-update produces the same result as single update."""

    def test_multi_update_matches_single(self):
        h1 = QuickXorHash()
        h1.update(b"Hello, World!")

        h2 = QuickXorHash()
        h2.update(b"Hello, ")
        h2.update(b"World!")

        assert h1.base64() == h2.base64()

    def test_chunked_matches_single(self):
        data = os.urandom(1024 * 1024)

        h1 = QuickXorHash()
        h1.update(data)

        h2 = QuickXorHash()
        chunk_size = 5120
        for i in range(0, len(data), chunk_size):
            h2.update(data[i : i + chunk_size])

        assert h1.base64() == h2.base64()

    def test_byte_by_byte(self):
        data = b"The quick brown fox jumps over the lazy dog"

        h1 = QuickXorHash()
        h1.update(data)

        h2 = QuickXorHash()
        for byte in data:
            h2.update(bytes([byte]))

        assert h1.base64() == h2.base64()


class TestQuickXorHashEdgeCases:
    """Test edge cases."""

    def test_empty_update(self):
        h = QuickXorHash()
        h.update(b"")
        assert h.base64() == "AAAAAAAAAAAAAAAAAAAAAAAAAAA="

    def test_none_like_empty(self):
        h1 = QuickXorHash()
        h2 = QuickXorHash()
        h2.update(b"")
        assert h1.base64() == h2.base64()

    def test_digest_size(self):
        h = QuickXorHash()
        assert h.digest_size == 20
        assert len(h.digest()) == 20

    def test_hexdigest(self):
        h = QuickXorHash()
        h.update(b"Hello, World!")
        assert h.hexdigest() == h.digest().hex()

    def test_various_chunk_sizes(self):
        """Test various chunk sizes to exercise different code paths."""
        data = os.urandom(10000)
        h_ref = QuickXorHash()
        h_ref.update(data)

        for chunk_size in [1, 7, 13, 100, 159, 160, 161, 320, 5000]:
            h = QuickXorHash()
            for i in range(0, len(data), chunk_size):
                h.update(data[i : i + chunk_size])
            assert h.base64() == h_ref.base64(), f"Mismatch with chunk_size={chunk_size}"

    def test_memoryview_input(self):
        """Test that memoryview input works correctly."""
        data = bytearray(b"Hello, World!")
        h1 = QuickXorHash()
        h1.update(bytes(data))

        h2 = QuickXorHash()
        h2.update(memoryview(data))

        assert h1.base64() == h2.base64()
