from typing import Any, Dict, List
from . import dx7
from ...errors import NotSupportedError

MANUFACTURER_ID = (0x43,)


def parse(sysex_bytes: bytes, model_hint: str = None) -> list:
    # TODO: actually try to guess the model from sysex
    return dx7.parse(sysex_bytes)


def dump(parsed_sysex: List[Dict[str, Any]]) -> bytes:
    model = parsed_sysex[0]['MODEL']

    if model == 'dx7':
        return dx7.dump(parsed_sysex)
    else:
        raise NotSupportedError()
