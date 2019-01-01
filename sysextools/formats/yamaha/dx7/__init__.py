from copy import deepcopy
from hashlib import sha1
import json
from typing import cast, Type, Union

import bread

from .spec import sysex_dump_message

# Single-voice SysEx messages for the DX7 expand all 155 parameters into a
# parameter per byte. Multi-voice messages compact each voice into 128 bytes
# and have 32 voices per message. There's also a four-byte header and a
# checksum byte
SYSEX_HEADER_SIZE = 4
SINGLE_VOICE_SYSEX_LENGTH = 155 + SYSEX_HEADER_SIZE + 1
MULTI_VOICE_SYSEX_LENGTH = 32 * 128 + SYSEX_HEADER_SIZE + 1


def parse_operator(operator: Type[bread.BreadStruct]) -> dict:
    parsed_operator = {
        'envelope_generator': {
            'rates': operator.eg_rates.as_native(),
            'levels': operator.eg_levels.as_native()
        },
        'keyboard': {
            'level_scaling': {
                'break_point': operator.keyboard_level_scaling_break_point,
                'left_depth': operator.keyboard_level_scaling_left_depth,
                'left_curve': operator.keyboard_level_scaling_left_curve,
                'right_depth': operator.keyboard_level_scaling_right_depth,
                'right_curve': operator.keyboard_level_scaling_right_curve
            },
            'rate_scaling': operator.keyboard_rate_scaling,
            'velocity_sensitivity': operator.key_velocity_sensitivity
        },
        'oscillator': {
            'detune': operator.osc_detune,
            'frequency': {
                'fine': operator.osc_frequency_fine,
                'coarse': operator.osc_frequency_coarse
            },
            'mode': operator.osc_mode
        },
        'amp_mod_sensitivity': operator.amp_mod_sensitivity,
        'output_level': operator.output_level
    }  # type: dict

    return parsed_operator


def load_parsed_operator_into_struct(operator: dict, struct: Type[bread.BreadStruct]):
    struct.eg_rates = operator['envelope_generator']['rates']
    struct.eg_levels = operator['envelope_generator']['levels']
    struct.keyboard_level_scaling_break_point = operator['keyboard']['level_scaling']['break_point']
    struct.keyboard_level_scaling_left_depth = operator['keyboard']['level_scaling']['left_depth']
    struct.keyboard_level_scaling_right_depth = operator['keyboard']['level_scaling']['right_depth']
    struct.keyboard_level_scaling_left_curve = operator['keyboard']['level_scaling']['left_curve']
    struct.keyboard_level_scaling_right_curve = operator['keyboard']['level_scaling']['right_curve']
    struct.keyboard_rate_scaling = operator['keyboard']['rate_scaling']
    struct.key_velocity_sensitivity = operator['keyboard']['velocity_sensitivity']
    struct.osc_detune = operator['oscillator']['detune']
    struct.osc_frequency_fine = operator['oscillator']['frequency']['fine']
    struct.osc_frequency_coarse = operator['oscillator']['frequency']['coarse']
    struct.osc_mode = operator['oscillator']['mode']
    struct.amp_mod_sensitivity = operator['amp_mod_sensitivity']
    struct.output_level = operator['output_level']


def compute_signature(voice):
    voice_copy = deepcopy(voice)
    del voice_copy['NAME']

    return sha1(json.dumps(voice_copy, sort_keys=True).encode('utf-8')).hexdigest()


def parse_voice(voice: Type[bread.BreadStruct]) -> dict:
    parsed_voice = {
        'operators': [],
        'pitch_envelope_generator': {
            'rates': voice.pitch_eg_rates.as_native(),
            'levels': voice.pitch_eg_levels.as_native()
        },
        'algorithm': voice.algorithm,
        'feedback': voice.feedback,
        'oscillator_key_sync': bool(voice.oscillator_sync),
        'lfo': {
            'speed': voice.lfo_speed,
            'delay': voice.lfo_delay,
            'pitch_mod_depth': voice.lfo_pitch_mod_depth,
            'amp_mod_depth': voice.lfo_amp_mod_depth,
            'key_sync': bool(voice.lfo_sync),
            'waveform': voice.lfo_waveform
        },
        'pitch_mod_sensitivity': voice.pitch_mod_sensitivity,
        'transpose': voice.transpose,
        'NAME': voice.name.strip(),
        'MANUFACTURER': 'yamaha',
        'MODEL': 'dx7'
    }  # type: dict

    # Operators in the DX7 are listed from OP6 to OP1, so we'll iterate through
    # them backwards

    for op in reversed(voice.operators):
        parsed_voice['operators'].append(parse_operator(op))

    parsed_voice['SIGNATURE'] = compute_signature(parsed_voice)

    return parsed_voice


