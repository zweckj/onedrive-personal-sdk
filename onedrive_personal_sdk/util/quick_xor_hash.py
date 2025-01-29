"""Calculate the QuickXorHash of a given input."""

import struct
import base64


class QuickXorHash:
    """QuickXorHash implementation."""

    bits_in_last_cell = 32
    shift = 11
    threshold = 600
    witdth_in_bits = 160
    block_size = 1

    def __init__(self):
        self._data = [0] * ((self.witdth_in_bits - 1) // 64 + 1)
        self._length_so_far = 0
        self._shift_so_far = 0

    @property
    def digest_size(self) -> int:
        """Get the size of the digest."""
        return (self.witdth_in_bits - 1) // 8 + 1

    def update(self, data: bytes) -> None:
        """Update the hash with the given data."""
        current_shift = self._shift_so_far

        vector_array_index = current_shift // 64
        vector_offset = current_shift % 64
        iterations = min(len(data), self.witdth_in_bits)

        for i in range(iterations):
            is_last_cell = vector_array_index == len(self._data) - 1
            bits_in_vector_cell = self.bits_in_last_cell if is_last_cell else 64

            if vector_offset <= bits_in_vector_cell - 8:
                for j in range(i, len(data), self.witdth_in_bits):
                    self._data[vector_array_index] ^= data[j] << vector_offset
            else:
                index1 = vector_array_index
                index2 = 0 if is_last_cell else vector_array_index + 1
                low = bits_in_vector_cell - vector_offset

                xored_byte = 0
                for j in range(i, len(data), self.witdth_in_bits):
                    xored_byte ^= data[j]

                self._data[index1] ^= xored_byte << vector_offset
                self._data[index2] ^= xored_byte >> low

            vector_offset += self.shift
            while vector_offset >= bits_in_vector_cell:
                vector_array_index = 0 if is_last_cell else vector_array_index + 1
                vector_offset -= bits_in_vector_cell

        self._shift_so_far = (
            self._shift_so_far + self.shift * (len(data) % self.witdth_in_bits)
        ) % self.witdth_in_bits
        self._length_so_far += len(data)

    def digest(self) -> bytes:
        """Get the digest of the hash."""

        # Ensure the buffer is large enough
        rgb = bytearray((self.witdth_in_bits + 7) // 8)

        for i in range(len(self._data) - 1):
            struct.pack_into("<Q", rgb, i * 8, self._data[i] % (1 << 64))

        # Ensure the buffer is large enough to accommodate the last element
        last_index = (len(self._data) - 1) * 8
        if last_index + 8 > len(rgb):
            rgb.extend([0] * (last_index + 8 - len(rgb)))

        struct.pack_into("<Q", rgb, last_index, self._data[-1] % (1 << 64))

        length_bytes = struct.pack("<Q", self._length_so_far)
        for i, byte in enumerate(length_bytes):
            rgb[(self.witdth_in_bits // 8) - len(length_bytes) + i] ^= byte

        # Ensure the buffer is large enough to accommodate the length bytes
        if len(rgb) < (self.witdth_in_bits // 8):
            rgb.extend([0] * ((self.witdth_in_bits // 8) - len(rgb)))

        # only use 20 bytes
        return bytes(rgb)[:20]

    def hexdigest(self) -> str:
        """Get the hexdigest of the hash."""
        return self.digest().hex()

    def base64(self) -> str:
        """Get the base64 digest of the hash."""
        return base64.b64encode(self.digest()).decode("utf-8")
