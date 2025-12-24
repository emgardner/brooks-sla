from typing import Optional
from pydantic import BaseModel
import serial_asyncio
from brooks_sla.core import Command, FlowRateUnit, FlowReference, TemperatureUnit
import asyncio
import hart_protocol
import struct

class FlowReading(BaseModel):
    reading: float
    units: FlowRateUnit

class FlowSetting(BaseModel):
    percent: float
    units: FlowRateUnit
    value: float

class FlowRange(BaseModel):
    units: FlowRateUnit
    value: float

class TempReading(BaseModel):
    reading: float
    units: TemperatureUnit

class HartResponseFrame(BaseModel):
    command: int
    bytecount: int
    address: int
    data: bytes
    full_response: bytes
    device_status: bytes
    response_code: bytes


class BrooksError(Exception):
    """Base Brooks Exception Code"""

class BrooksSLA:

    def __init__(self, tag: str, port: str, baudrate: int = 19200, address: Optional[int] = None) -> None:
        self._raw_tag = tag
        self._tag = hart_protocol.tools.pack_ascii(tag[-8:])
        self._port = port
        self._baudrate = baudrate
        self._parity = serial_asyncio.serial.PARITY_ODD
        self._stop_bits = serial_asyncio.serial.STOPBITS_ONE
        self._temp_units: Optional[TemperatureUnit] = None
        self._flow_units: Optional[FlowRateUnit] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._address: Optional[int] = None
        self._lock = asyncio.Lock()
        self._timeout = 1.0

    async def connect(self) -> None:
        reader, writer = await serial_asyncio.open_serial_connection(
            url=self._port,
            baudrate=self._baudrate,
        )
        self._reader = reader
        self._writer = writer

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    def _ensure_connected(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        if self._reader is None or self._writer is None:
            raise RuntimeError("Not connected. Call await connect() first.")
        return self._reader, self._writer

    async def flush_input(self) -> None:
        reader, _ = self._ensure_connected()
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(1024), timeout=0.05)
            except asyncio.TimeoutError:
                return
            if not chunk:
                return

    async def transaction(self, data: bytes) ->  HartResponseFrame:
        reader, writer = self._ensure_connected()
        async with self._lock:
            writer.write(data)
            unpacker = hart_protocol.Unpacker(reader, on_error="raise")
            async with asyncio.Timeout(self._timeout):
                for msg in unpacker:
                    return HartResponseFrame(
                        command=msg.command,
                        bytecount=msg.bytecount,
                        address=msg.address,
                        data=msg.data,
                        full_response=msg.full_response,
                        device_status=msg.device_status,
                        response_code=msg.response_code
                    )
        raise BrooksError("No Response From Device")


    async def get_address(self) -> None:
        data = hart_protocol.universal.read_unique_identifier_associated_with_tag(self._tag)
        response = await self.transaction(data)
        device_id = int.from_bytes(response.data[9:12], "big")
        self._address = device_id


    def construct_command(self, command: int, data: Optional[bytes] = None) -> bytes:
        if self._address == None:

            return hart_protocol.tools.pack_command(0, command, data)
        else:
            return hart_protocol.tools.pack_command(self._address, command, data)

    async def read_flow(self) -> FlowReading:
        response = await self.transaction(self.construct_command(Command.READ_PRIMARY_VARIABLE))
        units, variable = struct.unpack_from(">Bf", response.data)
        return FlowReading(
            units=FlowRateUnit(units),
            reading=variable
        )

    async def set_flow(self, units: FlowRateUnit, flow: float) -> FlowSetting:
        await self.select_units(units)
        data = struct.pack(">Bf", FlowRateUnit.NOT_USED.value, flow)
        response = await self.transaction(self.construct_command(Command.WRITE_SETPOINT_PERCENT_OR_SELECTED_UNITS, data))
        _, percent, units, variable = struct.unpack_from(">BfBf", response.data)
        return FlowSetting(
            percent=percent,
            units=FlowRateUnit(units),
            value=variable
        )

    async def set_flow_percent(self, flow: float) -> FlowSetting:
        if flow < 0.0 or flow > 100.0:
            raise BrooksError("Flow Percent must be 0.0-100.0")

        data = struct.pack(">Bf", FlowRateUnit.PERCENT.value, flow)
        response = await self.transaction(self.construct_command(Command.WRITE_SETPOINT_PERCENT_OR_SELECTED_UNITS, data))
        _, percent, units, variable = struct.unpack_from(">BfBf", response.data)
        return FlowSetting(
            percent=percent,
            units=FlowRateUnit(units),
            value=variable
        )

    async def select_units(self, units: FlowRateUnit, reference: FlowReference = FlowReference.CALIBRATION) -> None:
        data = struct.pack(">BB", reference.value, units.value)
        response = await self.transaction(self.construct_command(Command.SELECT_FLOW_UNIT, data))
        _, flow_units = struct.unpack(">BB", response.data)
        self._flow_units = FlowRateUnit(flow_units)

    async def master_reset(self) -> None:
        await self.transaction(self.construct_command(Command.PERFORM_MASTER_RESET))

    async def read_flow_range(self, gas: int = 1) -> FlowRange:
        if gas < 0 or gas > 6:
            raise BrooksError("Gas Must be between 0-6")
        data = struct.pack(">B",gas)
        response = await self.transaction(self.construct_command(Command.READ_FULL_SCALE_FLOW_RANGE, data))
        units, variable = struct.unpack_from(">Bf", response.data)
        return FlowRange(units=FlowRateUnit(units), value=variable)