def load_parsed_voice_into_struct(voice: dict, struct: Type[bread.BreadStruct]):
    for parsed_operator, struct_operator in zip(reversed(voice['operators']), struct.operators):
        load_parsed_operator_into_struct(parsed_operator, struct_operator)

    struct.pitch_eg_rates = voice['pitch_envelope_generator']['rates']
    struct.pitch_eg_levels = voice['pitch_envelope_generator']['levels']
    struct.algorithm = voice['algorithm']
    struct.feedback = voice['feedback']
    struct.oscillator_sync = voice['oscillator_key_sync']
    struct.lfo_speed = voice['lfo']['speed']
    struct.lfo_delay = voice['lfo']['delay']
    struct.lfo_pitch_mod_depth = voice['lfo']['pitch_mod_depth']
    struct.lfo_amp_mod_depth = voice['lfo']['amp_mod_depth']
    struct.lfo_sync = voice['lfo']['key_sync']
    struct.lfo_waveform = voice['lfo']['waveform']
    struct.pitch_mod_sensitivity = voice['pitch_mod_sensitivity']
    struct.transpose = voice['transpose']
    struct.name = voice['NAME'].ljust(len(struct.name))


def parse(sysex_bytes: bytes) -> list:
    raw_struct = bread.parse(sysex_bytes, sysex_dump_message)

    if raw_struct.format_number == 0:
        parsed_voices = [parse_voice(raw_struct)]
    else:
        parsed_voices = [parse_voice(x) for x in raw_struct.voices]

    return parsed_voices


def compute_checksum(data: bytes, offset_start: int = SYSEX_HEADER_SIZE, offset_end: int = 1):
    # To compute the checksum for DX7 SysEx messages:
    #
    # 1. compute the sum of the message's data bytes
    # 2. mask that number so that it's 7 bits long
    # 3. compute the masked number's 2s complement, and mask the result so it's 7 bits long

    if offset_end == 0:
        off_end = None
    else:
        off_end = -(offset_end)

    return (~(sum(data[offset_start:off_end]) & 0x7f) & 0x7f) + 1


def dump(sysex_json: Union[dict, list]) -> bytes:
    if type(sysex_json) == dict:
        # Single voice
        single_voice_blank_data = bytearray(SINGLE_VOICE_SYSEX_LENGTH)
        single_voice_blank_data[1] = 1
        sysex = bread.new(sysex_dump_message, data=single_voice_blank_data)
        sysex.format_number = 0
        sysex.byte_count = 0x011b

        load_parsed_voice_into_struct(cast(dict, sysex_json), sysex)
    else:
        multivoice_blank_data = bytearray(MULTI_VOICE_SYSEX_LENGTH)
        multivoice_blank_data[1] = 9
        sysex = bread.new(sysex_dump_message, data=multivoice_blank_data)
        sysex.format_number = 9
        sysex.byte_count = 0x2000

        for i, voice in enumerate(sysex_json):
            load_parsed_voice_into_struct(sysex_json[i], sysex.voices[i])

    parsed_data = bread.write(sysex, sysex_dump_message)
    sysex.checksum = compute_checksum(parsed_data)

    return bread.write(sysex, sysex_dump_message)


def add_headers_and_footers(bank_bytes: bytes) -> bytes:
    output_bytes = bytes([0x00])

    if len(bank_bytes) == 32 * 128:
        output_bytes += bytes([0x09, 0x20, 0x00])
    elif len(bank_bytes) == 155:
        output_bytes += bytes([0x00, 0x01, 0x1b])
    else:
        raise ValueError('Bank of size %d bytes not supported' % (len(bank_bytes)))

    output_bytes += bank_bytes

    output_bytes += bytes([compute_checksum(bank_bytes, offset_start=0, offset_end=0)])

    return output_bytes
