from pydantic import BaseModel, Field, model_validator
from enum import IntEnum
from typing import Literal, List, Union


class CommunicationStatus(BaseModel):
    raw: int = Field(..., ge=0, le=0xFF)

    communication_error: bool = False  # bit 7
    parity_error: bool = False         # bit 6
    overrun_error: bool = False        # bit 5
    framing_error: bool = False        # bit 4
    checksum_error: bool = False       # bit 3
    reserved: bool = False             # bit 2
    rx_buffer_overflow: bool = False   # bit 1
    undefined: bool = False             # bit 0

    @model_validator(mode="after")
    def decode_bits(self):
        v = self.raw
        self.communication_error = bool(v & 0x80)
        self.parity_error = bool(v & 0x40)
        self.overrun_error = bool(v & 0x20)
        self.framing_error = bool(v & 0x10)
        self.checksum_error = bool(v & 0x08)
        self.reserved = bool(v & 0x04)
        self.rx_buffer_overflow = bool(v & 0x02)
        self.undefined = bool(v & 0x01)
        return self

class CommandStatus(BaseModel):
    raw: int = Field(..., ge=0, le=0xFF)
    device_malfunction: bool = False  # bit 7
    error_code: int = 0               # bits 6–0
    configuration_changed: bool = False
    cold_start: bool = False
    more_status_available: bool = False
    primary_var_fixed: bool = False
    primary_var_saturated: bool = False
    non_primary_out_of_range: bool = False
    primary_var_out_of_range: bool = False

    @model_validator(mode="after")
    def decode(self):
        v = self.raw
        self.device_malfunction = bool(v & 0x80)
        self.error_code = v & 0x7F
        self.configuration_changed = self.error_code == 6
        self.cold_start = self.error_code == 5
        self.more_status_available = self.error_code == 4
        self.primary_var_fixed = self.error_code == 3
        self.primary_var_saturated = self.error_code == 2
        self.non_primary_out_of_range = self.error_code == 1
        self.primary_var_out_of_range = self.error_code == 0
        return self

class FrameType(IntEnum):
    SHORT_STX_FRAME = 0x02
    SHORT_ACK_FRAME = 0x06
    LONG_STX_FRAME = 0x82
    LONG_ACK_FRAME = 0x86

class ShortAddressByte(BaseModel):
    primary_master: bool = True
    slave: int

    def to_byte_array(self) -> List[int]:
        value = 0 
        if self.primary_master:
            value = value | (1 << 7)
        value |= self.slave
        return [value]



class LongAddressByte(BaseModel):
    primary_master: bool = True
    slave_burst: bool = False
    mfg_id: int = 10
    device_type: int = 100
    identification_number: int = 0
    broadcast: bool = False

    def to_byte_array(self) -> List[int]:
        byte0 = 0
        if self.primary_master:
            byte0 |= (1 << 7)
        if self.slave_burst:
            byte0 |= (1 << 6)
        mfg_mask = b"00111111"
        byte0 |= int(mfg_mask, 2) & self.mfg_id 
        if self.broadcast:
            return [byte0, self.device_type, 0, 0, 0]
        else:
            return [byte0, self.device_type] + list(self.identification_number.to_bytes(3, byteorder="big", signed=False))

AddressByte = Union[ShortAddressByte, LongAddressByte]

