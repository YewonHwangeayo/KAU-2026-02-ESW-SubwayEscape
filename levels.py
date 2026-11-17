"""Floor geometry and facility connections in world coordinates."""

from dataclasses import dataclass

FLOORS = ("B2", "B1", "1F")
WORLD_WIDTHS = (960, 960, 480)
STARTS = (50, 50, 50)
SPIKES = ((160, 420, 650), (140, 450, 700), (270,))
FACILITY_LABELS = {
    "stairs": "STAIR", "escalator": "ESC UP", "elevator": "E/V",
    "wc": "WC", "wrong_exit": "WRONG EXIT", "exit": "EXIT",
}
USE_LABELS = {
    **FACILITY_LABELS, "stairs": "STAIRS", "escalator": "ESCALATOR",
    "elevator": "ELEVATOR",
}


@dataclass(frozen=True)
class Facility:
    kind: str
    x: int
    arrival_x: int | None = None
    broken: bool = False


BASE_FACILITIES = (
    (Facility("stairs", 260, 220), Facility("escalator", 490, 520)),
    (
        Facility("stairs", 220, 82), Facility("wc", 320),
        Facility("escalator", 520, 120), Facility("wrong_exit", 620),
    ),
    (Facility("exit", 430),),
)


def facilities_for(difficulty):
    # The alternate car serves both underground floors independently.
    return (
        BASE_FACILITIES[0] + (
            Facility("elevator", 760, 760, broken=difficulty != "EASY"),
            Facility("elevator", 870, 870),
        ),
        BASE_FACILITIES[1] + (
            Facility("elevator", 760, 184), Facility("elevator", 870, 222),
        ),
        BASE_FACILITIES[2],
    )
