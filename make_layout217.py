#!/usr/bin/env python3
"""Build three ALC256 layout variants for Dell Latitude 5175 (ALC3266).

217 - layout21 settings + Platforms21 with the two output chains split apart
      (what I shipped first; on the machine it produced no audio device at all)
218 - control: byte-for-byte copy of layout21 / Platforms21, only the ids changed
      (must behave exactly like alcid=21: headphone fine, speaker silent)
219 - real merge: layout21 headphone settings + layout28's IntSpeaker block
      (speaker volume + DSP, which layout21 does not define at all)
      paired with Platforms28's three separate paths (mic / speaker / headphone)
      and layout28's pin configuration
"""
import io
import os
import plistlib
import re

RES = 'alc/Resources/ALC256'
CODEC_ID = 283902550
PIN_CFG = 'alc/Resources/PinConfigs.kext/Contents/Info.plist'

VARIANTS = [
    dict(id=217, layout='layout21.xml', platform='SPLIT21', pin=21, comment='split'),
    dict(id=218, layout='layout21.xml', platform='Platforms21.xml', pin=21, comment='control copy of 21'),
    dict(id=219, layout='MERGE28', platform='Platforms28.xml', pin=28, comment='21 headphone + 28 speaker'),
]


def load(path):
    raw = open(path, 'rb').read()
    if not raw.startswith(b'<?xml'):
        raw = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
               b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
               b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
               b'<plist version="1.0">\n' + raw + b'\n</plist>\n')
    return plistlib.load(io.BytesIO(raw))


def dump_fragment(obj, path):
    data = plistlib.dumps(obj, fmt=plistlib.FMT_XML).decode('utf-8')
    m = re.search(r'<(dict|array)>', data)
    body = data[m.start():].rsplit('</plist>', 1)[0].strip()
    open(path, 'w').write(body + '\n')


def split_platform21(plat, new_id):
    """Platforms21: keep both input paths, give speaker and headphone their own path."""
    pm = plat['PathMaps'][0]
    pm['PathMapID'] = new_id
    old = pm['PathMap']
    assert len(old) == 3, 'unexpected Platforms21 path count'
    chains = old[2]
    assert len(chains) == 2, 'expected two chains in the merged entry'
    pm['PathMap'] = [old[0], old[1], [chains[0]], [chains[1]]]
    return plat


def build_layout_merge28(new_id):
    """layout21 headphone/input settings, but layout28's IntSpeaker block."""
    lay = load(os.path.join(RES, 'layout21.xml'))
    ref = lay['PathMapRef'][0]
    ref['PathMapID'] = new_id
    src28 = load(os.path.join(RES, 'layout28.xml'))['PathMapRef'][0]
    ref['IntSpeaker'] = src28['IntSpeaker']
    lay['LayoutID'] = new_id
    return lay


def main():
    assert os.path.isdir(RES), 'run from repo root after cloning AppleALC into ./alc'

    info_path = os.path.join(RES, 'Info.plist')
    info = plistlib.load(open(info_path, 'rb'))
    files = info['Files']

    for v in VARIANTS:
        nid = v['id']

        if v['layout'] == 'MERGE28':
            lay = build_layout_merge28(nid)
        else:
            lay = load(os.path.join(RES, v['layout']))
            lay['LayoutID'] = nid
            lay['PathMapRef'][0]['PathMapID'] = nid
        dump_fragment(lay, os.path.join(RES, f'layout{nid}.xml'))

        if v['platform'] == 'SPLIT21':
            plat = split_platform21(load(os.path.join(RES, 'Platforms21.xml')), nid)
        else:
            plat = load(os.path.join(RES, v['platform']))
            plat['PathMaps'][0]['PathMapID'] = nid
        dump_fragment(plat, os.path.join(RES, f'Platforms{nid}.xml'))

        if not any(e.get('Id') == nid for e in files['Layouts']):
            files['Layouts'].append({'Comment': f'Dell 5175 layout {nid} ({v["comment"]})',
                                     'Id': nid, 'Path': f'layout{nid}.xml.zlib'})
        if not any(e.get('Id') == nid for e in files['Platforms']):
            files['Platforms'].append({'Comment': f'Dell 5175 platform {nid} ({v["comment"]})',
                                       'Id': nid, 'Path': f'Platforms{nid}.xml.zlib'})

    plistlib.dump(info, open(info_path, 'wb'), fmt=plistlib.FMT_XML, sort_keys=False)
    print('registered layouts:', sorted(e['Id'] for e in files['Layouts'] if e.get('Id') in (217, 218, 219)))
    print('registered platforms:', sorted(e['Id'] for e in files['Platforms'] if e.get('Id') in (217, 218, 219)))

    pc = plistlib.load(open(PIN_CFG, 'rb'))
    arr = pc['IOKitPersonalities']['as.vit9696.AppleALC']['HDAConfigDefault']
    for v in VARIANTS:
        nid, src = v['id'], v['pin']
        if any(e.get('LayoutID') == nid and e.get('CodecID') == CODEC_ID for e in arr):
            continue
        donor = [e for e in arr if e.get('LayoutID') == src and e.get('CodecID') == CODEC_ID][0]
        entry = dict(donor)
        entry['LayoutID'] = nid
        entry['Codec'] = f'Dell 5175 merged {nid} ({v["comment"]})'
        arr.append(entry)
        print(f'pin config {nid}: cloned from layout {src}, {len(entry["ConfigData"])} bytes')
    plistlib.dump(pc, open(PIN_CFG, 'wb'), fmt=plistlib.FMT_XML, sort_keys=False)


if __name__ == '__main__':
    main()
