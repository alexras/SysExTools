import bread as b
# Format taken from https://github.com/asb2m10/dexed/blob/master/Documentation/sysex-format.txt

NAME_ENCODING = 'utf-8'

enums = {
    'curves': {
        0: '-LIN',
        1: '-EXP',
        2: '+EXP',
        3: '+LIN'
    },
    'osc_mode': {
        0: 'ratio',
        1: 'fixed'
    },
    'waveforms': {
        0: 'triangle',
        1: 'saw down',
        2: 'saw up',
        3: 'square',
        4: 'sine',
        # Some sysex parsers (like the one in Dexed) seem to accept 6 and 7 as a
        # valid value for S&H, even though the spec's value is 5
        (5, 6, 7): 'sample and hold'
    }
}

raw_operator = [
    ('eg_rates', b.array(4, b.uint8)),
    ('eg_levels', b.array(4, b.uint8)),
    ('keyboard_level_scaling_break_point', b.uint8),  # C3 = 0x27
    ('keyboard_level_scaling_left_depth', b.uint8),
    ('keyboard_level_scaling_right_depth', b.uint8),
    ('keyboard_level_scaling_left_curve', b.enum(8, enums['curves'])),
    ('keyboard_level_scaling_right_curve', b.enum(8, enums['curves'])),
    ('keyboard_rate_scaling', b.uint8),
    ('amp_mod_sensitivity', b.uint8),
    ('key_velocity_sensitivity', b.uint8),
    ('output_level', b.uint8),
    ('osc_mode', b.enum(8, enums['osc_mode'])),
    ('osc_frequency_coarse', b.uint8),
    ('osc_frequency_fine', b.uint8),
    ('osc_detune', b.uint8, {'offset': -7})  # Range from -7 to 7
]

raw_voice = [
    ('operators', b.array(6, raw_operator)),
    ('pitch_eg_rates', b.array(4, b.uint8)),
    ('pitch_eg_levels', b.array(4, b.uint8)),
    ('algorithm', b.uint8, {'offset': 1}),
    ('feedback', b.uint8),
    ('oscillator_sync', b.uint8),
    ('lfo_speed', b.uint8),
    ('lfo_delay', b.uint8),
    ('lfo_pitch_mod_depth', b.uint8),
    ('lfo_amp_mod_depth', b.uint8),
    ('lfo_sync', b.uint8),
    ('lfo_waveform', b.enum(8, enums['waveforms'])),
    ('pitch_mod_sensitivity', b.uint8),
    ('transpose', b.uint8),
    ('name', b.string(10, NAME_ENCODING))
]

compressed_operator = [
    ('eg_rates', b.array(4, b.uint8)),
    ('eg_levels', b.array(4, b.uint8)),
    ('keyboard_level_scaling_break_point', b.uint8),  # C3 = 0x27
    ('keyboard_level_scaling_left_depth', b.uint8),
    ('keyboard_level_scaling_right_depth', b.uint8),
    b.padding(4),
    # Byte 11
    ('keyboard_level_scaling_right_curve', b.enum(2, enums['curves'])),
    ('keyboard_level_scaling_left_curve', b.enum(2, enums['curves'])),
    # Byte 12
    b.padding(1),
    ('osc_detune', b.intX(4), {'offset': -7}),
    ('keyboard_rate_scaling', b.intX(3)),
    # Byte 13
    b.padding(3),
    ('key_velocity_sensitivity', b.intX(3)),
    ('amp_mod_sensitivity', b.intX(2)),
    # Byte 14
    ('output_level', b.uint8),
    # Byte 15
    b.padding(2),
    ('osc_frequency_coarse', b.intX(5)),
    ('osc_mode', b.enum(1, enums['osc_mode'])),
    # Byte 16
    ('osc_frequency_fine', b.uint8)
]

compressed_voice = [
    ('operators', b.array(6, compressed_operator)),
    ('pitch_eg_rates', b.array(4, b.uint8)),
    ('pitch_eg_levels', b.array(4, b.uint8)),
    # Byte 110
    b.padding(3),
    ('algorithm', b.intX(5), {'offset': 1}),
    # Byte 111
    b.padding(4),
    ('oscillator_sync', b.intX(1)),
    ('feedback', b.intX(3)),
    # Byte 112
    ('lfo_speed', b.uint8),
    ('lfo_delay', b.uint8),
    ('lfo_pitch_mod_depth', b.uint8),
    ('lfo_amp_mod_depth', b.uint8),
    # Byte 116

    # This deviates from the diagram slightly, but matches what I'm seeing in
    # practice - pitch mod sensitivity is specified as 2 bits, but given that
    # its value is allowed to vary from 0-7, that can't possibly be the
    # case. This has the happy side-effect of shifting the LFO waveform over by
    # a bit, which allows us to parse waveforms properly.
    b.padding(1),
    ('pitch_mod_sensitivity', b.intX(3)),
    ('lfo_waveform', b.enum(3, enums['waveforms'])),
    ('lfo_sync', b.intX(1)),
    # Byte 117
    ('transpose', b.uint8),
    ('name', b.string(10, NAME_ENCODING))
]

voice_bank = [
    ('voices', b.array(32, compressed_voice))
]

sysex_dump_message = [
    b.padding(1),
    ('sub_status', b.intX(3)),
    ('channel_number', b.intX(4), {'offset': 1}),
    ('format_number', b.uint8),  # 0 = 1 voice, 9 = 32 voices
    # The byte count for DX7 sysex dumps is actually stored as a 7-bit MSB and
    # a 7-bit LSB. So a byte count value of 0x011b means that the dump contains
    # a single, 155-byte uncompressed voice, while a byte count value of 0x2000
    # means that the dump contains 32 128-byte compressed voices.
    ('byte_count', b.uint16, {'endianness': b.BIG_ENDIAN}),
    (b.CONDITIONAL, "format_number", {
        0: raw_voice,
        9: voice_bank
    }),
    ('checksum', b.uint8)  # masked 2's complement of sum of data bytes
]
