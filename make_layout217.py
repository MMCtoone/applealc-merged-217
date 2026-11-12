#!/usr/bin/env python3
"""Generate ALC256 layout 217 for Dell Latitude 5175 (ALC3266 / ALC256 family).

layout 217 = layout 21 (Andres ZeroCross, Dell 5570) settings for the headphone
            + the speaker / headphone output chains split into two independent
              HDA paths (the way layout 28 does it)
            + the pin configuration of layout 21 cloned to id 217
"""
import io
import os
import plistlib
import re

NEW_ID = 217
RES = 'alc/Resources/ALC256'
CODEC_ID = 283902550          # ALC256 family (ALC3266 reports this value)
SRC_ID = 21                   # pin configuration donor
PIN_CFG = 'alc/Resources/PinConfigs.kext/Contents/Info.plist'


def load(path):
    raw = open(path, 'rb').read()
    if not raw.startswith(b'<?xml'):
        raw = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
               b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
               b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
               b'<plist version="1.0">\n' + raw + b'\n</plist>\n')
    return plistlib.load(io.BytesIO(raw))


def dump_fragment(obj, path):
    """AppleALC resources are bare XML fragments (no <plist> wrapper)."""
    data = plistlib.dumps(obj, fmt=plistlib.FMT_XML).decode('utf-8')
    m = re.search(r'<(dict|array)>', data)
    body = data[m.start():]
    body = body.rsplit('</plist>', 1)[0].strip()
    open(path, 'w').write(body + '\n')


def main():
    assert os.path.isdir(RES), 'run from repo root after cloning AppleALC into ./alc'

    # 1) layout217: copy of layout21 with only the IDs changed
    lay = load(os.path.join(RES, 'layout21.xml'))
    lay['LayoutID'] = NEW_ID
    lay['PathMapRef'][0]['PathMapID'] = NEW_ID
    dump_fragment(lay, os.path.join(RES, 'layout217.xml'))

    # 2) Platforms217: layout21 paths, output chains separated
    plat = load(os.path.join(RES, 'Platforms21.xml'))
    pm = plat['PathMaps'][0]
    pm['PathMapID'] = NEW_ID
    old = pm['PathMap']
    assert len(old) == 3, 'unexpected Platforms21 path count'
    speaker_chain = old[2][0]   # 0x14 -> 0x02 internal speaker
    hp_chain = old[2][1]        # 0x21 -> 0x03 headphone
    pm['PathMap'] = [old[0], old[1], [speaker_chain], [hp_chain]]
    dump_fragment(plat, os.path.join(RES, 'Platforms217.xml'))

    # 3) register 217 in the codec Info.plist
    info_path = os.path.join(RES, 'Info.plist')
    info = plistlib.load(open(info_path, 'rb'))
    files = info['Files']
    if not any(e.get('Id') == NEW_ID for e in files['Layouts']):
        files['Layouts'].append({
            'Comment': 'Dell 5175 merge: headphone from layout21 (Dell 5570), speaker path split',
            'Id': NEW_ID,
            'Path': 'layout217.xml.zlib',
        })
    if not any(e.get('Id') == NEW_ID for e in files['Platforms']):
        files['Platforms'].append({
            'Comment': 'Dell 5175 merge: layout21 platform with speaker and headphone split into two paths',
            'Id': NEW_ID,
            'Path': 'Platforms217.xml.zlib',
        })
    plistlib.dump(info, open(info_path, 'wb'), fmt=plistlib.FMT_XML, sort_keys=False)
    print('layout217 registry ok:', [e['Path'] for e in files['Layouts'] if e.get('Id') == NEW_ID])
    print('Platforms217 registry ok:', [e['Path'] for e in files['Platforms'] if e.get('Id') == NEW_ID])

    # 4) clone the pin configuration (HDAConfigDefault entry) of layout 21 to 217
    pc = plistlib.load(open(PIN_CFG, 'rb'))
    arr = pc['IOKitPersonalities']['as.vit9696.AppleALC']['HDAConfigDefault']
    donors = [e for e in arr if e.get('LayoutID') == SRC_ID and e.get('CodecID') == CODEC_ID]
    assert donors, 'layout21 pin config for ALC256 not found'
    donor = donors[0]
    exists = any(e.get('LayoutID') == NEW_ID and e.get('CodecID') == CODEC_ID for e in arr)
    if not exists:
        entry = dict(donor)
        entry['LayoutID'] = NEW_ID
        entry['Codec'] = 'Dell 5175 merged 217: pin config of layout 21 (Dell 5570)'
        arr.append(entry)
        plistlib.dump(pc, open(PIN_CFG, 'wb'), fmt=plistlib.FMT_XML, sort_keys=False)
        print('pin config ok: cloned entry for 217, ConfigData bytes =', len(entry['ConfigData']))
    else:
        print('pin config ok: entry for 217 already present')


if __name__ == '__main__':
    main()
