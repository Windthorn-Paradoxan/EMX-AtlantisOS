from dataclasses import dataclass
import uuid
import random

# EMx alphabet and helpers

EMX_MINUS = "-0"
EMX_ZERO = "0"
EMX_PLUS = "+0"
EMX_VALUES = [EMX_MINUS, EMX_ZERO, EMX_PLUS]


@dataclass(frozen=True)
class T0State:
    x: str  # one of {-0, 0, +0}
    y: str
    z: str


@dataclass
class EMxState:
    t0: T0State         # polarity triple
    null_share: float   # ∅ in [0,1]
    energy: float       # coarse scalar
    lineage_id: str     # Ω – identity
    phase: float        # Σ – accumulated phase
    tick: int


def init_t0() -> T0State:
    return T0State(EMX_ZERO, EMX_ZERO, EMX_ZERO)


def random_axis_flip(t0: T0State) -> T0State:
    axis = random.choice(["x", "y", "z"])
    val = getattr(t0, axis)
    # simple 3-state rotation
    if val == EMX_ZERO:
        new_val = random.choice([EMX_MINUS, EMX_PLUS])
    elif val == EMX_PLUS:
        new_val = EMX_MINUS
    else:
        new_val = EMX_PLUS
    if axis == "x":
        return T0State(new_val, t0.y, t0.z)
    elif axis == "y":
        return T0State(t0.x, new_val, t0.z)
    else:
        return T0State(t0.x, t0.y, new_val)


def class_k(t0: T0State) -> int:
    # Number of non-zero axes after lift (k-class)
    count = 0
    for v in (t0.x, t0.y, t0.z):
        if v != EMX_ZERO:
            count += 1
    return count


def emx_init() -> EMxState:
    return EMxState(
        t0=init_t0(),
        null_share=0.22,      # baseline ∅
        energy=1.0,
        lineage_id=str(uuid.uuid4()),
        phase=0.0,
        tick=0
    )


# Lemniscate step: EMx = (s1, s2, NULL, s3, s4) conceptually.
# We fold that into one function that does:
#  P1 init → P2 Δ/flux → NULL crossing → P3 rot/exchange → P4 normalize/close → Σ


def emx_step(state: EMxState) -> EMxState:
    t0 = state.t0

    # 1) left lobe: small change in polarity (O₂/O₃ taste)
    t0_after_flux = random_axis_flip(t0)

    # 2) null dynamics: adjust ∅ by small stochastic term
    delta_null = (random.random() - 0.5) * 0.02
    new_null = min(1.0, max(0.0, state.null_share + delta_null))

    # 3) energy responds to how many axes are active (k-class)
    k = class_k(t0_after_flux)
    energy_decay = 0.01 + 0.02 * (k / 3.0)
    new_energy = max(0.0, state.energy - energy_decay)

    # 4) closure-like phase increment (Σ) – simple function of k and ∅
    d_phase = 0.1 * (k + 1) * (1.0 - new_null)
    new_phase = state.phase + d_phase

    # 5) tick advance
    return EMxState(
        t0=t0_after_flux,
        null_share=new_null,
        energy=new_energy,
        lineage_id=state.lineage_id,
        phase=new_phase,
        tick=state.tick + 1
    )


def emx_is_projection_window(state: EMxState) -> bool:
    # T₂ window approximation: every 8 ticks when null_share near baseline
    if state.tick % 8 != 0:
        return False
    return abs(state.null_share - 0.22) < 0.03


def emx_collapse_to_binary(state: EMxState):
    # T₂-style projection: lift ±0 → ±1, then sign>0→1, else 0
    def to_bit(v: str) -> int:
        if v == EMX_PLUS:
            return 1
        else:
            return 0  # treat {0, -0} as 0 for this example
    return (
        to_bit(state.t0.x),
        to_bit(state.t0.y),
        to_bit(state.t0.z),
    )


def run_emx(num_ticks: int = 50):
    state = emx_init()
    lineage_seen = set()  # Ω-like uniqueness check on (lineage, tick_bucket)

    for _ in range(num_ticks):
        # Ω: detect potential cloning in a coarse bucket
        bucket = (state.lineage_id, state.tick // 4)
        if bucket in lineage_seen:
            print(f"[Ω WARN] bucket collision at tick {state.tick}")
        else:
            lineage_seen.add(bucket)

        if emx_is_projection_window(state):
            out = emx_collapse_to_binary(state)
            print(
                f"[T={state.tick:02d}] T₂ window: "
                f"t0=({state.t0.x},{state.t0.y},{state.t0.z}), "
                f"∅={state.null_share:.3f}, E={state.energy:.3f}, "
                f"Σ={state.phase:.3f} -> binary={out}"
            )
        else:
            print(
                f"[T={state.tick:02d}] evolve: "
                f"t0=({state.t0.x},{state.t0.y},{state.t0.z}), "
                f"∅={state.null_share:.3f}, E={state.energy:.3f}, Σ={state.phase:.3f}"
            )

        state = emx_step(state)
