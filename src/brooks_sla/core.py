from enum import IntEnum
from pydantic import BaseModel, Field, model_validator
from enum import IntEnum


class FlowRateUnit(IntEnum):
    CUBIC_FEET_PER_MIN = 15
    GALLONS_PER_MIN = 16
    LITERS_PER_MIN = 17
    IMP_GALLONS_PER_MIN = 18
    CUBIC_METERS_PER_HOUR = 19
    GALLONS_PER_SEC = 22
    LITERS_PER_SEC = 24
    CUBIC_FEET_PER_SEC = 26
    CUBIC_FEET_PER_DAY = 27
    CUBIC_METERS_PER_SEC = 28
    CUBIC_METERS_PER_DAY = 29
    IMP_GALLONS_PER_HOUR = 30
    IMP_GALLONS_PER_DAY = 31
    PERCENT = 57
    GRAMS_PER_SEC = 70
    GRAMS_PER_MIN = 71
    GRAMS_PER_HOUR = 72
    KG_PER_SEC = 73
    KG_PER_MIN = 74
    KG_PER_HOUR = 75
    KG_PER_DAY = 76
    LBS_PER_SEC = 80
    LBS_PER_MIN = 81
    LBS_PER_HOUR = 82
    LBS_PER_DAY = 83
    CUBIC_FEET_PER_HOUR = 130
    CUBIC_METERS_PER_MIN = 131
    BARRELS_PER_SEC = 132
    BARRELS_PER_MIN = 133
    BARRELS_PER_HOUR = 134
    BARRELS_PER_DAY = 135
    GALLONS_PER_HOUR = 136
    IMP_GALLONS_PER_SEC = 137
    LITERS_PER_HOUR = 138
    ML_PER_SEC = 170
    ML_PER_MIN = 171
    ML_PER_HOUR = 172
    ML_PER_DAY = 173
    LITERS_PER_DAY = 174
    CUBIC_INCHES_PER_SEC = 200
    CUBIC_INCHES_PER_MIN = 201
    CUBIC_INCHES_PER_HOUR = 202
    CUBIC_INCHES_PER_DAY = 203
    GALLONS_PER_DAY = 235
    CC_PER_MIN = 240
    CC_PER_SEC = 241
    CC_PER_HOUR = 242
    CC_PER_DAY = 248
    GRAMS_PER_DAY = 243
    OUNCES_PER_SEC = 244
    OUNCES_PER_MIN = 245
    OUNCES_PER_HOUR = 246
    OUNCES_PER_DAY = 247
    NOT_USED = 250

class FlowReference(IntEnum):
    NORMAL = 0
    STANDARD = 1
    CALIBRATION = 2

class PressureUnit(IntEnum):
    IN_H2O = 1
    IN_HG = 2
    FT_H2O = 3

    PSI_A = 5
    PSI_B = 6

    BAR = 7
    MILLIBAR = 8

    PASCAL = 11
    KILOPASCAL = 12
    TORR = 13
    STANDARD_ATMOSPHERE = 14

    CM_H2O = 227
    GR_PER_CM2 = 228
    MM_HG = 229
    MILLITORR = 230
    KG_PER_CM2_A = 231
    ATM = 232
    FT_H2O_ALT = 233
    IN_H2O_ALT = 234
    IN_HG_ALT = 235
    TORR_ALT = 236
    MBAR_ALT = 237
    BAR_ALT = 238
    PASCAL_ALT = 239
    KPA_ALT = 240
    COUNTS = 241
    PERCENT = 242
    KG_PER_CM2_B = 243
    MILLITORR_ALT = 244
    MM_HG_ALT = 245
    GR_PER_CM2_ALT = 246

class TemperatureUnit(IntEnum):
    CELSIUS = 32
    FAHRENHEIT = 33
    KELVIN = 35


class DensityUnit(IntEnum):
    GRAMS_PER_CM3 = 91
    KG_PER_M3 = 92
    LBS_PER_GAL = 93
    LBS_PER_FT3 = 94
    GRAMS_PER_ML = 95
    KG_PER_L = 96
    GRAMS_PER_L = 97
    LBS_PER_IN3 = 98


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

class CommandErrorId(IntEnum):
    NON = 0
    UNDEFINED = 1
    INVALID_SELECTION = 2
    PARAMETER_TOO_LARGE = 3
    PARAMETER_TOO_SMALL = 4
    INCORRECT_BYTE_COUNT = 5
    TRANSMITTER_SPECIFIC = 6
    WRITE_PROTECT_MODE = 7
    COMMAND_ERROR_8 = 8
    COMMAND_ERROR_9 = 9
    COMMAND_ERROR_10 = 10
    COMMAND_ERROR_11 = 11
    COMMAND_ERROR_12 = 12
    COMMAND_ERROR_13 = 13
    COMMAND_ERROR_14 = 14
    COMMAND_ERROR_15 = 15
    ACCESS_RESTRICTED = 16
    DEVICE_BUSY = 32
    COMMAND_NOT_IMPLEMENTED = 64

class DeviceStatus(BaseModel):
    comms: CommunicationStatus
    command: CommandStatus

    @classmethod
    def from_bytes(cls, first: int, second: int) -> "DeviceStatus":
        return cls(
            comms=CommunicationStatus(raw=first),
            command=CommandStatus(raw=second),
        )

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
