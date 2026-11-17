"""Pillow renderer shared by the simulator and LCD adapter."""

import math

from PIL import Image, ImageDraw, ImageFont

from config import (
    DIFFICULTIES, GROUND, HEIGHT, MAX_HP, PLAYER_HEIGHT, PLAYER_WIDTH,
    SCENARIOS, SPIKE_HEIGHT, SPIKE_WIDTH, WIDTH,
)
from game import State
from levels import FACILITY_LABELS, FLOORS

INK = "#101a27"
PANEL = "#1a2a3a"
WHITE = "#f2f6f4"
MUTED = "#adc2cb"
MINT = "#6aefca"
AMBER = "#ffc866"
RED = "#ff7a80"
SMALL = ImageFont.load_default(size=10)
BODY = ImageFont.load_default(size=12)
LARGE = ImageFont.load_default(size=23)

FACILITY_COLORS = {
    "stairs": AMBER, "escalator": "#9bb6ff", "elevator": MINT,
    "wc": "#9bdbff", "wrong_exit": RED, "exit": MINT,
}
HEART = ((0, 2), (2, 0), (4, 0), (6, 2), (8, 0), (10, 0),
         (12, 2), (12, 5), (6, 11), (0, 5))


def text(draw, x, y, value, color=WHITE, font=BODY, anchor="mm"):
    draw.text((x, y), value, fill=color, font=font, anchor=anchor, align="center")


def clock(seconds):
    minutes, seconds = divmod(math.ceil(seconds), 60)
    return f"{minutes:02}:{seconds:02}"


def draw_hud(draw, game):
    draw.rectangle((0, 0, 239, 35), fill=INK)
    draw.line((0, 35, 239, 35), fill="#3a5666")
    hp_per_heart = MAX_HP // 5
    for index in range(5):
        x = 10 + 16 * index
        shape = [(x + dx, 12 + dy) for dx, dy in HEART]
        draw.polygon(shape, fill="#3c4c5c")
        fraction = min(1, max(0, (game.hp - index * hp_per_heart) / hp_per_heart))
        if fraction:
            # Clip the live part of the heart at the remaining HP fraction.
            mask = Image.new("1", (13, 12))
            ImageDraw.Draw(mask).polygon(HEART, fill=1)
            mask = mask.crop((0, 0, math.ceil(13 * fraction), 12))
            draw.bitmap((x, 12), mask, fill=RED)
    text(draw, 116, 17, FLOORS[game.floor], MINT)
    color = RED if game.time_left <= 15 else WHITE
    text(draw, 230, 13 if game.penalty > 0 else 17, f"TIME {clock(game.time_left)}",
         color, SMALL, "rm")
    if game.penalty > 0:
        text(draw, 230, 26, "x2", AMBER, SMALL, "rm")


def draw_facility(draw, facility, camera):
    x = round(facility.x - camera)
    if not -45 <= x <= WIDTH + 45:
        return
    kind = facility.kind
    color = RED if facility.broken else FACILITY_COLORS[kind]
    label = "E/V OUT" if facility.broken else FACILITY_LABELS[kind]
    sign_half = max(22, math.ceil(SMALL.getlength(label) / 2) + 5)
    draw.rectangle((x - 18, 128, x + 18, GROUND - 1), fill=INK, outline=color)
    draw.rectangle((x - sign_half, 110, x + sign_half, 126), fill=color)
    text(draw, x, 118, label, INK, SMALL)

    if kind in ("stairs", "escalator"):
        draw.line((x - 11, 175, x - 4, 175, x - 4, 167, x + 3, 167,
                   x + 3, 159, x + 10, 159), fill=color, width=2)
        if kind == "escalator":
            draw.line((x - 10, 164, x + 10, 145), fill=color, width=2)
    elif kind in ("elevator", "exit", "wrong_exit"):
        draw.rectangle((x - 11, 146, x + 11, GROUND - 1), fill=PANEL, outline=color)
        draw.line((x, 147, x, GROUND - 1), fill=color)
        if facility.broken or kind == "wrong_exit":
            draw.line((x - 7, 154, x + 7, 169), fill=color, width=2)
            draw.line((x + 7, 154, x - 7, 169), fill=color, width=2)
    else:
        draw.ellipse((x - 9, 149, x + 9, 167), outline=color, width=2)
        text(draw, x, 158, "WC", color, SMALL)


def draw_player(draw, game):
    x = round(game.player_x - game.camera_x)
    y = round(game.feet_y) - PLAYER_HEIGHT
    half = PLAYER_WIDTH // 2
    airborne = game.feet_y < GROUND or game.velocity_y < 0
    stride = 2 if int(game.walk_distance / 6) % 2 else 0
    draw.rectangle((x - half + 2, y, x + half - 3, y + 6), fill="#f2bf98")
    draw.rectangle((x - half + 1, y, x + half - 2, y + 2), fill=INK)
    draw.point((x + 2 * game.facing, y + 4), fill=INK)
    draw.rectangle((x - half, y + 7, x + half - 1, y + 15), fill=MINT)
    draw.rectangle((x - half, y + 13, x + half - 1, y + 15), fill="#238c7f")
    draw.rectangle((x - 4, y + 16, x - 1, y + 21 - (3 if airborne else stride)), fill=INK)
    draw.rectangle((x + 1, y + 16, x + 4, y + 21 - (2 - stride if not airborne else 1)),
                   fill="#33546d")


