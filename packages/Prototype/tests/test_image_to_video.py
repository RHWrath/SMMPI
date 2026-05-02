"""
Unit tests for image_to_video.py.

Scope: the testable cores only.
- resize_image_to_phone_camera: actual PIL work with real images of known sizes.
- trigger_media_scan: mocked device, verify the ADB shell command shape.
- convert_image_to_video: subprocess + PIL work mocked out, verify the contract.

GUI-orchestration functions (on_image_confirm, push_image_to_gallery,
push_image_as_video) are intentionally NOT tested here. They are better
covered by system tests against a real device.

Note on quirks (see chat):
- `mirror=True` currently does a vertical flip (FLIP_TOP_BOTTOM), not a
  horizontal mirror. Naming is misleading but tests lock in current behavior.
"""

import os
import subprocess
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

import image_to_video


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_test_image(path, width, height, color=(128, 64, 200), mode="RGB"):
    """Create a solid-color test image at the given size and path."""
    img = Image.new(mode, (width, height), color)
    img.save(str(path), "JPEG" if str(path).lower().endswith(".jpg") else "PNG")
    return str(path)


# ---------------------------------------------------------------------------
# resize_image_to_phone_camera — "fill" mode
# ---------------------------------------------------------------------------

class TestResizeFillMode:
    """
    Fill mode: scale image to cover target exactly, crop overflow.
    Output dimensions must equal target dimensions exactly.
    """

    def test_produces_exact_target_dimensions_for_wider_input(self, tmp_path):
        input_path = tmp_path / "wide.jpg"
        output_path = tmp_path / "out.jpg"
        # 3000x1000 = 3:1 ratio, fill into 1080x1920 (9:16 portrait)
        _write_test_image(input_path, 3000, 1000)

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            assert result.size == (1080, 1920)

    def test_produces_exact_target_dimensions_for_taller_input(self, tmp_path):
        input_path = tmp_path / "tall.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 500, 3000)  # very tall

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            assert result.size == (1080, 1920)

    def test_fill_mode_for_snapchat_photo_spec(self, tmp_path):
        # Snapchat: 1080x1920, rotate 90, mirror False, fill mode
        input_path = tmp_path / "snap.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 4032, 3024)  # typical phone photo

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            rotate=90, mirror=False, resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            # With rotate=90, target dimensions are swapped internally
            # so final output becomes 1920x1080
            assert result.size == (1920, 1080)

    def test_rgba_input_is_flattened_to_rgb(self, tmp_path):
        input_path = tmp_path / "rgba.png"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 1000, 1000, color=(128, 64, 200), mode="RGBA")

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=500, target_height=500,
            resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            assert result.mode == "RGB"


# ---------------------------------------------------------------------------
# resize_image_to_phone_camera — "contain" mode
# ---------------------------------------------------------------------------

class TestResizeContainMode:
    """
    Contain mode: preserve aspect ratio, fit within target as max bounds.
    Output dimensions should not exceed target and should keep source ratio.
    """

    def test_preserves_aspect_ratio_for_landscape(self, tmp_path):
        input_path = tmp_path / "landscape.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 4000, 2000)  # 2:1

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1920, target_height=1080,
            resize_mode="contain",
        )

        assert ok is True
        with Image.open(output_path) as result:
            w, h = result.size
            assert w <= 1920 and h <= 1080
            # 2:1 ratio preserved
            assert abs((w / h) - 2.0) < 0.01

    def test_preserves_aspect_ratio_for_portrait(self, tmp_path):
        input_path = tmp_path / "portrait.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 2000, 4000)  # 1:2

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1920, target_height=1080,
            resize_mode="contain",
        )

        assert ok is True
        with Image.open(output_path) as result:
            w, h = result.size
            assert w <= 1920 and h <= 1080
            assert abs((h / w) - 2.0) < 0.01

    def test_does_not_upscale_small_image(self, tmp_path):
        input_path = tmp_path / "small.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 400, 300)

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=4032, target_height=3024,
            resize_mode="contain",
        )

        assert ok is True
        with Image.open(output_path) as result:
            # contain mode leaves small images at their original size
            assert result.size == (400, 300)

    def test_contain_mode_for_whatsapp_photo_spec(self, tmp_path):
        # WhatsApp: 4032x3024, no rotate, no mirror, contain mode
        input_path = tmp_path / "whats.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 6000, 4000)  # bigger than target

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=4032, target_height=3024,
            resize_mode="contain",
        )

        assert ok is True
        with Image.open(output_path) as result:
            w, h = result.size
            assert w <= 4032 and h <= 3024


