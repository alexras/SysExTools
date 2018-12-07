from . import dx7

MANUFACTURER_ID = (0x43,)


def parse(sysex_bytes: bytes, model_hint: str = None) -> list:
    # TODO: actually try to guess the model from sysex
    return dx7.parse(sysex_bytes)
