"""Logical buttons and a tkinter keyboard adapter."""

from dataclasses import dataclass

LEFT, RIGHT, UP, DOWN, A, B = "left", "right", "up", "down", "a", "b"
CONFIRM = "confirm"


@dataclass(frozen=True)
class InputState:
    held: frozenset[str] = frozenset()
    pressed: tuple[str, ...] = ()


KEYS = {
    "left": LEFT, "right": RIGHT, "up": UP, "down": DOWN,
    "a": A, "space": A, "b": B, "escape": B, "return": CONFIRM,
    "kp_enter": CONFIRM,
}


class Keyboard:
    def __init__(self, window):
        self.window = window
        self.down = set()
        self.events = []
        self.releases = {}
        window.bind("<KeyPress>", self._press)
        window.bind("<KeyRelease>", self._release)
        window.bind("<FocusOut>", self._clear)

    def _press(self, event):
        key = event.keysym.lower()
        button = KEYS.get(key)
        if button is None:
            return
        if key in self.releases:
            self.window.after_cancel(self.releases.pop(key))
        if key not in self.down:
            if all(KEYS[held] != button for held in self.down):
                self.events.append(button)
            self.down.add(key)
        return "break"

    def _release(self, event):
        key = event.keysym.lower()
        if key in self.down and key not in self.releases:
            # Coalesce synthetic release/press pairs from key repeat.
            self.releases[key] = self.window.after_idle(self._finish_release, key)

    def _finish_release(self, key):
        self.releases.pop(key)
        self.down.discard(key)

    def _clear(self, _event):
        for callback in self.releases.values():
            self.window.after_cancel(callback)
        self.releases.clear()
        self.down.clear()
        self.events.clear()

    def snapshot(self):
        state = InputState(frozenset(KEYS[key] for key in self.down), tuple(self.events))
        self.events.clear()
        return state
