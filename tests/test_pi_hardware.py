"""Hardware contracts verified with fakes; electrical behavior needs a Pi."""

from contextlib import ExitStack
import errno
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import sys

import pi_main


class PiHardwareTests(unittest.TestCase):
    def args(self, *extra):
        return pi_main.parse_args(["--rotation", "180", "--baudrate", "24000000", *extra])

    def modules(self, fail_role=None, fail_lcd=False):
        events = []
        ports = []
        def port(pin):
            events.append(("request", pin))
            if pin == fail_role:
                raise OSError(errno.EBUSY, "busy")
            obj = Mock(value=True)
            obj.deinit.side_effect = lambda: events.append(("release", pin))
            ports.append(obj)
            return obj

        board = SimpleNamespace(**{name: name for name in pi_main.DEFAULT_PINS.values()})
        digitalio = SimpleNamespace(DigitalInOut=port, Pull=SimpleNamespace(UP="pullup"))
        raw = Mock()
        raw.close.side_effect = lambda: events.append(("spi-close",))
        constructor = Mock(side_effect=RuntimeError("LCD failed") if fail_lcd else None)
        modules = {
            "board": board, "digitalio": digitalio,
            "spidev": SimpleNamespace(SpiDev=lambda: raw),
            "adafruit_rgb_display": SimpleNamespace(
                st7789=SimpleNamespace(ST7789=constructor)
            ),
        }
        return modules, events, ports, raw, constructor

    def test_mapping_and_cs_kernel_ownership(self):
        modules, events, ports, raw, constructor = self.modules()
        with patch.dict(sys.modules, modules):
            with ExitStack() as stack:
                _, gpio = pi_main.open_hardware(stack, self.args())
                self.assertEqual(set(gpio), set(pi_main.DEFAULT_PINS) - {"cs"})
                self.assertNotIn(("request", "CE0"), events)
                raw.open.assert_called_once_with(0, 0)
                self.assertFalse(raw.no_cs)
                kwargs = constructor.call_args.kwargs
                self.assertIsNone(kwargs["cs"])
                self.assertEqual((kwargs["width"], kwargs["height"], kwargs["y_offset"]),
                                 (240, 240, 80))
                self.assertEqual((kwargs["rotation"], kwargs["baudrate"]), (180, 24000000))
                gpio["backlight"].switch_to_output.assert_called_once_with(value=False)
            self.assertEqual(events[-1], ("spi-close",))
            for port in ports:
                port.deinit.assert_called_once()

    def test_partial_initialization_and_lcd_failure_release_resources(self):
        for options in ({"fail_role": "D24"}, {"fail_lcd": True}):
            modules, events, ports, raw, _ = self.modules(**options)
            with patch.dict(sys.modules, modules):
                with self.assertRaises((OSError, RuntimeError)):
                    with ExitStack() as stack:
                        pi_main.open_hardware(stack, self.args())
            raw.close.assert_called_once()
            for port in ports:
                port.deinit.assert_called_once()

    def test_button_test_never_opens_spi(self):
        modules, events, _, raw, constructor = self.modules()
        with patch.dict(sys.modules, modules):
            with ExitStack() as stack:
                lcd, gpio = pi_main.open_hardware(
                    stack, pi_main.parse_args(["--mode", "buttons-test"])
                )
                self.assertIsNone(lcd)
                self.assertEqual(set(gpio), set((*pi_main.BUTTONS, "c")))
        raw.open.assert_not_called()
        constructor.assert_not_called()

    def test_lcd_test_never_requests_buttons(self):
        modules, events, _, _, _ = self.modules()
        with patch.dict(sys.modules, modules):
            with ExitStack() as stack:
                _, gpio = pi_main.open_hardware(stack, self.args("--mode", "lcd-test"))
                self.assertEqual(set(gpio), {"dc", "reset", "backlight"})

    def test_spi_adapter_configure_write_and_release(self):
        modules, _, _, raw, _ = self.modules()
        with patch.dict(sys.modules, modules):
            with ExitStack() as stack:
                spi = pi_main.KernelSPI(stack)
                self.assertTrue(spi.try_lock())
                self.assertFalse(spi.try_lock())
                spi.configure(baudrate=24000000, polarity=1, phase=1)
                self.assertEqual(raw.mode, 3)
                spi.write(b"abcd", start=1, end=3)
                self.assertEqual(bytes(raw.writebytes2.call_args.args[0]), b"bc")
                spi.unlock()
                self.assertTrue(spi.try_lock())
                spi.unlock()
            raw.close.assert_called_once()

    def test_duplicate_alias_reserved_pin_and_classroom_defaults(self):
        for flags in (["--a", "D8"], ["--a", "D10"], ["--a", "bad"],
                      ["--cs", "D5"], ["--baudrate", "0"]):
            with self.subTest(flags=flags), patch("sys.stderr"):
                with self.assertRaises(SystemExit):
                    self.args(*flags)
        args = pi_main.parse_args([])
        self.assertEqual((args.rotation, args.baudrate, args.y_offset), (180, 24000000, 80))

    def test_lcd_first_frame_and_backlight_shutdown(self):
        modules, events, ports, raw, constructor = self.modules()
        lcd = Mock()
        constructor.return_value = lcd
        with patch.dict(sys.modules, modules):
            pi_main.run(self.args("--mode", "lcd-test", "--seconds", "0.001"))
        self.assertEqual(lcd.image.call_args.args[0].size, (240, 240))
        self.assertFalse(ports[2].value)
        raw.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
