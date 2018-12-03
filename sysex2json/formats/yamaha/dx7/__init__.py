import bread
import typing

from .spec import sysex_dump_message


def parse_operator(operator: typing.Type[bread.BreadStruct]) -> dict:
    parsed_operator = {
        'envelope_generator': {
            'rates': operator.eg_rates,
            'levels': operator.eg_levels
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


def parse_voice(voice: typing.Type[bread.BreadStruct]) -> dict:
    parsed_voice = {
        'operators': []
    }  # type: dict

    # Operators in the DX7 are listed from OP6 to OP1, so we'll iterate through
    # them backwards

    for op in reversed(voice.operators):
        parsed_voice['operators'].append(parse_operator(op))

    return parsed_voice


def parse(sysex_bytes: bytes) -> list:
    raw_struct = bread.parse(sysex_bytes, sysex_dump_message)

    if raw_struct.format_number == 0:
        parsed_voices = [parse_voice(raw_struct)]
    else:
        parsed_voices = [parse_voice(x) for x in raw_struct.voices]

    return parsed_voices
