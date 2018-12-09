import os
from typing import Any, Callable, cast, Dict, List, Tuple, Union  # noqa


from .constants import SYSEX_START_BYTE, SYSEX_END_BYTE, EXTENDED_MANUFACTURER_ID_BYTE
from .formats import yamaha
from .errors import ParseError, NotSupportedError

_PARSERS = {
    yamaha.MANUFACTURER_ID: yamaha.parse
}  # type: Dict[Tuple[int,...], Callable]

# This is a map from strings to modules, but typing annotations don't seem to
# know about modules, so I'm annotating it as having "any" as its value type
# TODO: is there a more elegant way of doing this?
_FORMATS = {
    'yamaha': yamaha
}  # type: Dict[str, Any]


def byte_to_int(byte) -> int:
    return int.from_bytes(byte, byteorder='little')


def int_to_byte(i: int) -> bytes:
    return i.to_bytes(1, byteorder='little')


def parse(sysex_file, **kwargs) -> List[Dict[str, Any]]:
    with open(sysex_file, 'rb') as fp:
        # Check that the sysex message looks basically valid (i.e. that it starts
        # and ends with the expected SysEx control bytes)

        first_byte = byte_to_int(fp.read(1))

        if first_byte != SYSEX_START_BYTE:
            raise ParseError('Expected SysEx message to start with 0xf0')

        fp.seek(-1, os.SEEK_END)
        last_byte = byte_to_int(fp.read(1))

        if last_byte != SYSEX_END_BYTE:
            raise ParseError('Expected SysEx message to end in 0xf7')

        # Extract the manufacturer ID (which is either 1 or 3 bytes long,
        # depending on which manufacturer we're dealing with
        fp.seek(1, os.SEEK_SET)

        manufacturer_id = (byte_to_int(fp.read(1)),)  # type: Tuple[int,...]

        if manufacturer_id == EXTENDED_MANUFACTURER_ID_BYTE:
            manufacturer_id += tuple(map(byte_to_int, fp.read(2)))

        if manufacturer_id not in _PARSERS:
            raise NotSupportedError("Manufacturer ID for this SysEx (%s) not supported" %
                                    (manufacturer_id))

        # Read the non-control SysEx bytes and pass them to the appropriate parser
        sysex_bytes = fp.read(os.path.getsize(sysex_file) - len(manufacturer_id) - 2)

        return _PARSERS[manufacturer_id](sysex_bytes, **kwargs)


def dump(parsed_sysex: List[Dict[str, Any]], sysex_file: str):
    manufacturer = parsed_sysex[0]['MANUFACTURER']

    format_lib = _FORMATS[manufacturer]

    with open(sysex_file, 'wb') as fp:
        fp.write(SYSEX_START_BYTE.to_bytes(1, byteorder='little'))

        for id_chunk in format_lib.MANUFACTURER_ID:
            fp.write(id_chunk.to_bytes(1, byteorder='little'))

        dumped_bytes = format_lib.dump(parsed_sysex)
        fp.write(dumped_bytes)

        fp.write(SYSEX_END_BYTE.to_bytes(1, byteorder='little'))
        fp.flush()
