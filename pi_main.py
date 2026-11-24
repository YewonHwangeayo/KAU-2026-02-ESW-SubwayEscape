"""ST7789 adapter for the classroom Pi 5 board; CE0 is kernel-controlled."""

import argparse
from contextlib import ExitStack
import errno
import logging
import re
from pathlib import Path
import signal
import subprocess
from threading import Lock
from time import monotonic, sleep

from buttons import A, B, DOWN, LEFT, RIGHT, UP, InputState
from config import HEIGHT, WIDTH
from display import render
from game import Game

LOG = logging.getLogger(__name__)
BUTTONS = (LEFT, RIGHT, UP, DOWN, A, B)
DEFAULT_PINS = {
    "cs": "CE0", "dc": "D25", "reset": "D24", "backlight": "D26",
    LEFT: "D27", RIGHT: "D23", UP: "D17", DOWN: "D22",
    A: "D5", B: "D6", "c": "D4",
}


class KernelSPI:
    """The SPI subset used by Adafruit SPIDevice for a write-only LCD.

    chip_select=None in SPIDevice leaves CE0 to the spidev kernel driver.
    No DigitalInOut request is made for GPIO8.
    """

    def __init__(self, stack):
        import spidev

        self.lock = Lock()
        self.device = spidev.SpiDev()
        stack.callback(self.device.close)
        LOG.info("SPI opening /dev/spidev0.0; kernel CE0/GPIO8")
        self.device.open(0, 0)
        self.device.no_cs = False
        self.device.cshigh = False

    def try_lock(self):
        return self.lock.acquire(blocking=False)

    def unlock(self):
        self.lock.release()

    def configure(self, *, baudrate, polarity=0, phase=0, bits=8):
        self.device.max_speed_hz = baudrate
        self.device.mode = (polarity << 1) | phase
        self.device.bits_per_word = bits

    def write(self, buffer, *, start=0, end=None):
        data = memoryview(buffer)[start:end]
        if data:
            self.device.writebytes2(data)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("game", "lcd-test", "buttons-test", "diagnose"),
                        default="game")
    for name, default in DEFAULT_PINS.items():
        parser.add_argument(f"--{name}", default=default, help=f"board pin (default {default})")
    parser.add_argument("--x-offset", type=int, default=0)
    parser.add_argument("--y-offset", type=int, default=80)
    # Classroom Joystick.py display settings.
    parser.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=180)
    parser.add_argument("--baudrate", type=int, default=24000000)
    parser.add_argument("--seconds", type=float, default=0,
                        help="test duration; 0 runs until Ctrl-C")
    args = parser.parse_args(argv)
    for key in DEFAULT_PINS:
        name = getattr(args, key)
        if name != "CE0" and not re.fullmatch(r"D(?:[0-9]|[12][0-9])", name):
            parser.error(f"invalid board pin for {key}: {name}")
    normalized = [8 if getattr(args, key) in ("CE0", "D8")
                  else int(getattr(args, key).removeprefix("D"))
                  for key in DEFAULT_PINS]
    if len(set(normalized)) != len(normalized):
        parser.error("GPIO assignments overlap (CE0 and D8 are the same pin)")
    if args.cs not in ("CE0", "D8"):
        parser.error("kernel CS uses CE0/GPIO8; keep --cs CE0")
    if set(normalized) & {7, 9, 10, 11}:
        parser.error("GPIO7/9/10/11 are reserved for the enabled SPI0 interface")
    if args.baudrate is not None and args.baudrate <= 0:
        parser.error("--baudrate must be positive")
    if args.seconds < 0:
        parser.error("--seconds must be nonnegative")
    return args


def diagnose():
    """Read-only checks, also useful before any GPIO initialization."""
    commands = (
        ["gpioinfo"],
        ["pinctrl", "get", "8"],
        ["fuser", "-v", "/dev/spidev0.0"],
        ["pgrep", "-af", "python|jupyter"],
    )
    for command in commands:
        LOG.info("diagnostic command: %s", " ".join(command))
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5)
            LOG.info("exit=%s\n%s%s", result.returncode, result.stdout, result.stderr)
        except (OSError, subprocess.TimeoutExpired) as exc:
            LOG.warning("%s", exc)
    path = Path("/boot/firmware/config.txt")
    if path.exists():
        LOG.info("SPI config lines\n%s", "\n".join(
            line for line in path.read_text().splitlines()
            if "spi" in line.lower()
        ))


