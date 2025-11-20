from dataclasses import dataclass
from enum import Enum, auto
import math
import uuid
import random


class Mode(Enum):
    IDLE = auto()
    ACTIVE = auto()
    UNCERTAIN = auto()
    COLLAPSED = auto()


@dataclass
class SystemState:
    x: float
    y: float
    z: float
    energy: float
    uncertainty: float  # 0..1
    mode: Mode
    history_id: str


def init_state() -> SystemState:
    return SystemState(
        x=0.0,
        y=0.0,
        z=0.0,
        energy=1.0,
        uncertainty=0.2,
        mode=Mode.IDLE,
        history_id=str(uuid.uuid4())
    )


def step_dynamics(s: SystemState) -> SystemState:
    # Random drift
    dx = (random.random() - 0.5) * 0.1
    dy = (random.random() - 0.5) * 0.1
    dz = (random.random() - 0.5) * 0.1

    x = s.x + dx
    y = s.y + dy
    z = s.z + dz

    # Energy decays slightly
    energy = max(0.0, s.energy - 0.01)

    # Uncertainty depends on motion magnitude
    motion_norm = math.sqrt(dx * dx + dy * dy + dz * dz)
    uncertainty = min(1.0, max(0.0, s.uncertainty + 0.5 * (motion_norm - 0.05)))

    # Determine mode
    if uncertainty < 0.1 and energy > 0.5:
        mode = Mode.ACTIVE
    elif uncertainty > 0.6:
        mode = Mode.UNCERTAIN
    else:
        mode = Mode.IDLE

    return SystemState(
        x=x,
        y=y,
        z=z,
        energy=energy,
        uncertainty=uncertainty,
        mode=mode,
        history_id=s.history_id
    )


def should_collapse(s: SystemState, tick: int) -> bool:
    # Example: collapse every 10 ticks if uncertainty is low enough
    if tick % 10 != 0:
        return False
    return s.uncertainty < 0.4 and s.energy > 0.2


def collapse_to_binary(s: SystemState):
    # Binary output based on sign of coordinates
    bx = 1 if s.x > 0 else 0
    by = 1 if s.y > 0 else 0
    bz = 1 if s.z > 0 else 0
    return (bx, by, bz)


def run_simulation(num_ticks: int = 50):
    s = init_state()
    seen_trajectories = set()  # crude no-clone check

    for t in range(num_ticks):
        s = step_dynamics(s)

        traj_key = (round(s.x, 3), round(s.y, 3), round(s.z, 3), s.mode)
        if traj_key in seen_trajectories:
            # Detect collision (no-clone style)
            print(f"[WARN] trajectory collision at tick {t}")
        else:
            seen_trajectories.add(traj_key)

        if should_collapse(s, t):
            out = collapse_to_binary(s)
            print(f"[T={t}] COLLAPSE -> {out} (energy={s.energy:.3f}, unc={s.uncertainty:.3f})")
        else:
            print(f"[T={t}] state=({s.x:.3f}, {s.y:.3f}, {s.z:.3f}), "
                  f"energy={s.energy:.3f}, unc={s.uncertainty:.3f}, mode={s.mode.name}")