def draw_station(draw, game):
    camera = game.camera_x
    draw.rectangle((0, 36, 239, 185), fill=("#3a5860", "#415364", "#56777b")[game.floor])
    draw.rectangle((0, 49, 239, 57), fill=PANEL)
    draw.line((0, 57, 239, 57), fill="#6b9196")
    for y in (84, 105, 145, 165):
        draw.line((0, y, 239, y), fill="#4e6c75")
    for world_x in range(0, game.world_width, 120):
        x = round(world_x - camera)
        if -120 <= x <= WIDTH:
            draw.rectangle((x, 58, x + 9, GROUND - 1), fill="#294451")
            draw.line((x + 9, 58, x + 9, GROUND - 1), fill="#78989b")
            draw.rectangle((x + 29, 65, x + 89, 79), fill=PANEL)
            text(draw, x + 59, 72, f"{FLOORS[game.floor]}  /  LINE 01", MUTED, SMALL)
    draw.rectangle((0, GROUND, 239, 209), fill="#233c48")
    draw.line((0, GROUND, 239, GROUND), fill=AMBER, width=2)
    for world_x in range(0, game.world_width, 20):
        x = round(world_x - camera)
        if 0 <= x < WIDTH:
            draw.line((x, 195, x, 208), fill="#375462")
    for facility in game.facilities[game.floor]:
        draw_facility(draw, facility, camera)
    for center in game.spikes:
        x = round(center - camera) - SPIKE_WIDTH // 2
        if -SPIKE_WIDTH < x < WIDTH:
            for index in range(3):
                left = x + round(index * SPIKE_WIDTH / 3)
                right = x + round((index + 1) * SPIKE_WIDTH / 3)
                draw.polygon(((left, GROUND), ((left + right) // 2, GROUND - SPIKE_HEIGHT),
                              (right, GROUND)), fill=RED)
    draw_player(draw, game)
    draw_hud(draw, game)
    draw.rectangle((0, 210, 239, 239), fill=INK)
    text(draw, 120, 225, game.prompt, MINT, SMALL)


def draw_options(draw, title, labels, selected, top, spacing):
    text(draw, 120, 28, title, MINT, LARGE)
    for index, label in enumerate(labels):
        y = top + index * spacing
        if index == selected:
            draw.rectangle((25, y - 10, 214, y + 10), fill=MINT)
        text(draw, 120, y, label, INK if index == selected else WHITE)
    text(draw, 120, 225, "A: SELECT     B: BACK", MUTED, SMALL)


def render(game):
    image = Image.new("RGB", (WIDTH, HEIGHT), INK)
    draw = ImageDraw.Draw(image)
    state = game.state

    if state in (State.PLAYING, State.FACILITY_MENU):
        draw_station(draw, game)
        if state is State.FACILITY_MENU:
            draw.rectangle((40, 52, 199, 195), fill=PANEL, outline=MINT, width=2)
            text(draw, 120, 75, "GO UP?", MINT, LARGE)
            for index, label in enumerate(("UP", "DOWN")):
                y = 110 + index * 28
                selected = game.direction == index
                if selected:
                    draw.rectangle((60, y - 11, 179, y + 11), fill=MINT)
                text(draw, 120, y, label, INK if selected else WHITE)
            text(draw, 120, 174, "A: CONFIRM   B: CANCEL", MUTED, SMALL)
    elif state is State.SCENARIO:
        labels = [s.label for s in SCENARIOS.values()]
        offset = max(0, game.scenario_index - 4)
        draw_options(draw, "CHOOSE SCENARIO", labels[offset:offset + 5],
                     game.scenario_index - offset, 70, 28)
        text(draw, 120, 202, f"{game.scenario_index + 1} / {len(labels)}", MUTED, SMALL)
    elif state is State.DIFFICULTY:
        labels = [f"{name}   {clock(times[game.scenario.needs_wc])}"
                  for name, times in DIFFICULTIES.items()]
        draw_options(draw, "DIFFICULTY", labels, game.difficulty_index, 86, 35)
    else:
        draw.rectangle((12, 12, 227, 206), fill=PANEL, outline="#345165")
        draw.line((28, 59, 212, 59), fill="#345165")
        if state is State.TITLE:
            text(draw, 120, 41, "SUBWAY ESCAPE", MINT, LARGE)
            for index, (label, x) in enumerate(zip(FLOORS, (51, 120, 189))):
                y = 151 - index * 18
                color = (MUTED, AMBER, MINT)[index]
                if index:
                    draw.line((x - 69, y + 18, x, y), fill="#638493", width=2)
                draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)
                text(draw, x, y - 17, label, color, SMALL)
            text(draw, 120, 225, "A / ENTER: START", MINT, SMALL)
        elif state is State.INTRO:
            text(draw, 120, 39, game.scenario.label, MINT, LARGE)
            text(draw, 120, 82, f"{game.difficulty}  /  {clock(game.time_left)}", AMBER)
            draw.multiline_text((120, 115), game.scenario.goal, font=BODY,
                                fill=WHITE, anchor="mm", align="center", spacing=4)
            text(draw, 120, 174, "ARROWS: MOVE  A: JUMP  B: USE", MUTED, SMALL)
            text(draw, 120, 225, "A: PLAY     B: BACK", MINT, SMALL)
        elif state is State.CLEAR:
            text(draw, 120, 40, "GAME CLEAR", MINT, LARGE)
            text(draw, 120, 106, f"ARRIVAL TIME  {clock(game.elapsed)}")
            text(draw, 120, 135, f"HP  {game.hp} / {MAX_HP}")
            text(draw, 120, 225, "A: RESTART     B: MENU", MINT, SMALL)
        elif state is State.GAME_OVER:
            text(draw, 120, 40, "GAME OVER", RED, LARGE)
            text(draw, 120, 113, game.failure, WHITE)
            text(draw, 120, 225, "A: RETRY     B: MENU", MINT, SMALL)
    return image


# Keep the prototype's renderer entry point available.
draw_game = render
