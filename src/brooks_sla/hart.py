from pydantic import BaseModel
from enum import IntEnum
import math
from typing import List, Optional, Union


class FrameType(IntEnum):
    SHORT_STX_FRAME = 0x02
    SHORT_ACK_FRAME = 0x06
    LONG_STX_FRAME = 0x82
    LONG_ACK_FRAME = 0x86

class ShortAddress(BaseModel):
    primary_master: bool = True
    slave: int

    def to_bytes(self) -> bytes:
        value = 0 
        if self.primary_master:
            value = value | (1 << 7)
        value |= self.slave
        return bytes([value])



class LongAddress(BaseModel):
    primary_master: bool = True
    slave_burst: bool = False
    mfg_id: int = 10
    device_type: int = 100
    identification_number: int = 0
    broadcast: bool = False

    def to_bytes(self) -> bytes:
        byte0 = 0
        if self.primary_master:
            byte0 |= (1 << 7)
        if self.slave_burst:
            byte0 |= (1 << 6)
        mfg_mask = b"00111111"
        byte0 |= int(mfg_mask, 2) & self.mfg_id 
        if self.broadcast:
            return bytes([byte0, self.device_type, 0, 0, 0])
        else:
            return bytes([byte0, self.device_type] + list(self.identification_number.to_bytes(3, byteorder="big", signed=False)))

Address = Union[ShortAddress, LongAddress]


class HartFrame(BaseModel):
    preamble_char: int = 0xFF
    preamble_chars: int = 5 # Minimum 2 suggested 5
    frame_type: FrameType
    address: Address
    command: int
    data: Optional[bytes]

    def to_packet(self) -> bytes:
        if self.preamble_chars < 2:
            raise ValueError("preamble_chars must be >= 2")
        if isinstance(self.address, ShortAddress) and self.frame_type != FrameType.SHORT_STX_FRAME:
            raise ValueError("ShortAddress requires SHORT_STX_FRAME for requests")
        if isinstance(self.address, LongAddress) and self.frame_type != FrameType.LONG_STX_FRAME:
            raise ValueError("LongAddress requires LONG_STX_FRAME for requests")
        preamble = bytes([self.preamble_char]) * self.preamble_chars
        frame_type_b = bytes([int(self.frame_type)])
        address_b = self.address.to_bytes()
        payload = b"" if self.data is None else self.data
        byte_count_b = len(payload).to_bytes(1, byteorder="big", signed=False)
        body = frame_type_b + address_b + bytes([self.command]) + byte_count_b + payload
        chk = HartFrame.chksum(body)

        return preamble + body + chk

    @staticmethod
    def chksum(data: bytes) -> bytes:
        lrc = 0
        for byte in data:
            lrc ^= byte
        return bytes([lrc])

def pack_ascii(data: str) -> bytes:
    chars = [c.encode() for c in string]  # type: ignore
    out = 0
    for i, c in zip(range(8), [ord(c) & 0b0011_1111 for c in chars][::-1]):
        out |= c << (i * 6)
    return out.to_bytes(math.ceil((len(data) * 6) / 8), "big")

def hart_checksum(data: bytes) -> int:
    chk = 0
    for b in data:
        chk ^= b
    return chk
