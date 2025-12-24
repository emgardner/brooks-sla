# import pytest
# from typing import Optional
# from brooks_sla.hart import (
#     Address,
#     HartFrame,
#     FrameType,
#     hart_checksum
# )
# 
# class HartProtocolError(Exception):
#     """Raised when bytes are syntactically a frame but violate protocol (e.g., bad checksum)."""
# 
# 
# class HartStreamParser:
# 
#     _PREAMBLE = 0
#     _FRAME_TYPE = 1
#     _ADDRESS = 2
#     _CMD = 3
#     _BYTE_COUNT = 4
#     _DATA = 5
#     _CHECKSUM = 6
# 
#     def __init__(self, *, min_preamble: int = 2, max_preamble: int = 32, max_byte_count: int = 255):
#         self._buf = bytearray()
#         self._off = 0  # logical cursor
#         self._min_preamble = min_preamble
#         self._max_preamble = max_preamble
#         self._max_byte_count = max_byte_count
#         self._state = self._PREAMBLE
#         self._preamble_count = 0
#         self._frame_type: Optional[FrameType] = None
#         self._addr_len: Optional[int] = None
#         self._address: Optional[Address] = None
#         self._command: Optional[int] = None
#         self._byte_count: Optional[int] = None
#         self._data = bytearray()
# 
#     # ---------------- buffer primitives ----------------
# 
#     def _available(self) -> int:
#         return len(self._buf) - self._off
# 
#     def _peek(self, idx: int = 0) -> int:
#         return self._buf[self._off + idx]
# 
#     def _take1(self) -> Optional[int]:
#         if self._available() < 1:
#             return None
#         b = self._buf[self._off]
#         self._off += 1
#         return b
# 
#     def _take(self, n: int) -> Optional[bytes]:
#         if self._available() < n:
#             return None
#         out = bytes(self._buf[self._off : self._off + n])
#         self._off += n
#         return out
# 
#     def advance(self, n: int = 1) -> None:
#         """
#         Caller-controlled resync: move cursor forward by n bytes and reset parse state.
#         """
#         if n <= 0:
#             return
#         self._off = min(len(self._buf), self._off + n)
#         self._reset_state()
# 
#     def compact(self) -> None:
#         """
#         Optional maintenance: physically drop consumed bytes.
#         Not required for correctness.
#         """
#         if self._off > 0:
#             del self._buf[: self._off]
#             self._off = 0
# 
#     def _reset_state(self) -> None:
#         self._state = self._PREAMBLE
#         self._preamble_count = 0
#         self._frame_type = None
#         self._addr_len = None
#         self._address = None
#         self._command = None
#         self._byte_count = None
#         self._data.clear()
# 
#     # ---------------- public API ----------------
# 
#     def feed(self, data: bytes) -> Optional[HartFrame]:
#         """
#         Append bytes and attempt to parse and return ONE frame.
#         If more frames are buffered, caller can call feed(b"") or next_frame().
#         """
#         if data:
#             self._buf.extend(data)
#         return self.next_frame()
# 
#     def next_frame(self) -> Optional[HartFrame]:
#         """
#         Attempt to parse and return ONE frame from already-buffered bytes.
#         Returns None if insufficient bytes to complete a frame.
#         Raises HartProtocolError on protocol violations.
#         """
#         while True:
#             if self._state == self._PREAMBLE:
#                 # Consume 0xFF preamble
#                 while self._available() > 0 and self._peek() == 0xFF:
#                     self._take1()
#                     self._preamble_count += 1
#                     if self._preamble_count > self._max_preamble:
#                         raise HartProtocolError("Preamble too long")
# 
#                 # Need more bytes
#                 if self._available() == 0:
#                     return None
# 
#                 # Non-FF encountered
#                 if self._preamble_count < self._min_preamble:
#                     raise HartProtocolError("Insufficient preamble before delimiter")
# 
#                 self._state = self._FRAME_TYPE
#                 continue
# 
#             if self._state == self._FRAME_TYPE:
#                 b = self._take1()
#                 if b is None:
#                     return None
# 
#                 if b not in (ft.value for ft in FrameType):
#                     raise HartProtocolError(f"Invalid delimiter: 0x{b:02X}")
# 
#                 self._frame_type = FrameType(b)
#                 self._addr_len = 5 if (b & 0x80) else 1
#                 self._state = self._ADDRESS
#                 continue
# 
#             if self._state == self._ADDRESS:
#                 assert self._addr_len is not None
#                 addr = self._take(self._addr_len)
#                 if addr is None:
#                     return None
#                 self._address = bytearray(addr)
#                 self._state = self._CMD
#                 continue
# 
#             if self._state == self._CMD:
#                 cmd = self._take1()
#                 if cmd is None:
#                     return None
#                 self._command = cmd
#                 self._state = self._BYTE_COUNT
#                 continue
# 
#             if self._state == self._BYTE_COUNT:
#                 bc = self._take1()
#                 if bc is None:
#                     return None
#                 if bc > self._max_byte_count:
#                     raise HartProtocolError(f"Byte count too large: {bc}")
#                 self._byte_count = bc
#                 self._state = self._DATA
#                 continue
# 
#             if self._state == self._DATA:
#                 assert self._byte_count is not None
#                 data = self._take(self._byte_count)
#                 if data is None:
#                     return None
#                 self._data = bytearray(data)
#                 self._state = self._CHECKSUM
#                 continue
# 
#             if self._state == self._CHECKSUM:
#                 chk = self._take1()
#                 if chk is None:
#                     return None
# 
#                 assert self._frame_type is not None
#                 assert self._command is not None
#                 assert self._byte_count is not None
# 
#                 body = (
#                     int(self._frame_type).to_bytes(1, "big")
#                     + self._address.to_bytes()
#                     + self._command.to_bytes(1, "big")
#                     + self._byte_count.to_bytes(1, "big")
#                     + bytes(self._data)
#                 )
#                 computed = hart_checksum(body)
#                 if computed != chk:
#                     raise HartProtocolError(
#                         f"Invalid checksum (computed 0x{computed:02X}, got 0x{chk:02X})"
#                     )
#                 frame = HartFrame(
#                     frame_type=self._frame_type,
#                     address=bytes(self._address),
#                     command=self._command,
#                     data=bytes(self._data),
#                 )
#                 self._reset_state()
#                 return frame
# 
#             # Should not reach
#             return None
# 
#     def _frame_ready_now(self) -> bool:
#         """
#         True only if a FULL, VALID frame is already buffered and could be returned
#         without reading more bytes.
#         """
#         if self._state != self._CHECKSUM:
#             return False
#         if self._available() < 1:
#             return False
# 
#         # Validate checksum without consuming it
#         assert self._frame_type is not None
#         assert self._command is not None
#         assert self._byte_count is not None
# 
#         chk = self._peek(0)
#         body = (
#             int(self._frame_type).to_bytes(1, "big")
#             + bytes(self._address)
#             + self._command.to_bytes(1, "big")
#             + self._byte_count.to_bytes(1, "big")
#             + bytes(self._data)
#         )
#         return hart_checksum(body) == chk
# 
#     def wants(self) -> int:
#         """
#         Read hint:
#           - returns 0 ONLY if a complete valid frame is already buffered and ready to return
#           - otherwise returns a minimum of 1
#         """
#         if self._frame_ready_now():
#             return 0
# 
#         # internal needed-to-progress (can be 0), but clamp to >=1 for caller reads
#         need = self._needed_internal()
#         return max(1, need)
# 
#     def _needed_internal(self) -> int:
#         """
#         Internal minimum additional bytes to progress parsing.
#         Can be 0 when there are already enough buffered bytes to advance state,
#         but wants() clamps to >=1 unless a frame is ready.
#         """
#         avail = self._available()
# 
#         if self._state == self._PREAMBLE:
#             # If no buffered bytes, ask for enough to plausibly satisfy min preamble
#             if avail == 0:
#                 return max(1, self._min_preamble - self._preamble_count)
# 
#             # If buffered bytes exist, either FFs or delimiter candidate are already there
#             return 0
# 
#         if self._state == self._FRAME_TYPE:
#             return max(1 - avail, 0)
# 
#         if self._state == self._ADDRESS:
#             assert self._addr_len is not None
#             return max(self._addr_len - avail, 0)
# 
#         if self._state == self._CMD:
#             return max(1 - avail, 0)
# 
#         if self._state == self._BYTE_COUNT:
#             return max(1 - avail, 0)
# 
#         if self._state == self._DATA:
#             assert self._byte_count is not None
#             return max(self._byte_count - avail, 0)
# 
#         if self._state == self._CHECKSUM:
#             return max(1 - avail, 0)
# 
#         return 1
# 
# 
# def build_packet(
#     *,
#     preamble_len: int,
#     frame_type: FrameType,
#     address: bytes,
#     command: int,
#     data: bytes,
# ) -> bytes:
#     bc = len(data)
#     body = (
#         int(frame_type).to_bytes(1, "big")
#         + address
#         + command.to_bytes(1, "big")
#         + bc.to_bytes(1, "big")
#         + data
#     )
#     chk = hart_checksum(body)
#     return (b"\xFF" * preamble_len) + body + bytes([chk])
# 
# 
# def test_wants_preamble_minimums():
#     parser = HartStreamParser()
#     assert parser.wants() == 2
# 
#     parser.feed(bytes([0xFF]))
#     assert parser.wants() == 1
# 
#     parser.feed(bytes([0xFF]))
#     assert parser.wants() == 1  # needs delimiter
# 
#     with pytest.raises(HartProtocolError):
#         parser = HartStreamParser()
#         parser.feed(bytes([0xFF for _ in range(0, 33)]))  # > max preamble
# 
#     with pytest.raises(HartProtocolError):
#         parser = HartStreamParser()
#         parser.feed(bytes([0xFF, 0xFE]))  # insufficient preamble
# 
#     with pytest.raises(HartProtocolError):
#         parser = HartStreamParser()
#         parser.feed(bytes([0xFE]))  # non-FF immediately
# 
# 
# def test_delimiter_and_address_length_wants():
#     # short delimiter -> address length 1 (after delimiter consumed, wants() == 1)
#     parser = HartStreamParser()
#     parser.feed(bytes([0xFF, 0xFF, FrameType.SHORT_ACK_FRAME]))
#     assert parser.wants() == 1  # wants 1 address byte
# 
#     parser = HartStreamParser()
#     parser.feed(bytes([0xFF, 0xFF, FrameType.SHORT_STX_FRAME]))
#     assert parser.wants() == 1
# 
#     with pytest.raises(HartProtocolError):
#         parser = HartStreamParser()
#         parser.feed(bytes([0xFF, 0xFF, 0x01]))  # invalid delimiter
# 
#     # long delimiter -> address length 5
#     parser = HartStreamParser()
#     parser.feed(bytes([0xFF, 0xFF, FrameType.LONG_ACK_FRAME]))
#     assert parser.wants() == 5
# 
#     parser = HartStreamParser()
#     parser.feed(bytes([0xFF, 0xFF, FrameType.LONG_STX_FRAME]))
#     assert parser.wants() == 5
# 
# 
# def test_incremental_parse_short_frame():
#     parser = HartStreamParser()
# 
#     pkt = build_packet(
#         preamble_len=2,
#         frame_type=FrameType.SHORT_ACK_FRAME,
#         address=b"\x80",   # arbitrary
#         command=0x01,
#         data=b"\xAA\xBB",
#     )
# 
#     # Feed it byte-by-byte; only final byte should produce a frame.
#     out = None
#     for i, b in enumerate(pkt):
#         out = parser.feed(bytes([b]))
#         if i < len(pkt) - 1:
#             assert out is None
# 
#     assert isinstance(out, HartFrame)
#     assert out.frame_type == FrameType.SHORT_ACK_FRAME
#     assert out.address == b"\x80"
#     assert out.command == 0x01
#     assert out.byte_count == 2
#     assert out.data == b"\xAA\xBB"
# 
# 
# def test_checksum_failure_raises():
#     parser = HartStreamParser()
# 
#     good = build_packet(
#         preamble_len=2,
#         frame_type=FrameType.SHORT_ACK_FRAME,
#         address=b"\x80",
#         command=0x01,
#         data=b"\xAA\xBB",
#     )
#     bad = bytearray(good)
#     bad[-1] ^= 0xFF  # corrupt checksum
# 
#     with pytest.raises(HartProtocolError):
#         parser.feed(bytes(bad))
# 
# 
# def test_two_frames_buffered_wants_zero_then_next_frame():
#     parser = HartStreamParser()
# 
#     pkt1 = build_packet(
#         preamble_len=2,
#         frame_type=FrameType.SHORT_ACK_FRAME,
#         address=b"\x80",
#         command=0x01,
#         data=b"\x01",
#     )
#     pkt2 = build_packet(
#         preamble_len=2,
#         frame_type=FrameType.SHORT_ACK_FRAME,
#         address=b"\x81",
#         command=0x02,
#         data=b"\x02\x03",
#     )
# 
#     # Feed both at once. feed() returns only one frame (by design).
#     f1 = parser.feed(pkt1 + pkt2)
#     assert f1 is not None
#     assert f1.command == 0x01
#     assert f1.data == b"\x01"
# 
#     # Second frame is already fully buffered and valid -> wants() should be 0
#     assert parser.wants() == 0
# 
#     # Caller can pull without reading more
#     f2 = parser.next_frame()
#     assert f2 is not None
#     assert f2.command == 0x02
#     assert f2.data == b"\x02\x03"
# 
#     # Now nothing ready; wants() should be >= 1
#     assert parser.wants() >= 1
# 
# 
# def test_long_address_frame_parse():
#     parser = HartStreamParser()
# 
#     pkt = build_packet(
#         preamble_len=3,
#         frame_type=FrameType.LONG_ACK_FRAME,
#         address=b"\xC1\x10\x01\x02\x03",  # 5 bytes
#         command=0x09,
#         data=b"",
#     )
# 
#     f = parser.feed(pkt)
#     assert f is not None
#     assert f.frame_type == FrameType.LONG_ACK_FRAME
#     assert f.address == b"\xC1\x10\x01\x02\x03"
#     assert f.command == 0x09
#     assert f.byte_count == 0
#     assert f.data == b""
