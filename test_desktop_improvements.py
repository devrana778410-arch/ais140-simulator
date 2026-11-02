import unittest
import tkinter as tk
import sys
import os

BASE_DIR = r"D:\ais140sim\ais140-simulator-main"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.gui.device_tab import DeviceTab
from src.gui.app import SimulatorApp


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

    def test_mousewheel_scrolling(self):
        """Verify that mousewheel scrolls the canvas with both standard mouse and trackpads."""
        win = tk.Toplevel(self.root)
        app = SimulatorApp(win)
        win.update()
        app._toggle_debug_mode()
        win.update()

        dev_tab = app._devices[1]["tab"]

        # 1. Standard mouse wheel down (-120)
        before = app._viewport_canvas.yview()[0]
        dev_tab._inputs_card.event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        win.update()
        after = app._viewport_canvas.yview()[0]
        self.assertGreater(after, before, "Mouse wheel down should scroll canvas downward")

        # 2. Trackpad small delta (-30)
        before = after
        dev_tab._inputs_card.event_generate("<MouseWheel>", delta=-30, x=5, y=5)
        win.update()
        after = app._viewport_canvas.yview()[0]
        self.assertGreater(after, before, "Trackpad small delta should scroll canvas downward")

        # 3. Mouse wheel over empty log falls through to scroll canvas
        before = after
        dev_tab._log.event_generate("<MouseWheel>", delta=-120, x=5, y=5)
        win.update()
        after = app._viewport_canvas.yview()[0]
        self.assertGreater(after, before, "Empty log should fall through to scroll canvas")

        win.destroy()


if __name__ == "__main__":
    unittest.main()
