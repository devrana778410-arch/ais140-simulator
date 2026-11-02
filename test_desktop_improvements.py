import unittest
import tkinter as tk
import sys
import os

BASE_DIR = r"D:\ais140sim\ais140-simulator-main"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.gui.device_tab import DeviceTab


class TestDesktopImprovements(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_vltd_custom_coordinates_in_get_config(self):
        """Verify that VLTD profile reads custom coordinates from entry inputs."""
        tab = DeviceTab(self.root, device_num=1, on_start=lambda cfg: None, on_stop=lambda: None, on_remove=lambda: None)
        tab._profile_var.set("VLTD")
        tab._apply_profile_visibility("VLTD")

        # Set valid IMEI
        tab._imei.delete(0, "end")
        tab._imei.insert(0, "864000080731065")

        # Set custom coordinates
        tab._lat.delete(0, "end")
        tab._lat.insert(0, "23.022500")
        tab._lon.delete(0, "end")
        tab._lon.insert(0, "72.571400")

        cfg = tab._collect_config()
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["profile"], "VLTD")
        self.assertEqual(cfg["lat"], 23.022500)
        self.assertEqual(cfg["lon"], 72.571400)

        # Test selecting RTO updates lat/lon entries
        tab._on_rto_autocomplete_selected("GJ-01", 23.033863, 72.585022)
        self.assertEqual(tab._lat.get(), "23.033863")
        self.assertEqual(tab._lon.get(), "72.585022")

    def test_log_box_height_and_scrollable(self):
        """Verify that log box is roomy (height >= 14) and inside a scrollable container."""
        tab = DeviceTab(self.root, device_num=1, on_start=lambda cfg: None, on_stop=lambda: None, on_remove=lambda: None)
        self.assertGreaterEqual(int(tab._log.cget("height")), 14)
        
        # Verify log has yscrollcommand configured
        yscroll = tab._log.cget("yscrollcommand")
        self.assertTrue(bool(yscroll), "Log box must have vertical scrollbar configured")


if __name__ == "__main__":
    unittest.main()
