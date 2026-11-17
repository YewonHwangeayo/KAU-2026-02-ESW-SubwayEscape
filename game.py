"""Simulation and state transitions, independent of Tk and Pillow."""

from enum import Enum, auto

from buttons import A, B, CONFIRM, DOWN, LEFT, RIGHT, UP, InputState
from config import (
    DIFFICULTIES, GRAVITY, GROUND, HIT_COOLDOWN, JUMP_SPEED, MAX_HP,
    PLAYER_WIDTH, SCENARIOS, SPIKE_HEIGHT, SPIKE_PENALTY, SPIKE_WIDTH,
    USE_DISTANCE, WALK_SPEED, WIDTH,
)
from levels import SPIKES, STARTS, USE_LABELS, WORLD_WIDTHS, facilities_for


class State(Enum):
    TITLE = auto()
    SCENARIO = auto()
    DIFFICULTY = auto()
    INTRO = auto()
    PLAYING = auto()
    FACILITY_MENU = auto()
    CLEAR = auto()
    GAME_OVER = auto()


class Game:
    def __init__(self):
        self.state = State.TITLE
        self.scenario_index = 0
        self.difficulty_index = 1
        self._reset_run()

    @property
    def scenario(self):
        return tuple(SCENARIOS.values())[self.scenario_index]

    @property
    def difficulty(self):
        return tuple(DIFFICULTIES)[self.difficulty_index]

    @property
    def world_width(self):
        return WORLD_WIDTHS[self.floor]

    @property
    def camera_x(self):
        return min(max(0, self.player_x - WIDTH / 2), self.world_width - WIDTH)

    @property
    def spikes(self):
        return self.floor_spikes[self.floor]

    @property
    def nearby_facility(self):
        nearest = min(self.facilities[self.floor], key=lambda f: abs(f.x - self.player_x))
        return nearest if abs(nearest.x - self.player_x) <= USE_DISTANCE else None

    @property
    def prompt(self):
        if self.message_time > 0:
            return self.message
        facility = self.nearby_facility
        if facility is not None:
            return f"B: USE {USE_LABELS[facility.kind]}"
        if self.scenario.needs_wc and not self.wc_visited:
            if self.floor == 1:
                return "FIND WC"
            if self.floor == 2:
                return "WC MISSED  /  CHECK EXIT"
        if self.floor == 2:
            return "GO TO EXIT"
        if self.scenario.elevator_only:
            return "FIND AN ELEVATOR"
        if any(abs(x - self.player_x) < 110 for x in self.spikes):
            return "A: JUMP OVER SPIKES"
        return "FIND A WAY UP"

    def _reset_run(self):
        self.floor = 0
        self.player_x = STARTS[0]
        self.feet_y = GROUND
        self.velocity_y = 0.0
        self.facing = 1
        self.walk_distance = 0.0
        self.hp = MAX_HP
        self.time_limit = DIFFICULTIES[self.difficulty][self.scenario.needs_wc]
        self.time_left = float(self.time_limit)
        self.elapsed = 0.0
        self.wc_visited = False
        self.facilities = facilities_for(self.difficulty)
        self.floor_spikes = SPIKES if self.scenario.spikes_enabled else ((), (), ())
        self.spike_contacts = set()
        self.penalty = self.cooldown = 0.0
        self.selected_facility = None
        self.direction = 0
        self.message = self.failure = ""
        self.message_time = 0.0

    def update(self, dt, input_state=InputState()):
        # Account for wall-clock time using the state active since the last frame.
        if self.state is State.PLAYING:
            remaining_dt = max(0, dt)
            movement = int(RIGHT in input_state.held) - int(LEFT in input_state.held)
            while remaining_dt > 0 and self.state is State.PLAYING:
                step = min(remaining_dt, 1 / 120)
                self._advance(step, movement)
                remaining_dt -= step

        for button in input_state.pressed:
            previous = self.state
            self._handle_button(button)
            if self.state is not previous:
                break

    def _advance(self, dt, movement):
        extra = min(dt, self.penalty)
        self.elapsed += dt
        self.time_left = max(0, self.time_left - dt - extra)
        self.penalty = max(0, self.penalty - dt)
        self.cooldown = max(0, self.cooldown - dt)
        self.message_time = max(0, self.message_time - dt)
        if self.time_left <= 0:
            self._fail("TIME RAN OUT")
            return

        half_width = PLAYER_WIDTH / 2
        old_x = self.player_x
        self.player_x = min(self.world_width - half_width,
                            max(half_width, old_x + movement * WALK_SPEED * dt))
        if movement:
            self.facing = movement
        walked = abs(self.player_x - old_x)
        self.walk_distance = self.walk_distance + walked if walked else 0.0

        if self.feet_y < GROUND or self.velocity_y < 0:
            self.feet_y += self.velocity_y * dt + 0.5 * GRAVITY * dt ** 2
            self.velocity_y += GRAVITY * dt
            if self.feet_y >= GROUND:
                self.feet_y = GROUND
                self.velocity_y = 0.0

        if self.spikes:
            contacts = {
                x for x in self.spikes
                if abs(self.player_x - x) < half_width + SPIKE_WIDTH / 2
                and self.feet_y > GROUND - SPIKE_HEIGHT
            }
            if contacts - self.spike_contacts and self.cooldown == 0:
                self.penalty = float(SPIKE_PENALTY)
                self.cooldown = float(HIT_COOLDOWN)
            self.spike_contacts = contacts

    def _handle_button(self, button):
        confirm = button in (A, CONFIRM)
        if self.state is State.TITLE:
            if confirm:
                self.state = State.SCENARIO
        elif self.state is State.SCENARIO:
            self.scenario_index = self._select(button, self.scenario_index, len(SCENARIOS))
            if confirm:
                self.state = State.DIFFICULTY
            elif button == B:
                self.state = State.TITLE
        elif self.state is State.DIFFICULTY:
            self.difficulty_index = self._select(button, self.difficulty_index, len(DIFFICULTIES))
            if confirm:
                self._reset_run()
                self.state = State.INTRO
            elif button == B:
                self.state = State.SCENARIO
        elif self.state is State.INTRO:
            if confirm:
                self.state = State.PLAYING
            elif button == B:
                self.state = State.DIFFICULTY
        elif self.state is State.PLAYING:
            if button == A and self.feet_y == GROUND and self.velocity_y == 0:
                self.velocity_y = -JUMP_SPEED
            elif button == B:
                self._interact()
        elif self.state is State.FACILITY_MENU:
            if button in (UP, DOWN):
                self.direction = int(button == DOWN)
            elif confirm:
                self._use_transport()
            elif button == B:
                self.selected_facility = None
                self.state = State.PLAYING
        elif self.state in (State.CLEAR, State.GAME_OVER):
            if confirm:
                self._reset_run()
                self.state = State.INTRO
            elif button == B:
                self.state = State.SCENARIO

    @staticmethod
    def _select(button, index, count):
        if button in (UP, LEFT):
            return (index - 1) % count
        if button in (DOWN, RIGHT):
            return (index + 1) % count
        return index

    def _show(self, message):
        self.message = message
        self.message_time = 2.0

    def _fail(self, reason):
        self.failure = reason
        self.state = State.GAME_OVER

    def _damage(self, amount):
        self.hp = max(0, self.hp - amount)
        if self.hp == 0:
            self._fail("OUT OF HEALTH")

    def _arrive(self, x):
        self.player_x = x
        self.feet_y = GROUND
        self.velocity_y = self.walk_distance = 0.0
        self.spike_contacts.clear()
        self.message_time = 0.0

    def _interact(self):
        facility = self.nearby_facility
        if facility is None:
            self._show("NO FACILITY NEARBY")
        elif facility.broken:
            self._show("OUT OF SERVICE  /  E/V EAST")
        elif facility.kind == "wc":
            self.wc_visited = True
            self._show("WC VISITED  /  GO TO EXIT")
        elif facility.kind == "wrong_exit":
            self._arrive(STARTS[1])
            self._damage(10 if self.scenario.stair_damage else 0)
            self._show("WRONG EXIT  /  BACK TO START")
        elif facility.kind == "exit":
            if self.scenario.needs_wc and not self.wc_visited:
                self._fail("B1 WC WAS MISSED")
            else:
                self.state = State.CLEAR
        else:
            self.selected_facility = facility
            self.direction = 0
            self.state = State.FACILITY_MENU

    def _use_transport(self):
        facility = self.selected_facility
        self.selected_facility = None
        if self.direction == 1:
            self._fail("DOWN LEADS AWAY FROM EXIT")
            return
        if self.scenario.elevator_only and facility.kind != "elevator":
            self._fail("ELEVATOR REQUIRED")
            return
        if facility.kind == "escalator" and self.scenario.escalator_forbidden:
            self._fail("LUGGAGE: ESCALATOR BLOCKED")
            return

        self.state = State.PLAYING
        if facility.kind == "stairs":
            self._damage(self.scenario.stair_damage)
        elif facility.kind == "escalator":
            self._damage(self.scenario.escalator_damage)
        if self.state is State.PLAYING:
            self.floor += 1
            self._arrive(facility.arrival_x)
