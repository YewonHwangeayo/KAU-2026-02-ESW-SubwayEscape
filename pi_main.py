"""Optional ST7789/GPIO adapter with an explicit wiring configuration."""

import argparse
from contextlib import ExitStack
from time import monotonic, sleep

from buttons import A, B, DOWN, LEFT, RIGHT, UP, InputState
from config import HEIGHT, WIDTH
from display import render
from game import Game

BUTTONS = (LEFT, RIGHT, UP, DOWN, A, B)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("cs", "dc", "reset", *BUTTONS):
        parser.add_argument(f"--{name}", required=True, help="Blinka board pin name")
    parser.add_argument("--x-offset", type=int, required=True)
    parser.add_argument("--y-offset", type=int, required=True)
    parser.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), required=True)
    args = parser.parse_args()

    # Imported only on Pi, after parsing wiring supplied by the user.
    import board
    import digitalio
    from adafruit_rgb_display import st7789

    names = {name: getattr(args, name) for name in ("cs", "dc", "reset", *BUTTONS)}
    if len(set(names.values())) != len(names):
        parser.error("choose distinct pins for display control and buttons")
    try:
        pins = {name: getattr(board, pin) for name, pin in names.items()}
    except AttributeError as exc:
        parser.error(str(exc))

    with ExitStack() as stack:
        spi = board.SPI()
        stack.callback(spi.deinit)
        gpio = {}
        for name, pin in pins.items():
            port = digitalio.DigitalInOut(pin)
            stack.callback(port.deinit)
            gpio[name] = port
        for button in BUTTONS:
            gpio[button].switch_to_input(pull=digitalio.Pull.UP)

        lcd = st7789.ST7789(
            spi, cs=gpio["cs"], dc=gpio["dc"], rst=gpio["reset"],
            width=WIDTH, height=HEIGHT, rotation=args.rotation,
            x_offset=args.x_offset, y_offset=args.y_offset,
        )
        game = Game()
        held = frozenset()
        previous = monotonic()
        try:
            while True:
                now = monotonic()
                current = frozenset(button for button in BUTTONS if not gpio[button].value)
                pressed = tuple(button for button in BUTTONS if button in current - held)
                game.update(now - previous, InputState(current, pressed))
                previous, held = now, current
                lcd.image(render(game))
                sleep(max(0, 1 / 30 - (monotonic() - now)))
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
