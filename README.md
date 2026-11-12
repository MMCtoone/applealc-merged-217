# AppleALC layout 217 — Dell Latitude 5175 (ALC3266)

Merged layout built from upstream AppleALC so that **headphone and internal speaker work at the same time**.

## Why

In `Resources/ALC256`:

* `Platforms21.xml` packs **two output chains into a single `path` element**:
  `[0x14 -> 0x02]` (internal speaker) and `[0x21 -> 0x03]` (headphone).
  AppleHDA builds only one output chain per path entry, so with layout 21 the speaker is lost (`alcid=21`: headphone fine, no speaker).
* `Platforms28.xml` keeps them as **two separate paths** (speaker present), but layout 28 comes from an **Asus X555UJ**, so its headphone amp/delay settings are wrong for a Dell (`alcid=28`: speaker fine, headphone clipping + inverted channels).

The node IDs are identical in both files, so the two verified-good halves can be merged.

## What layout 217 is

| part | source |
|---|---|
| `LayoutID` / `PathMapID` | 217 (new) |
| headphone settings | `layout21.xml` (Dell 5570, verified working) unchanged |
| internal speaker settings | `layout21.xml` unchanged |
| platform paths | `Platforms21.xml` inputs unchanged, output chains split: `0x14->0x02` and `0x21->0x03` as two independent paths |

`make_layout217.py` performs this transformation mechanically against a fresh `acidanthera/AppleALC` clone.

## Build

Pushing to `main` or running the `Build merged AppleALC` workflow builds the kext on a GitHub macOS runner and publishes the zip as a release asset. No local Xcode needed, and it does not depend on the local network of the target machine.

## Install

1. Replace `EFI/OC/Kexts/AppleALC.kext` with the built kext.
2. Set `alcid=217` in `boot-args` (and `layout-id = 0xD9` if you keep the device property).
3. Reboot; check `kextstat | grep -i applealc`, then confirm both "Internal Speakers" and "Headphones" appear in Sound settings.

## Fallback

If the speaker is still silent at 217, the codec needs extra EAPD/amp handling; a Linux codec dump (`cat /proc/asound/card0/codec#0`) is then required to fix layout 217.
