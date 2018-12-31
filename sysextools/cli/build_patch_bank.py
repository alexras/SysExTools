import itertools
import json
import logging
import os
from typing import List, Optional

from .. import parse, dump

logging.basicConfig(filename='build_patch_bank.log', level=logging.DEBUG)


def process_sysex(sysex_file: os.DirEntry, output_dir: str, author: Optional[str], source: Optional[str]) -> List[dict]:
    patch_list = []

    logging.info(f"Extracting voices from {sysex_file.name}")

    try:
        voices = parse(sysex_file.path)
    except Exception as e:
        logging.error(f"Failed to parse {sysex_file.path} - {str(e)}")
        return []

    for voice in voices:
        if author and 'AUTHOR' not in voice:
            voice['AUTHOR'] = author

        voice['BANK'] = sysex_file.name

        if source:
            voice['SOURCE'] = source

        signature = voice['SIGNATURE']
        output_subdir = os.path.join(output_dir, signature[:2])

        output_sysex = os.path.join(output_subdir, f"{signature}.syx")
        output_json = os.path.join(output_subdir, f"{signature}.json")

        if os.path.exists(output_sysex):
            logging.info(f"Instrument {voice['NAME']} is a duplicate ({voice['SIGNATURE']}); skipping")
            continue

        logging.info(f"Writing {voice['NAME']} ({voice['SIGNATURE']})")

        dump([voice], output_sysex)

        with open(output_json, 'w+') as fp:
            json.dump(voice, fp)

        patch_list.append({
            'name': voice['NAME'],
            'author': voice['AUTHOR'],
            'signature': voice['SIGNATURE'],
            'manufacturer': voice['MANUFACTURER'],
            'model': voice['MODEL'],
            'source_bank': voice['BANK']
        })

    return patch_list


def build_patch_bank(sysex_files_dir: str, output_dir: str):
    patch_list_file = os.path.join(output_dir, 'patch_list.json')

    patch_list = []  # type: List[dict]

    if os.path.exists(patch_list_file):
        with open(patch_list_file, 'r') as fp:
            patch_list = json.load(fp)

    builtins = []
    user_built = []

    # Build subdirectories for each of the prefixes so we can keep directories relatively small
    for i in range(256):
        try:
            os.mkdir(os.path.join(output_dir, "{:02x}".format(i)))
        except FileExistsError:
            pass

    # Partition folders into built-ins and user-constructed sysex files, so
    # that we can scan the built-ins first
    for sysex_dir in os.scandir(sysex_files_dir):
        if sysex_dir.name == '_Skip' or sysex_dir.name.startswith('.'):
            continue

        if sysex_dir.name.startswith('BUILTIN_'):
            builtins.append(sysex_dir)
        else:
            user_built.append(sysex_dir)

    for sysex_dir in itertools.chain(builtins, user_built):
        if sysex_dir.is_dir():
            if sysex_dir == '_Unknown':
                author = None
            else:
                author = sysex_dir.name.replace('BUILTIN_', '')

            logging.info(f"Scanning sysex files for author '{author}'")

            source_path = os.path.join(sysex_dir.path, 'source.txt')
            source = None

            if os.path.exists(source_path):
                with open(source_path, 'r') as fp:
                    source = fp.read().strip()

            for f in os.scandir(sysex_dir.path):
                if f.name.lower().endswith('.syx'):
                    patch_list.extend(process_sysex(f, output_dir, source=source, author=author))


    with open(patch_list_file, 'w+') as fp:
        json.dump(patch_list, fp, indent=2)
