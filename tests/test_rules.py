import unittest

from PIL import ImageColor

from buttons import A, B, CONFIRM, DOWN, LEFT, RIGHT, UP, InputState
from config import GROUND, SCENARIOS, SPIKE_HEIGHT, WALK_SPEED

from display import RED, render
from game import Game, State
from levels import SPIKES, STARTS


def press(game, button):
    game.update(0, InputState(pressed=(button,)))


def start(scenario="normal", difficulty=1):
    game = Game()
    press(game, CONFIRM)
    for _ in range(tuple(SCENARIOS).index(scenario)):
        press(game, DOWN)
    press(game, A)
    if difficulty != 1:
        press(game, UP if difficulty == 0 else DOWN)
    press(game, CONFIRM)
    press(game, A)
    return game


def use(game, x):
    game.player_x = x
    press(game, B)


def ride(game, x):
    use(game, x)
    press(game, A)


class RuleTests(unittest.TestCase):
    def test_all_menu_paths_and_time_limits(self):
        for scenario in SCENARIOS:
            for difficulty in range(3):
                with self.subTest(scenario=scenario, difficulty=difficulty):
                    game = start(scenario, difficulty)
                    self.assertIs(game.state, State.PLAYING)
                    limits = (90, 60, 45) if scenario == "toilet" else (150, 120, 90)
                    self.assertEqual(game.time_left, limits[difficulty])

    def test_spike_visibility_and_collision_on_each_floor(self):
        for key, scenario in SCENARIOS.items():
            for floor, positions in enumerate(SPIKES):
                with self.subTest(scenario=key, floor=floor):
                    game = start(key)
                    game.floor = floor
                    for spike in positions:
                        game.player_x = spike
                        image = render(game)
                        center = round(spike - game.camera_x)
                        region = image.crop((center - 13, GROUND - SPIKE_HEIGHT,
                                             center + 14, GROUND))
                        self.assertEqual(ImageColor.getrgb(RED) in {
                            color for _, color in region.getcolors()},
                            scenario.spikes_enabled)
                        old_time = game.time_left
                        game.update(0.005)
                        self.assertEqual(game.penalty, 5 if scenario.spikes_enabled else 0)
                        game.update(1)
                        self.assertAlmostEqual(
                            old_time - game.time_left, 2.005 if scenario.spikes_enabled else 1.005
                        )
                        game.update(5)

    def test_spike_edge_and_penalty_duration(self):
        game = start()
        game.player_x = SPIKES[0][0]
        game.update(0.005)
        time_left = game.time_left
        game.update(5)
        self.assertAlmostEqual(game.time_left, time_left - 10)
        self.assertAlmostEqual(game.penalty, 0)
        game.update(1)
        self.assertAlmostEqual(game.time_left, time_left - 11)
        game.player_x = 100
        game.update(0.01)
        game.player_x = SPIKES[0][0]
        game.update(0.005)
        self.assertEqual(game.penalty, 5)

    def test_cooldown_and_second_spike_refresh_without_stacking(self):
        game = start()
        game.player_x = 160
        game.update(0.005)
        game.player_x = 420
        game.update(0.2)
        self.assertAlmostEqual(game.penalty, 4.8)
        game.player_x = 300
        game.update(1)
        game.player_x = 420
        game.update(0.005)
        self.assertAlmostEqual(game.penalty, 5)
        old_time = game.time_left
        game.update(1)
        self.assertAlmostEqual(old_time - game.time_left, 2)

    def test_jump_clears_spike_and_cannot_repeat_midair(self):
        game = start()
        game.player_x = 122
        press(game, A)
        game.update(0.4, InputState(frozenset({RIGHT})))
        self.assertLess(game.feet_y, GROUND - SPIKE_HEIGHT)
        velocity = game.velocity_y
        press(game, A)
        self.assertEqual(game.velocity_y, velocity)
        game.update(0.5, InputState(frozenset({RIGHT})))
        self.assertEqual(game.feet_y, GROUND)
        self.assertEqual(game.penalty, 0)
        self.assertAlmostEqual(game.player_x, 203)
        game.update(0.1, InputState(frozenset({LEFT})))
        self.assertAlmostEqual(game.player_x, 194)
        self.assertEqual(game.facing, -1)

    def test_down_fails_and_b_cancels(self):
        game = start()
        use(game, 260)
        self.assertIs(game.state, State.FACILITY_MENU)
        press(game, B)
        self.assertIs(game.state, State.PLAYING)
        self.assertEqual(game.floor, 0)
        use(game, 260)
        press(game, DOWN)
        press(game, A)
        self.assertIs(game.state, State.GAME_OVER)
        self.assertIn("DOWN", game.failure)

    def test_accessible_routes_include_backup_elevator(self):
        for scenario in ("stroller", "limited_mobility"):
            for x in (260, 490):
                game = start(scenario)
                ride(game, x)
                self.assertEqual(game.failure, "ELEVATOR REQUIRED")
            for difficulty in range(3):
                game = start(scenario, difficulty)
                if difficulty:
                    use(game, 760)
                    self.assertIn("OUT OF SERVICE", game.prompt)
                    self.assertEqual(game.floor, 0)
                elevator = 870 if difficulty else 760
                ride(game, elevator)
                self.assertEqual((game.floor, game.player_x), (1, elevator))
                ride(game, elevator)
                self.assertEqual(game.floor, 2)
                self.assertIs(game.state, State.PLAYING)
                use(game, 430)
                self.assertIs(game.state, State.CLEAR)

    def test_all_scenarios_can_walk_to_exit_on_hard(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                game = start(scenario, 2)
                elevator_only = SCENARIOS[scenario].elevator_only
                targets = [870, 870] if elevator_only else [260, 220]
                if scenario == "toilet":
                    targets[1:1] = [320]
                targets.append(430)

                for x in targets:
                    delta = x - game.player_x
                    direction = RIGHT if delta >= 0 else LEFT
                    game.update(abs(delta) / WALK_SPEED, InputState(frozenset({direction})))
                    self.assertAlmostEqual(game.player_x, x)
                    press(game, B)
                    if game.state is State.FACILITY_MENU:
                        press(game, A)

                self.assertIs(game.state, State.CLEAR)
                self.assertGreater(game.time_left, 0)
                self.assertGreater(game.hp, 0)

    def test_health_costs_and_exhaustion(self):
        for scenario in ("luggage", "senior"):
            game = start(scenario)
            ride(game, 260)
            self.assertEqual(game.hp, 70)
            game.hp = 30
            ride(game, 220)
            self.assertEqual(game.hp, 0)
            self.assertEqual(game.failure, "OUT OF HEALTH")
        senior = start("senior")
        ride(senior, 490)
        self.assertEqual(senior.hp, 95)
        luggage = start("luggage")
        ride(luggage, 490)
        self.assertIs(luggage.state, State.GAME_OVER)
        self.assertIn("ESCALATOR", luggage.failure)

    def test_wc_required_without_timer_reset(self):
        for visit in (False, True):
            game = start("toilet")
            ride(game, 260)
            game.update(2)
            before = game.time_left
            if visit:
                use(game, 320)
            self.assertEqual(game.time_left, before)
            ride(game, 220)
            use(game, 430)
            self.assertIs(game.state, State.CLEAR if visit else State.GAME_OVER)

    def test_wrong_exit_returns_to_b1_spawn(self):
        for scenario in SCENARIOS:
            game = start(scenario)
            ride(game, 870)
            use(game, 620)
            self.assertEqual((game.floor, game.player_x), (1, STARTS[1]))
            self.assertEqual(game.hp, 90 if scenario in ("luggage", "senior") else 100)
            seconds = game.time_left
            game.update(1)
            self.assertAlmostEqual(game.time_left, seconds - 1)

    def test_timer_pause_expiry_and_retry(self):
        game = Game()
        game.update(100)
        self.assertEqual(game.time_left, 120)
        game = start()
        use(game, 260)
        game.update(121)
        self.assertEqual(game.time_left, 120)
        press(game, B)
        game.time_left = 0.5
        game.update(1)
        self.assertIs(game.state, State.GAME_OVER)
        self.assertEqual(game.time_left, 0)
        game.update(100)
        press(game, A)
        self.assertIs(game.state, State.INTRO)
        self.assertEqual(game.time_left, 120)
        game.update(30)
        self.assertEqual(game.time_left, 120)

    def test_render_all_states_without_simulation_mutation(self):
        game = start()
        for state in State:
            game.state = state
            before = dict(vars(game))
            self.assertEqual(render(game).size, (240, 240))
            self.assertEqual(vars(game), before)


if __name__ == "__main__":
    unittest.main()