# ---------------------------------------------------------------------------
# resize_image_to_phone_camera — "fit" (legacy)
# ---------------------------------------------------------------------------

class TestResizeFitMode:
    """Fit mode: pad with black to exact target dimensions."""

    def test_produces_exact_target_dimensions(self, tmp_path):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 1000, 500)  # 2:1

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            resize_mode="fit",
        )

        assert ok is True
        with Image.open(output_path) as result:
            assert result.size == (1080, 1920)


# ---------------------------------------------------------------------------
# resize_image_to_phone_camera — rotation & mirror
# ---------------------------------------------------------------------------

class TestRotationAndMirror:

    def test_rotate_90_swaps_target_dimensions(self, tmp_path):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 1000, 2000)

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            rotate=90, resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            # 90-degree rotation swaps target: 1080x1920 -> 1920x1080
            assert result.size == (1920, 1080)

    def test_rotate_180_does_not_swap_target_dimensions(self, tmp_path):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 1000, 2000)

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            rotate=180, resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            # 180 rotation is a flip, dimensions stay portrait
            assert result.size == (1080, 1920)

    def test_rotate_270_swaps_target_dimensions(self, tmp_path):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 1000, 2000)

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            rotate=270, resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            assert result.size == (1920, 1080)

    def test_rotate_none_produces_exact_target(self, tmp_path):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.jpg"
        _write_test_image(input_path, 1000, 2000)

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=1080, target_height=1920,
            rotate=None, resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            assert result.size == (1080, 1920)

    def test_mirror_true_performs_vertical_flip(self, tmp_path):
        # NOTE: parameter is called "mirror" but current code uses
        # Image.FLIP_TOP_BOTTOM (vertical flip, not horizontal mirror).
        # Locking in current behavior — see chat for the open question.
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.jpg"

        # Build an image with a distinctive top vs. bottom pattern:
        # top half white, bottom half black.
        img = Image.new("RGB", (100, 100), (0, 0, 0))
        for y in range(50):
            for x in range(100):
                img.putpixel((x, y), (255, 255, 255))
        img.save(str(input_path))

        ok = image_to_video.resize_image_to_phone_camera(
            str(input_path), str(output_path),
            target_width=100, target_height=100,
            mirror=True, resize_mode="fill",
        )

        assert ok is True
        with Image.open(output_path) as result:
            # After vertical flip: top becomes black, bottom becomes white.
            # Check near center of each half to dodge interpolation blur at boundary.
            top_pixel = result.getpixel((50, 20))
            bottom_pixel = result.getpixel((50, 80))
            # Top was white before flip, should now be black (dark)
            assert sum(top_pixel) < 150
            # Bottom was black before flip, should now be white (bright)
            assert sum(bottom_pixel) > 600


# ---------------------------------------------------------------------------
# resize_image_to_phone_camera — failure cases
# ---------------------------------------------------------------------------

class TestResizeFailures:

    def test_returns_false_on_missing_input_file(self, tmp_path):
        output_path = tmp_path / "out.jpg"
        ok = image_to_video.resize_image_to_phone_camera(
            str(tmp_path / "does_not_exist.jpg"), str(output_path),
        )
        assert ok is False
        assert not output_path.exists()

    def test_returns_false_on_corrupt_input(self, tmp_path):
        corrupt_path = tmp_path / "corrupt.jpg"
        corrupt_path.write_bytes(b"not a real jpeg")
        output_path = tmp_path / "out.jpg"

        ok = image_to_video.resize_image_to_phone_camera(
            str(corrupt_path), str(output_path),
        )
        assert ok is False


# ---------------------------------------------------------------------------
# trigger_media_scan
# ---------------------------------------------------------------------------

