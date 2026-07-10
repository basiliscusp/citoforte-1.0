#!/usr/bin/env bash
set -euo pipefail

echo "[1/7] USB devices"
lsusb || true

echo
echo "[2/7] USB tree"
lsusb -t || true

echo
echo "[3/7] ALSA cards"
cat /proc/asound/cards || true

echo
echo "[4/7] ALSA device nodes"
ls /dev/snd || true

echo
echo "[5/7] MIDI ports"
aseqdump -l || true

echo
echo "[6/7] Raw MIDI"
amidi -l || true

echo
echo "[7/7] Kernel tail (USB/MIDI)"
dmesg | tail -n 50 || true

echo
echo "Check completato."
