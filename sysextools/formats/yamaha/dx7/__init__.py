from copy import deepcopy
from hashlib import sha1
import json
import typing

import bread

from .spec import sysex_dump_message


def parse_operator(operator: typing.Type[bread.BreadStruct]) -> dict:
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
                'coarse': operator.osc_frequency_course
            },
            'mode': operator.osc_mode
        },
        'amp_mod_sensitivity': operator.amp_mod_sensitivity,
        'output_level': operator.output_level
    }  # type: dict

    return parsed_operator


def compute_signature(voice):
    voice_copy = deepcopy(voice)
    del voice_copy['name']

    return sha1(json.dumps(voice_copy, sort_keys=True).encode('utf-8')).hexdigest()


def parse_voice(voice: typing.Type[bread.BreadStruct]) -> dict:
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
        'name': voice.name.strip(),
        'MANUFACTURER': 'yamaha',
        'MODEL': 'dx7'
    }  # type: dict

    # Operators in the DX7 are listed from OP6 to OP1, so we'll iterate through
    # them backwards

    for op in reversed(voice.operators):
        parsed_voice['operators'].append(parse_operator(op))

    parsed_voice['signature'] = compute_signature(parsed_voice)

    return parsed_voice


def load_parsed_voice_into_struct(voice: typing.Union[dict, list], struct: typing.Type[bread.BreadStruct]):
    pass


def parse(sysex_bytes: bytes) -> list:
    raw_struct = bread.parse(sysex_bytes, sysex_dump_message)

    if raw_struct.format_number == 0:
        parsed_voices = [parse_voice(raw_struct)]
    else:
        parsed_voices = [parse_voice(x) for x in raw_struct.voices]

    return parsed_voices


def dump(sysex_json: typing.Union[dict, list]) -> bytes:
    if type(sysex_json) == dict:
        # Single voice
        single_voice_sysex = bread.new(sysex_dump_message)
        single_voice_sysex.format_number = 0

        load_parsed_voice_into_struct(sysex_json, single_voice_sysex)

        return bread.write(single_voice_sysex, sysex_dump_message)
    else:
        multivoice_sysex = bread.new(sysex_dump_message)
        multivoice_sysex.format_number = 9

        for i, voice in enumerate(sysex_json):
            load_parsed_voice_into_struct(sysex_json[i], multivoice_sysex.voices[i])

        return bread.write(multivoice_sysex, sysex_dump_message)
