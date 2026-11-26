"""L3 滤镜表：on 接高通降噪，off 只转码。"""

from __future__ import annotations

import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path
from subprocess import CompletedProcess

from unittest.mock import patch

from src.audio.ffmpeg_dsp import FILTERS, FfmpegDspEnhancer, ffmpeg_args
from src.audio.silence import Atom, SilenceSpan, _write_range, atoms_from_silences, merge_silences, pack_atoms, speech_files
from src.pipeline.runner import Pipeline
from src.protocol.errors import MissingDependencyError
from src.protocol.states import EnhanceState


class TestFilterTable(unittest.TestCase):
    def test_off_has_no_af(self) -> None:
        args = ffmpeg_args(Path("in.wav"), Path("out.wav"), EnhanceState.OFF)
        self.assertNotIn("-af", args)
        self.assertIn("16000", args)
        self.assertEqual(FILTERS[EnhanceState.OFF], ())

    def test_on_appends_highpass_and_denoise(self) -> None:
        args = ffmpeg_args(Path("in.wav"), Path("out.wav"), EnhanceState.ON)
        af = args[args.index("-af") + 1]
        self.assertIn("highpass=f=80", af)
        self.assertIn("afftdn=nf=-25", af)
        self.assertNotIn("ForcedAligner", af)


class TestMissingFfmpeg(unittest.TestCase):
    def test_wav_passthrough_when_ffmpeg_missing(self) -> None:
        path = Path("a.wav")
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            self.assertEqual(FfmpegDspEnhancer().prepare(path, EnhanceState.OFF), [path])

    def test_mp3_needs_ffmpeg(self) -> None:
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            with self.assertRaises(MissingDependencyError):
                FfmpegDspEnhancer().prepare(Path("a.mp3"), EnhanceState.OFF)

    def test_enhance_on_needs_ffmpeg(self) -> None:
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=False):
            with self.assertRaises(MissingDependencyError):
                FfmpegDspEnhancer().prepare(Path("a.wav"), EnhanceState.ON)


