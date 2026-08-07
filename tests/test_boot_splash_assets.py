import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BootSplashAssetTests(unittest.TestCase):
    def test_boot_splash_is_touchscreen_sized_png(self):
        splash = ROOT / "docs" / "assets" / "morsepi-boot-splash.png"

        data = splash.read_bytes()

        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual((width, height), (800, 480))

    def test_installer_targets_plymouth_pix_theme_and_keeps_backups(self):
        installer = ROOT / "scripts" / "install_boot_splash.sh"

        script = installer.read_text(encoding="utf-8")

        self.assertIn("/usr/share/plymouth/themes/pix/splash.png", script)
        self.assertIn(".morsepi-original", script)
        self.assertIn(".morsepi-backup-", script)
        self.assertIn("update-initramfs", script)
