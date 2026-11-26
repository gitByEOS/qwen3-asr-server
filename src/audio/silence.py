"""扫静音得到原子段，再装箱成贴近 30 秒的组。"""

from __future__ import annotations

import math
import os
import struct
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

FRAME_SEC = 0.02
SILENCE_RMS = 300
MIN_SILENCE_SEC = 0.35
TARGET_SEC = 30.0


@dataclass(frozen=True)
class SilenceSpan:
    start: float
    end: float


@dataclass(frozen=True)
class Atom:
    start: float
    end: float


def merge_silences(
    spans: list[SilenceSpan],
    min_silence_sec: float = MIN_SILENCE_SEC,
) -> list[SilenceSpan]:
    kept = [span for span in spans if span.end - span.start >= min_silence_sec]
    kept.sort(key=lambda span: span.start)
    merged: list[SilenceSpan] = []
    for span in kept:
        if not merged:
            merged.append(span)
            continue
        previous = merged[-1]
        gap = span.start - previous.end
        if gap <= 0:
            merged[-1] = SilenceSpan(previous.start, max(previous.end, span.end))
            continue
        merged.append(span)
    return merged


def atoms_from_silences(duration: float, silences: list[SilenceSpan]) -> list[Atom]:
    atoms: list[Atom] = []
    cursor = 0.0
    for silence in silences:
        if silence.start - cursor > 0.01:
            atoms.append(Atom(cursor, silence.start))
        cursor = max(cursor, silence.end)
    if duration - cursor > 0.01:
        atoms.append(Atom(cursor, duration))
    return atoms


def pack_atoms(atoms: list[Atom], target: float = TARGET_SEC) -> list[tuple[int, int]]:
    count = len(atoms)
    if count == 0:
        return []
    best_cost = [float("inf")] * (count + 1)
    best_groups = [0] * (count + 1)
    best_short = [float("inf")] * (count + 1)
    nxt = [count] * (count + 1)
    best_cost[count] = 0.0
    for start in range(count - 1, -1, -1):
        for end in range(start + 1, count + 1):
            duration = atoms[end - 1].end - atoms[start].start
            cost = (duration - target) ** 2 + best_cost[end]
            groups = 1 + best_groups[end]
            short = duration if end == count else min(duration, best_short[end])
            chosen = best_cost[start] == float("inf")
            if not chosen and cost < best_cost[start] - 1e-9:
                chosen = True
            elif not chosen and abs(cost - best_cost[start]) <= 1e-9:
                if groups < best_groups[start] or (
                    groups == best_groups[start] and short > best_short[start]
                ):
                    chosen = True
            if not chosen:
                continue
            best_cost[start] = cost
            best_groups[start] = groups
            best_short[start] = short
            nxt[start] = end
    packed: list[tuple[int, int]] = []
    cursor = 0
    while cursor < count:
        packed.append((cursor, nxt[cursor]))
        cursor = nxt[cursor]
    return packed


def speech_files(wav_path: Path) -> list[Path]:
    duration, silences = _scan(wav_path)
    atoms = atoms_from_silences(duration, merge_silences(silences))
    if not atoms:
        return [wav_path]
    ranges = [
        (atoms[start].start, atoms[end - 1].end)
        for start, end in pack_atoms(atoms)
    ]
    if len(ranges) == 1 and ranges[0][0] <= 0.01 and abs(ranges[0][1] - duration) <= 0.02:
        return [wav_path]
    written: list[Path] = []
    try:
        for start, end in ranges:
            written.append(_write_range(wav_path, start, end))
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return written


def _rms(chunk: bytes, width: int) -> float:
    if width == 2:
        count = len(chunk) // 2
        samples = struct.unpack("<" + "h" * count, chunk[: count * 2]) if count else ()
    elif width == 1:
        samples = tuple(byte - 128 for byte in chunk)
        count = len(samples)
    else:
        count = len(chunk) // width
        samples = tuple(
            int.from_bytes(chunk[index : index + width], "little", signed=True)
            for index in range(0, count * width, width)
        )
    if not count:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / count)


def _scan(wav_path: Path) -> tuple[float, list[SilenceSpan]]:
    with wave.open(str(wav_path), "rb") as source:
        rate = source.getframerate()
        width = source.getsampwidth()
        channels = source.getnchannels()
        frames = source.readframes(source.getnframes())
    duration = len(frames) / (width * channels) / rate
    frame_bytes = max(1, int(rate * FRAME_SEC)) * width * channels
    silences: list[SilenceSpan] = []
    silent_at: float | None = None
    for offset in range(0, len(frames), frame_bytes):
        chunk = frames[offset : offset + frame_bytes]
        if len(chunk) < width * channels:
            break
        at = offset / (width * channels) / rate
        if _rms(chunk, width) < SILENCE_RMS:
            if silent_at is None:
                silent_at = at
            continue
        if silent_at is not None:
            silences.append(SilenceSpan(silent_at, at))
            silent_at = None
    if silent_at is not None:
        silences.append(SilenceSpan(silent_at, duration))
    return duration, silences


def _write_range(wav_path: Path, start: float, end: float) -> Path:
    with wave.open(str(wav_path), "rb") as source:
        rate = source.getframerate()
        source.setpos(int(start * rate))
        frames = source.readframes(max(0, int((end - start) * rate)))
        params = source.getparams()
    fd, name = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with wave.open(name, "wb") as target:
            target.setparams(params)
            target.writeframes(frames)
    except Exception:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)