class TestSilenceSplit(unittest.TestCase):
    def test_ac_asr_018(self) -> None:
        kept = merge_silences(
            [SilenceSpan(1.0, 1.1), SilenceSpan(5.0, 6.0), SilenceSpan(6.15, 7.0)],
            min_silence_sec=0.35,
        )
        self.assertEqual(kept, [SilenceSpan(5.0, 6.0), SilenceSpan(6.15, 7.0)])
        atoms = atoms_from_silences(12.0, kept)
        self.assertEqual(atoms[1], Atom(6.0, 6.15))
        packed = pack_atoms(atoms)
        start, end = packed[0]
        self.assertLessEqual(atoms[start].start, 6.0)
        self.assertGreaterEqual(atoms[end - 1].end, 6.15)
        sample = [
            Atom(0, 10),
            Atom(10, 22),
            Atom(22, 31),
            Atom(31, 42),
            Atom(42, 50),
        ]
        groups = pack_atoms(sample)
        self.assertEqual(
            [sample[end - 1].end - sample[start].start for start, end in groups],
            [22.0, 28.0],
        )

        class TwoPieces:
            def prepare(self, audio_path: Path, enhance: EnhanceState) -> list[Path]:
                return [Path("a.wav"), Path("b.wav")]

        class Engine:
            model = object()

            def transcribe(self, audio_path: Path, language: str = "auto", on_partial=None, on_status=None):
                text = "甲" if audio_path.stem == "a" else "乙"
                if on_partial is not None:
                    on_partial(text)
                return text, "Chinese"

            def release(self) -> None:
                self.model = None

        seen: list[str] = []
        result = Pipeline(TwoPieces(), Engine()).run(Path("in.wav"), on_partial=seen.append)
        self.assertEqual(result.text, "甲乙")
        self.assertEqual(seen[0], "甲")
        self.assertEqual(seen[-1], "甲乙")
        self.assertEqual(atoms_from_silences(3.0, []), [Atom(0.0, 3.0)])

    def test_short_voiced_atoms_are_preserved(self) -> None:
        self.assertEqual(
            atoms_from_silences(1.405, [SilenceSpan(1.0, 1.4)]),
            [Atom(0.0, 1.0), Atom(1.4, 1.405)],
        )
        self.assertEqual(
            atoms_from_silences(2.0, [SilenceSpan(0.005, 0.5), SilenceSpan(0.505, 1.0)]),
            [Atom(0.0, 0.005), Atom(0.5, 0.505), Atom(1.0, 2.0)],
        )
        self.assertEqual(atoms_from_silences(0.0, []), [])
        self.assertEqual(atoms_from_silences(1.0, [SilenceSpan(0.0, 1.0)]), [])

    def test_short_voiced_tail_keeps_all_samples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "tail.wav"
            voice = struct.pack("<h", 2000)
            payload = voice * 16000 + b"\0\0" * 6400 + voice * 80
            with wave.open(str(source), "wb") as target:
                target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                target.writeframes(payload)
            pieces = speech_files(source)
            try:
                output = bytearray()
                for piece in pieces:
                    with wave.open(str(piece), "rb") as audio:
                        output.extend(audio.readframes(audio.getnframes()))
                voiced = sum(value != 0 for value, in struct.iter_unpack("<h", output))
                self.assertEqual(voiced, 16080)
                self.assertTrue(source.exists())
            finally:
                for piece in pieces:
                    if piece != source:
                        piece.unlink(missing_ok=True)

    def test_slice_uses_sample_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "samples.wav"
            with wave.open(str(source), "wb") as target:
                target.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                target.writeframes(struct.pack("<16000h", *range(16000)))
            piece = _write_range(source, 1 / 16000, 11 / 16000)
            try:
                with wave.open(str(piece), "rb") as audio:
                    self.assertEqual(audio.getnframes(), 10)
                    self.assertEqual(audio.readframes(1), struct.pack("<h", 1))
            finally:
                piece.unlink(missing_ok=True)

    def test_split_removes_full_render(self) -> None:
        full_fd, full_name = tempfile.mkstemp(suffix=".wav")
        piece_fd, piece_name = tempfile.mkstemp(suffix=".wav")
        os.close(full_fd)
        os.close(piece_fd)
        full = Path(full_name)
        piece = Path(piece_name)
        try:
            with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=True), patch.object(
                FfmpegDspEnhancer, "_run_ffmpeg", return_value=full
            ), patch("src.audio.ffmpeg_dsp.speech_files", return_value=[piece]):
                got = FfmpegDspEnhancer().prepare(Path("in.mp4"), EnhanceState.OFF)
            self.assertEqual(got, [piece])
            self.assertFalse(full.exists())
            self.assertTrue(piece.exists())
        finally:
            full.unlink(missing_ok=True)
            piece.unlink(missing_ok=True)

    def test_ffmpeg_failure_removes_partial(self) -> None:
        created: dict[str, Path] = {}
        real_mkstemp = tempfile.mkstemp

        def spy_mkstemp(suffix: str = ".wav"):
            fd, name = real_mkstemp(suffix=suffix)
            created["path"] = Path(name)
            return fd, name

        failed = CompletedProcess(args=[], returncode=1, stderr="转码失败")
        with patch("src.audio.ffmpeg_dsp.is_ffmpeg_ready", return_value=True), patch(
            "src.audio.ffmpeg_dsp.tempfile.mkstemp", side_effect=spy_mkstemp
        ), patch("src.audio.ffmpeg_dsp.subprocess.run", return_value=failed):
            with self.assertRaises(RuntimeError):
                FfmpegDspEnhancer().prepare(Path("a.mp3"), EnhanceState.OFF)
        self.assertFalse(created["path"].exists())

    def test_cut_failure_removes_written_slices(self) -> None:
        written: list[Path] = []

        def fake_write(wav_path: Path, start: float, end: float) -> Path:
            if written:
                raise RuntimeError("切失败")
            fd, name = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            piece = Path(name)
            written.append(piece)
            return piece

        try:
            with patch("src.audio.silence._scan", return_value=(50.0, [SilenceSpan(20.0, 21.0)])), patch(
                "src.audio.silence._write_range", side_effect=fake_write
            ):
                with self.assertRaises(RuntimeError):
                    speech_files(Path("x.wav"))
            self.assertEqual(len(written), 1)
            self.assertFalse(written[0].exists())
        finally:
            for path in written:
                path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
