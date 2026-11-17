"""Shared game constants and scenario rules."""

from dataclasses import dataclass

WIDTH = HEIGHT = 240
GROUND = 186
PLAYER_WIDTH = 12
PLAYER_HEIGHT = 22
WALK_SPEED = 90
GRAVITY = 600
JUMP_SPEED = 240
MAX_HP = 100
USE_DISTANCE = 24
SPIKE_WIDTH = 26
SPIKE_HEIGHT = 12
SPIKE_PENALTY = 5
HIT_COOLDOWN = 1

# Values are (standard seconds, toilet seconds).
DIFFICULTIES = {"EASY": (150, 90), "NORMAL": (120, 60), "HARD": (90, 45)}


@dataclass(frozen=True)
class Scenario:
    label: str
    goal: str
    spikes_enabled: bool = True
    elevator_only: bool = False
    stair_damage: int = 0
    escalator_damage: int = 0
    escalator_forbidden: bool = False
    needs_wc: bool = False


SCENARIOS = {
    "normal": Scenario("NORMAL", "Reach the 1F exit."),
    "luggage": Scenario(
        "LUGGAGE", "Use elevators when possible.\nAvoid escalators.",
        stair_damage=30, escalator_forbidden=True,
    ),
    "stroller": Scenario("STROLLER", "Use elevators only.", False, True),
    "senior": Scenario(
        "SENIOR", "Elevators save your health.", stair_damage=30, escalator_damage=5,
    ),
    "limited_mobility": Scenario("LIMITED MOBILITY", "Use elevators only.", False, True),
    "toilet": Scenario("NEED A TOILET", "Visit the B1 WC, then exit on 1F.", needs_wc=True),
}
