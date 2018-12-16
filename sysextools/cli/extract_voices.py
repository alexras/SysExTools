import os
import json
from typing import List, Optional

from .. import parse, dump


def extract_voices(sysex_file: str, output: str, author: Optional[str],
                   source: Optional[str], debug: Optional[bool] = False) -> List[dict]:
    if not os.path.exists(output):
        raise ValueError(f"Output path ({output}) must exist")

    voices = parse(sysex_file)

    if debug:
        dump(voices, 'debug_output.syx')

    for voice in voices:
        dump([voice], f"{output}/{voice['signature']}.syx")

        if author and 'AUTHOR' not in voice:
            voice['AUTHOR'] = author

        voice['BANK'] = os.path.basename(sysex_file)

        if source:
            voice['SOURCE'] = source

        output_path = f"{output}/{voice['signature']}.json"

        if not os.path.exists(output_path):
            with open(output_path, 'w+') as fp:
                json.dump(voice, fp, indent=2)

    return voices
