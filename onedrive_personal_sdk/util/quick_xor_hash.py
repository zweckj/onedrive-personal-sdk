"""Calculate the QuickXorHash of a given input."""

import struct
import base64

import numpy as np

_SHIFT = 11
_WIDTH_IN_BITS = 160
_WIDTH_IN_BYTES = _WIDTH_IN_BITS // 8  # 20


class QuickXorHash:
    """QuickXorHash implementation."""

    shift = _SHIFT
    witdth_in_bits = _WIDTH_IN_BITS
    block_size = 1

    def __init__(self):
        self._state = np.zeros(_WIDTH_IN_BYTES, dtype=np.uint8)
        self._length_so_far = 0
        self._shift_so_far = 0

    @property
    def digest_size(self) -> int:
        """Get the size of the digest."""
        return _WIDTH_IN_BYTES

    def update(self, data: bytes) -> None:
        """Update the hash with the given data."""
        if not data:
            return

        data_len = len(data)
        width = _WIDTH_IN_BITS
        iterations = min(data_len, width)

        # Vectorized XOR reduction: collapse all bytes into 160 lanes
        arr = np.frombuffer(data, dtype=np.uint8)
        full_blocks = data_len // width
        remainder = data_len % width

        if full_blocks > 0:
            main = arr[: full_blocks * width].reshape(full_blocks, width)
            xored = np.bitwise_xor.reduce(main, axis=0)
            if remainder:
                tail = np.zeros(width, dtype=np.uint8)
                tail[:remainder] = arr[full_blocks * width :]
                xored ^= tail
        else:
            xored = np.zeros(width, dtype=np.uint8)
            xored[:remainder] = arr

        # Vectorized scatter: compute target bit positions for all bytes at once
        positions = (
            self._shift_so_far + np.arange(iterations) * _SHIFT
        ) % width
        byte_idx = (positions >> 3).astype(np.intp)
        bit_off = (positions & 7).astype(np.uint16)

        # Each byte XOR'd at a non-byte-aligned position spans up to 2 bytes
        shifted = xored[:iterations].astype(np.uint16) << bit_off
        low_bytes = (shifted & 0xFF).astype(np.uint8)
        high_bytes = (shifted >> 8).astype(np.uint8)

        next_byte_idx = (byte_idx + 1) % _WIDTH_IN_BYTES

        # Unbuffered XOR accumulation handles duplicate indices correctly
        np.bitwise_xor.at(self._state, byte_idx, low_bytes)
        np.bitwise_xor.at(self._state, next_byte_idx, high_bytes)

        self._shift_so_far = (
            self._shift_so_far + _SHIFT * (data_len % width)
        ) % width
        self._length_so_far += data_len

    def digest(self) -> bytes:
        """Get the digest of the hash."""
        rgb = bytearray(self._state.tobytes())

        # XOR in the total length as a little-endian uint64
        length_bytes = struct.pack("<Q", self._length_so_far)
        offset = _WIDTH_IN_BYTES - len(length_bytes)
        for i in range(len(length_bytes)):
            rgb[offset + i] ^= length_bytes[i]

        return bytes(rgb)

    def hexdigest(self) -> str:
        """Get the hexdigest of the hash."""
        return self.digest().hex()

    def base64(self) -> str:
        """Get the base64 digest of the hash."""
        return base64.b64encode(self.digest()).decode("utf-8")
