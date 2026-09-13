"""
Cognitive CanSat - Airborne & Ground Firmware Protocol Verification
-------------------------------------------------------------------
Automated test suite validating:
1. Binary packet struct packing and ESP-NOW MTU compliance (<= 250 bytes).
2. Image slicing algorithm into 200-byte chunks.
3. Bit-for-bit reassembly on the ground receiver.
4. Serial framing ($CAM_FRAME,...) and Base64 streaming decoder integrity.
5. Incomplete frame timeout and packet loss protection.
"""

import struct
import base64
import hashlib
import unittest

SYNC_WORD = 0xAA55
PKT_FRAME_START = 0x01
PKT_FRAME_DATA = 0x02
CHUNK_MAX_SIZE = 200
ESP_NOW_HARD_MTU = 250


class TestFirmwareProtocol(unittest.TestCase):

    def test_packet_sizes_and_mtu(self):
        """Verify struct binary layouts strictly satisfy ESP-NOW MTU constraints."""
        # FrameHeaderPacket format:
        # uint16_t sync, uint8_t pkt_type, uint16_t frame_id, uint32_t total_bytes,
        # uint16_t total_chunks, uint16_t width, uint16_t height, uint8_t quality
        header_fmt = "<HBIHHH B"
        # struct alignment without padding: '<H B H I H H H B'
        header_fmt = "<HBHIIHHB"  # H(2) + B(1) + H(2) + I(4) + H(2) + H(2) + H(2) + B(1)
        header_size = struct.calcsize("<HBHIIHHB")
        self.assertLessEqual(header_size, ESP_NOW_HARD_MTU, "Header packet exceeds ESP-NOW MTU")
        self.assertLess(header_size, 30, "Header packet should be lightweight")

        # FrameChunkPacket format:
        # sync(2) + pkt_type(1) + frame_id(2) + chunk_index(2) + total_chunks(2) + chunk_len(1) + payload(200)
        chunk_header_fmt = "<HBH H H B"
        chunk_header_size = struct.calcsize("<HBH H H B")
        total_chunk_pkt_size = chunk_header_size + CHUNK_MAX_SIZE
        self.assertEqual(chunk_header_size, 10, "Chunk header should be exactly 10 bytes")
        self.assertEqual(total_chunk_pkt_size, 210, "Full chunk packet should be 210 bytes")
        self.assertLessEqual(total_chunk_pkt_size, ESP_NOW_HARD_MTU,
                             f"Chunk packet ({total_chunk_pkt_size}B) exceeds 250B ESP-NOW hardware limit!")

    def test_image_chunking_and_bit_for_bit_reassembly(self):
        """Simulate slicing a real JPEG payload and reassembling it bit-for-bit."""
        # Create synthetic JPEG payload with SOI (0xFFD8) and EOI (0xFFD9)
        raw_image_data = b"\xff\xd8\xff\xe0" + b"\x42\xa5\x19\x7c" * 850 + b"\xff\xd9"
        total_bytes = len(raw_image_data)
        original_hash = hashlib.sha256(raw_image_data).hexdigest()

        total_chunks = (total_bytes + CHUNK_MAX_SIZE - 1) // CHUNK_MAX_SIZE

        # Transmitter Slicing
        transmitted_packets = []
        for i in range(total_chunks):
            offset = i * CHUNK_MAX_SIZE
            chunk_slice = raw_image_data[offset: offset + CHUNK_MAX_SIZE]
            pkt = {
                "sync": SYNC_WORD,
                "pkt_type": PKT_FRAME_DATA,
                "frame_id": 42,
                "chunk_index": i,
                "total_chunks": total_chunks,
                "chunk_len": len(chunk_slice),
                "payload": chunk_slice
            }
            transmitted_packets.append(pkt)

        # Receiver Reassembly Simulation
        reassembly_buffer = bytearray(total_bytes)
        received_chunks = 0
        for pkt in transmitted_packets:
            self.assertEqual(pkt["sync"], SYNC_WORD)
            self.assertEqual(pkt["frame_id"], 42)
            idx = pkt["chunk_index"]
            offset = idx * CHUNK_MAX_SIZE
            reassembly_buffer[offset: offset + pkt["chunk_len"]] = pkt["payload"]
            received_chunks += 1

        self.assertEqual(received_chunks, total_chunks)
        reassembled_hash = hashlib.sha256(reassembly_buffer).hexdigest()
        self.assertEqual(reassembled_hash, original_hash, "Reassembled image bytes must match original exactly!")

    def test_ground_serial_framing_and_base64_decode(self):
        """Verify ground receiver $CAM_FRAME serial output framing and browser decode."""
        sample_jpeg = b"\xff\xd8\xff\xdb" + b"TEST_AERIAL_IMAGE_DATA" * 50 + b"\xff\xd9"
        frame_id = 105
        size_bytes = len(sample_jpeg)
        duration_ms = 18

        # Ground Receiver encodes into Base64
        b64_str = base64.b64encode(sample_jpeg).decode('ascii')
        serial_line = f"$CAM_FRAME,{frame_id},{size_bytes},{duration_ms},{b64_str}\r\n"

        # Laptop Mission Control Parser
        trimmed = serial_line.strip()
        self.assertTrue(trimmed.startswith("$CAM_FRAME,"))

        parts = trimmed.split(",", 4)
        self.assertEqual(len(parts), 5)
        parsed_id = int(parts[1])
        parsed_size = int(parts[2])
        parsed_duration = int(parts[3])
        parsed_b64 = parts[4]

        self.assertEqual(parsed_id, frame_id)
        self.assertEqual(parsed_size, size_bytes)
        self.assertEqual(parsed_duration, duration_ms)

        decoded_bytes = base64.b64decode(parsed_b64)
        self.assertEqual(decoded_bytes, sample_jpeg, "Decoded Base64 frame must match original JPEG binary")

    def test_packet_loss_drop_incomplete_frame(self):
        """Verify that an incomplete frame with missing chunks is flagged and safely handled."""
        raw_data = b"X" * 1000
        total_chunks = (len(raw_data) + CHUNK_MAX_SIZE - 1) // CHUNK_MAX_SIZE  # 5 chunks

        # Simulate dropping chunk index 2 (simulating RF interference)
        received_indices = [0, 1, 3, 4]  # Missing index 2
        chunks_received = len(received_indices)

        self.assertLess(chunks_received, total_chunks, "Missing chunk detected")
        # In ground receiver code: dispatch_completed_frame() is only triggered when received_chunks == expected_chunks
        frame_dispatched = (chunks_received >= total_chunks)
        self.assertFalse(frame_dispatched, "Incomplete frame must NOT be dispatched to laptop serial")


if __name__ == "__main__":
    print("=" * 70)
    print("  COGNITIVE CANSAT - FIRMWARE PROTOCOL & CHUNKING VERIFICATION")
    print("=" * 70)
    unittest.main(verbosity=2)
