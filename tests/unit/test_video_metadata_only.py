"""Round 18, task 5 (F-29): a video read is not all-or-nothing.

The reader tried OpenCV, then moviepy, then gave up with "No video library
installed". Two things were wrong with that:

* the container is readable without either decoder - duration, resolution,
  codec, sample rate and the container's own tags say a great deal about a
  video, and ffmpeg is available offline (the ``imageio-ffmpeg`` wheel ships a
  static binary), so the failure was a missing fallback, not missing data;
* nothing in the result ever said that *speech* was not transcribed. A caller
  reading "duration 30s, 1920x1080" could reasonably assume the video had been
  understood. Every path now states ``speech_extracted: False`` and names the
  scope of the read.

Fixtures are the corpus videos (read, never written) plus one generated clip,
so the tests exercise real containers rather than header stubs.
"""
import os
import subprocess
import sys

import pytest

CORPUS = os.path.join(os.path.dirname(__file__), "..", "..", "test-doc")
VIDEO_DIR = os.path.join(CORPUS, "Videos")
SAMPLE = os.path.join(VIDEO_DIR, "testMP4VideoAudio.mp4")

from reader_file.readers import read_video  # noqa: E402
from reader_file.readers.read_video import (  # noqa: E402
    VideoFileReader,
    _parse_ffmpeg_stderr,
    ffmpeg_path,
    probe_container_metadata,
)


@pytest.fixture
def no_decoders(monkeypatch):
    """Make `import cv2` and `import moviepy` fail the way a bare machine does."""
    monkeypatch.setitem(sys.modules, "cv2", None)
    monkeypatch.setitem(sys.modules, "moviepy", None)
    monkeypatch.setitem(sys.modules, "moviepy.editor", None)


def _require(path):
    if not os.path.exists(path):
        pytest.skip(f"corpus file missing: {path}")


# --------------------------------------------------------------------------- #
# ffmpeg banner parsing
# --------------------------------------------------------------------------- #
BANNER = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'clip.mp4':
  Metadata:
    major_brand     : isom
    creation_time   : 2021-04-05T09:08:07.000000Z
    title           : Quarterly review
  Duration: 00:01:23.45, start: 0.000000, bitrate: 812 kb/s
  Stream #0:0(und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1280x720, 812 kb/s, 25 fps, 25 tbr
  Stream #0:1(und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 96 kb/s
"""


def test_the_banner_yields_duration_geometry_and_streams():
    parsed = _parse_ffmpeg_stderr(BANNER)
    assert parsed["duration_seconds"] == pytest.approx(83.45, abs=0.01)
    assert (parsed["width"], parsed["height"]) == (1280, 720)
    assert parsed["fps"] == 25.0
    assert parsed["codec"].startswith("h264")
    assert parsed["audio_codec"].startswith("aac")
    assert parsed["audio_sample_rate"] == 44100
    assert parsed["has_audio"] is True


def test_container_tags_are_read_not_discarded():
    parsed = _parse_ffmpeg_stderr(BANNER)
    assert parsed["tags"]["title"] == "Quarterly review"
    assert parsed["tags"]["creation_time"].startswith("2021-04-05")


def test_a_silent_stream_is_reported_as_having_no_audio():
    parsed = _parse_ffmpeg_stderr(
        "  Duration: 00:00:05.00, start: 0.0, bitrate: 100 kb/s\n"
        "  Stream #0:0: Video: h264, yuv420p, 320x240, 30 fps\n")
    assert parsed["has_audio"] is False
    assert parsed["width"] == 320


# --------------------------------------------------------------------------- #
# No decoder installed: metadata only, and it says so
# --------------------------------------------------------------------------- #
def test_no_decoder_still_returns_metadata(no_decoders):
    _require(SAMPLE)
    if ffmpeg_path() is None:
        pytest.skip("no ffmpeg binary available")
    result = VideoFileReader().read_video_file(SAMPLE)
    assert "error" not in result, result.get("error")
    assert result.get("metadata_only") is True
    assert result.get("metadata_source") == "ffmpeg"
    assert result["width"] > 0 and result["height"] > 0
    assert result["resolution"] == f"{result['width']}x{result['height']}"
    assert result["duration_seconds"] > 0
    assert result["duration_formatted"]
    assert result.get("codec")


def test_no_decoder_states_that_no_speech_was_extracted(no_decoders):
    _require(SAMPLE)
    if ffmpeg_path() is None:
        pytest.skip("no ffmpeg binary available")
    result = VideoFileReader().read_video_file(SAMPLE)
    assert result["speech_extracted"] is False
    assert result["extraction_scope"] == "container_metadata"
    assert "speech" in result["extraction_note"].lower()
    assert result.get("missing_dependency")


def test_without_ffmpeg_either_the_read_fails_honestly(no_decoders, monkeypatch):
    _require(SAMPLE)
    monkeypatch.setattr(read_video, "ffmpeg_path", lambda: None)
    result = VideoFileReader().read_video_file(SAMPLE)
    assert result.get("error")
    assert "ffmpeg" in result["error"]
    assert result["speech_extracted"] is False


def test_a_file_that_is_not_a_video_does_not_crash_the_reader(no_decoders, tmp_path):
    bogus = tmp_path / "not_a_video.mp4"
    bogus.write_bytes(b"this is not a container")
    result = VideoFileReader().read_video_file(str(bogus))
    assert isinstance(result, dict)
    assert result.get("error") or result.get("speech_extracted") is False


# --------------------------------------------------------------------------- #
# The decoder path makes the same claim
# --------------------------------------------------------------------------- #
def test_the_opencv_path_also_says_no_speech_was_extracted():
    _require(SAMPLE)
    pytest.importorskip("cv2")
    result = VideoFileReader().read_video_file(SAMPLE)
    assert "error" not in result, result.get("error")
    assert result["speech_extracted"] is False
    assert result["extraction_scope"] == "container_metadata"
    assert "speech" in result["extraction_note"].lower()


def test_probing_a_missing_file_returns_nothing_rather_than_raising(tmp_path):
    assert probe_container_metadata(str(tmp_path / "absent.mp4")) == {}