class TestTriggerMediaScan:

    def test_sends_media_scan_broadcast(self):
        mock_device = MagicMock()
        mock_device.shell.return_value = "Broadcast completed"

        ok = image_to_video.trigger_media_scan(
            mock_device, "/storage/emulated/0/DCIM/Camera/virtual_photo.jpg"
        )

        assert ok is True
        # Assert the ADB shell command was invoked once
        assert mock_device.shell.call_count == 1

    def test_broadcast_command_shape(self):
        mock_device = MagicMock()
        mock_device.shell.return_value = "ok"

        image_to_video.trigger_media_scan(
            mock_device, "/storage/emulated/0/DCIM/Camera/virtual_photo.jpg"
        )

        # Pull the command string that was sent
        call_args = mock_device.shell.call_args
        sent_cmd = call_args[0][0]  # first positional arg
        assert "am broadcast" in sent_cmd
        assert "android.intent.action.MEDIA_SCANNER_SCAN_FILE" in sent_cmd
        assert 'file:///storage/emulated/0/DCIM/Camera/virtual_photo.jpg' in sent_cmd

    def test_returns_false_on_shell_exception(self):
        mock_device = MagicMock()
        mock_device.shell.side_effect = RuntimeError("device disconnected")

        ok = image_to_video.trigger_media_scan(mock_device, "/fake/path.jpg")
        assert ok is False


# ---------------------------------------------------------------------------
# convert_image_to_video
# ---------------------------------------------------------------------------

class TestConvertImageToVideo:
    """
    convert_image_to_video resizes the image (which we've already tested)
    and shells out to ffmpeg. We mock ffmpeg so these tests run fast and
    don't require a real ffmpeg install.
    """

    def _mock_ffmpeg_success(self):
        mock = MagicMock()
        mock.returncode = 0
        mock.stderr = ""
        return mock

    def _mock_ffmpeg_failure(self, returncode=1, stderr="ffmpeg failed"):
        mock = MagicMock()
        mock.returncode = returncode
        mock.stderr = stderr
        return mock

    def test_returns_false_when_ffmpeg_not_found(self, tmp_path, monkeypatch):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.mp4"
        _write_test_image(input_path, 1000, 1000)

        monkeypatch.setattr(image_to_video, "get_ffmpeg_path", lambda: None)

        ok = image_to_video.convert_image_to_video(
            str(input_path), str(output_path),
        )
        assert ok is False

    def test_returns_false_when_resize_fails(self, tmp_path, monkeypatch):
        # Non-existent input → resize returns False → convert returns False before touching ffmpeg
        missing = tmp_path / "missing.jpg"
        output = tmp_path / "out.mp4"

        ok = image_to_video.convert_image_to_video(str(missing), str(output))
        assert ok is False

    def test_returns_true_on_ffmpeg_success(self, tmp_path, monkeypatch):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.mp4"
        _write_test_image(input_path, 1000, 1000)

        monkeypatch.setattr(image_to_video, "get_ffmpeg_path", lambda: "/fake/ffmpeg")
        with patch.object(subprocess, "run", return_value=self._mock_ffmpeg_success()):
            ok = image_to_video.convert_image_to_video(
                str(input_path), str(output_path),
            )

        assert ok is True

    def test_returns_false_on_ffmpeg_failure(self, tmp_path, monkeypatch):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.mp4"
        _write_test_image(input_path, 1000, 1000)

        monkeypatch.setattr(image_to_video, "get_ffmpeg_path", lambda: "/fake/ffmpeg")
        with patch.object(subprocess, "run", return_value=self._mock_ffmpeg_failure()):
            ok = image_to_video.convert_image_to_video(
                str(input_path), str(output_path),
            )

        assert ok is False

    def test_returns_false_on_ffmpeg_timeout(self, tmp_path, monkeypatch):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.mp4"
        _write_test_image(input_path, 1000, 1000)

        monkeypatch.setattr(image_to_video, "get_ffmpeg_path", lambda: "/fake/ffmpeg")
        with patch.object(
            subprocess, "run",
            side_effect=subprocess.TimeoutExpired("ffmpeg", 30)
        ):
            ok = image_to_video.convert_image_to_video(
                str(input_path), str(output_path),
            )

        assert ok is False

    def test_ffmpeg_called_with_correct_output_path(self, tmp_path, monkeypatch):
        input_path = tmp_path / "in.jpg"
        output_path = tmp_path / "out.mp4"
        _write_test_image(input_path, 1000, 1000)

        monkeypatch.setattr(image_to_video, "get_ffmpeg_path", lambda: "/fake/ffmpeg")
        with patch.object(subprocess, "run", return_value=self._mock_ffmpeg_success()) as mock_run:
            image_to_video.convert_image_to_video(
                str(input_path), str(output_path),
            )

            call_args = mock_run.call_args[0][0]  # the command list
            assert call_args[0] == "/fake/ffmpeg"
            assert str(output_path) in call_args