class Command(IntEnum):
    READ_UNIQUE_IDENTIFIER = 0
    READ_PRIMARY_VARIABLE = 1
    READ_PRIMARY_VARIABLE_CURRENT_AND_PERCENT_RANGE = 2
    READ_ALL_DYNAMIC_VARIABLES_AND_CURRENT = 3
    WRITE_POLLING_ADDRESS = 6
    MANUAL_RS485_COMMUNICATIONS = 9
    READ_UNIQUE_IDENTIFIER_ASSOCIATED_WITH_TAG = 11
    READ_MESSAGE = 12
    READ_TAG_DESCRIPTOR_DATE = 13
    READ_PRIMARY_VARIABLE_SENSOR_INFORMATION = 14
    READ_OUTPUT_INFORMATION = 15
    READ_FINAL_ASSEMBLY_NUMBER = 16
    WRITE_MESSAGE = 17
    WRITE_TAG_DESCRIPTOR_DATE = 18
    WRITE_FINAL_ASSEMBLY_NUMBER = 19
    SET_PRIMARY_VARIABLE_LOWER_RANGE_VALUE = 37
    RESET_CONFIGURATION_CHANGED_FLAG = 38
    EEPROM_CONTROL = 39
    PERFORM_MASTER_RESET = 42
    READ_ADDITIONAL_TRANSMITTER_STATUS = 48
    READ_DYNAMIC_VARIABLE_ASSIGNMENTS = 50
    WRITE_NUMBER_OF_RESPONSE_PREAMBLES = 59
    WRITE_ANALOG_OUTPUT_ADDITIONAL_DAMPING = 64
    WRITE_DEVICE_UNIQUE_ID = 122
    SELECT_BAUDRATE = 123
    ENTER_EXIT_WRITE_PROTECT_MODE = 128  # NON-PUBLIC
    WRITE_MANUFACTURER_DEVICE_TYPE_CODE = 130
    READ_SERIAL_NUMBER = 131
    READ_MODEL_NUMBER = 132
    READ_FIRMWARE_REVISION = 134
    READ_GAS_NAME = 150
    READ_GAS_DENSITY_FLOW_REF_AND_FLOW_RANGE = 151
    READ_FULL_SCALE_FLOW_RANGE = 152
    READ_FULL_SCALE_PRESSURE_RANGE = 159
    READ_CALIBRATED_PRESSURE_RANGE = 179
    READ_STANDARD_TEMPERATURE_AND_PRESSURE = 190
    WRITE_STANDARD_TEMPERATURE_AND_PRESSURE = 191
    READ_OPERATIONAL_SETTINGS_PRESSURE = 192
    READ_OPERATIONAL_SETTINGS_FLOW = 193
    SELECT_PRESSURE_APPLICATION_NUMBER = 194
    SELECT_GAS_CALIBRATION_FLOW_NUMBER = 195
    SELECT_FLOW_UNIT = 196
    SELECT_TEMPERATURE_UNIT = 197
    SELECT_PRESSURE_UNIT = 198
    SELECT_PRESSURE_FLOW_CONTROL = 199
    READ_SETPOINT_SETTINGS = 215
    SELECT_SETPOINT_SOURCE = 216
    SELECT_SOFTSTART = 218
    WRITE_LINEAR_SOFTSTART_RAMP_VALUE = 219
    READ_PID_CONTROLLER_VALUES = 220
    WRITE_PID_CONTROLLER_VALUES = 221
    READ_VALVE_RANGE_AND_OFFSET = 222
    WRITE_VALVE_RANGE_AND_OFFSET = 223
    GET_VALVE_OVERRIDE_STATUS = 230
    SET_VALVE_OVERRIDE_STATUS = 231
    READ_SETPOINT_PERCENT_AND_SELECTED_UNITS = 235
    WRITE_SETPOINT_PERCENT_OR_SELECTED_UNITS = 236
    READ_VALVE_CONTROL_VALUE = 237
    READ_TOTALIZER_STATUS = 240
    SET_TOTALIZER_CONTROL = 241
    READ_TOTALIZER_VALUE_AND_UNIT = 242
    READ_HIGH_LOW_PRESSURE_ALARM = 243
    WRITE_HIGH_LOW_PRESSURE_ALARM = 244
    READ_ALARM_ENABLE_SETTING = 245
    WRITE_ALARM_ENABLE_SETTING = 246
    READ_HIGH_LOW_FLOW_ALARM = 247
    WRITE_HIGH_LOW_FLOW_ALARM = 248
    CHANGE_USER_PASSWORD = 250

class Frame(BaseModel):
    preamble_char: int = 0xFF
    preamble_chars: int = 5 # Minimum 2 suffested 5
    frame_type: FrameType
    address: AddressByte
    tag: List[int] # 6 digits
    command: Command
    data: bytearray

    def to_packet(self) -> bytearray:
        preamble = [self.preamble_char for _ in range(0, self.preamble_chars)]
        frame_type = [self.frame_type.value]
        address_bytes = []
        if isinstance(ShortAddressByte, self.address):

        else:



