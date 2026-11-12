#!/usr/bin/env python3
"""In-place ALC256 fixes for Dell Latitude 5175 (ALC3266). No new layout ids.

Variant A: keep id 21 / platform 21 / pin config 21, only graft layout28's IntSpeaker
           block (DefaultVolume + MuteGPIO + DSP) onto layout21, because layout21's
           IntSpeaker has no DefaultVolume at all, which is why the speaker stays mute.
Variant B: keep id 28 / layout28 / Platforms28, only replace layout 28's pin
           configuration with layout 21's (80 B + 16 B wake verbs instead of 52 B + 4 B).
"""
import io
import os
import plistlib
import re

RES = 'alc/Resources/ALC256'
PIN_CFG = 'alc/Resources/PinConfigs.kext/Contents/Info.plist'
CODEC_ID = 283902550


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


def variant_a():
    lay21 = load(os.path.join(RES, 'layout21.xml'))
    lay28 = load(os.path.join(RES, 'layout28.xml'))
    sp28 = lay28['PathMapRef'][0]['IntSpeaker']
    print('[A] layout21 Headphone before:', list(lay21['PathMapRef'][0]['Headphone'].keys()))
    lay21['PathMapRef'][0]['IntSpeaker'] = sp28
    dump_fragment(lay21, os.path.join(RES, 'layout21.xml'))
    print('[A] layout21 IntSpeaker now:', list(sp28.keys()))


def variant_b():
    cfg = load(PIN_CFG)
    arr = cfg['IOKitPersonalities']['as.vit9696.AppleALC']['HDAConfigDefault']
    e21 = next(e for e in arr if e.get('LayoutID') == 21 and e.get('CodecID') == CODEC_ID)
    e28 = next(e for e in arr if e.get('LayoutID') == 28 and e.get('CodecID') == CODEC_ID)
    print('[B] layout28 pin before: %d B, wake %d B' % (
        len(e28['ConfigData']), len(e28.get('WakeConfigData', b'')))
    e28['ConfigData'] = e21['ConfigData']
    if 'WakeConfigData' in e21:
        e28['WakeConfigData'] = e21['WakeConfigData']
    e28['WakeVerbReinit'] = e21.get('WakeVerbReinit', True)
    e28['AFGLowPowerState'] = e21.get('AFGLowPowerState', b'AwAAAA==')
    e28['Codec'] = 'Dell 5175: layout28 with layout21 pin config'
    plistlib.dump(cfg, open(PIN_CFG, 'wb'), fmt=plistlib.FMT_BINARY)
    print('[B] layout28 pin after: %d B, wake %d B' % (
        len(e28['ConfigData']), len(e28.get('WakeConfigData', b'')))


if __name__ == '__main__':
    variant_a()
    variant_b()
    print('done')
