"""macOS tkinter simulator."""

import tkinter as tk
from time import monotonic

from PIL import ImageTk

from buttons import Keyboard
from config import HEIGHT, WIDTH
from display import render
from game import Game


def main():
    root = tk.Tk()
    root.title("Subway Escape")
    root.geometry(f"{WIDTH}x{HEIGHT}")
    root.resizable(False, False)

    label = tk.Label(root, borderwidth=0, highlightthickness=0)
    label.pack(fill="both", expand=True)
    root.after_idle(root.focus_set)
    label.bind("<Button-1>", lambda _event: root.focus_set())

    game = Game()
    keyboard = Keyboard(root)
    previous = monotonic()

    def update_screen():
        nonlocal previous
        now = monotonic()
        game.update(now - previous, keyboard.snapshot())
        previous = now
        photo = ImageTk.PhotoImage(render(game), master=root)
        label.configure(image=photo)
        label.image = photo
        root.after(33, update_screen)

    update_screen()
    root.mainloop()


if __name__ == "__main__":
    main()