def request_gpio(stack, board, digitalio, role, name, *, output=None):
    pin = getattr(board, name)
    LOG.info("GPIO requesting %s = board.%s (%s)", role, name, pin)
    try:
        port = digitalio.DigitalInOut(pin)
    except OSError as exc:
        if exc.errno == errno.EBUSY:
            LOG.error("GPIO busy: %s=%s. Run --mode diagnose to inspect consumers.", role, name)
        raise
    stack.callback(port.deinit)
    if output is None:
        # Classroom board uses input wiring as defined in Joystick.py.
        port.switch_to_input()
    else:
        port.switch_to_output(value=output)
    LOG.info("GPIO ready: %s=%s", role, name)
    return port


def turn_off(port):
    port.value = False
    LOG.info("Backlight off")


def open_hardware(stack, args):
    import board
    import digitalio

    gpio = {}
    lcd = None
    if args.mode != "buttons-test":
        from adafruit_rgb_display import st7789

        spi = KernelSPI(stack)
        for role in ("dc", "reset", "backlight"):
            gpio[role] = request_gpio(
                stack, board, digitalio, role, getattr(args, role), output=False
            )
        stack.callback(turn_off, gpio["backlight"])
        LOG.info("LCD %dx%d rotation=%d offset=(%d,%d) baudrate=%d; cs=None/kernel CE0",
                 WIDTH, HEIGHT, args.rotation, args.x_offset, args.y_offset, args.baudrate)
        lcd = st7789.ST7789(
            spi, cs=None, dc=gpio["dc"], rst=gpio["reset"],
            width=WIDTH, height=HEIGHT, rotation=args.rotation,
            x_offset=args.x_offset, y_offset=args.y_offset, baudrate=args.baudrate,
        )
        # Backlight stays off until a complete first frame has been written.
    if args.mode != "lcd-test":
        for role in (*BUTTONS, "c"):
            gpio[role] = request_gpio(stack, board, digitalio, role, getattr(args, role))
    return lcd, gpio


def lcd_test_frame():
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (WIDTH, HEIGHT), "black")
    draw = ImageDraw.Draw(image)
    for i, color in enumerate(("red", "green", "blue")):
        draw.rectangle((i * 80, 0, i * 80 + 79, 179), fill=color)
    draw.rectangle((0, 0, WIDTH - 1, HEIGHT - 1), outline="white", width=2)
    draw.text((12, 192), "ST7789 240x240", fill="white")
    draw.text((12, 214), "TOP RGB / WHITE BORDER", fill="white")
    return image


def run(args):
    if args.mode == "diagnose":
        diagnose()
        return
    with ExitStack() as stack:
        lcd, gpio = open_hardware(stack, args)
        game = Game()
        held = frozenset()
        previous = monotonic()
        started = previous
        if lcd is not None:
            lcd.image(lcd_test_frame() if args.mode == "lcd-test" else render(game))
            gpio["backlight"].value = True
            LOG.info("First frame sent; D26 backlight enabled (verify on LCD)")
        while not args.seconds or monotonic() - started < args.seconds:
            now = monotonic()
            if args.mode != "lcd-test":
                current = frozenset(
                    button for button in (*BUTTONS, "c") if not gpio[button].value
                )
                if current != held:
                    LOG.info("Buttons held=%s", ",".join(sorted(current)) or "(none)")
                if args.mode == "game":
                    pressed = tuple(button for button in BUTTONS if button in current - held)
                    game.update(now - previous, InputState(current & frozenset(BUTTONS), pressed))
                    lcd.image(render(game))
                held = current
            previous = now
            sleep(max(0, 1 / 30 - (monotonic() - now)))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    # SIGTERM from a terminal/process manager unwinds ExitStack like Ctrl-C.
    def terminate(_signum, _frame):
        raise KeyboardInterrupt
    previous_handler = signal.signal(signal.SIGTERM, terminate)
    try:
        run(args)
    except KeyboardInterrupt:
        LOG.info("Stopped; hardware resources released")
    except Exception:
        LOG.exception("Hardware run failed; acquired resources released")
        raise
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


if __name__ == "__main__":
    main()
