"""
EMx Core Kernel - REFACTORED for Emergent Harmonics
Pure algebraic implementation - harmonics MEASURED not prescribed.
"""

from typing import Tuple, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
import math

# ═══════════════════════════════════════════════════════════════
# I. TERNARY ALPHABET (THE CARRIER)
# ═══════════════════════════════════════════════════════════════

class Polarity(Enum):
    """The three fundamental orientations"""
    MINUS_ZERO = -1
    ZERO = 0
    PLUS_ZERO = 1

    def __repr__(self):
        return {-1: "−0", 0: "0", 1: "+0"}[self.value]

    def __neg__(self):
        """Polarity negation"""
        return Polarity(-self.value)

    @property
    def magnitude(self):
        """All polarities have zero magnitude"""
        return 0

TernaryTriple = Tuple[Polarity, Polarity, Polarity]

# ═══════════════════════════════════════════════════════════════
# II. META-OPERATORS (THE ALGEBRA)
# ═══════════════════════════════════════════════════════════════

class MetaOperator:
    """Pure algebraic transformations on polarities"""

    @staticmethod
    def plus_inject(p: Polarity) -> Polarity:
        return Polarity.PLUS_ZERO

    @staticmethod
    def minus_inject(p: Polarity) -> Polarity:
        return Polarity.MINUS_ZERO

    @staticmethod
    def separate(p: Polarity) -> Set[Polarity]:
        if p == Polarity.ZERO:
            return {Polarity.MINUS_ZERO, Polarity.PLUS_ZERO}
        else:
            return {p}

    @staticmethod
    def compose_plus_minus() -> Polarity:
        return Polarity.PLUS_ZERO

    @staticmethod
    def compose_minus_plus() -> Polarity:
        return Polarity.MINUS_ZERO

    @staticmethod
    def collapse_separation(separated: Set[Polarity], bias: Polarity) -> Polarity:
        if bias == Polarity.PLUS_ZERO:
            return Polarity.PLUS_ZERO
        elif bias == Polarity.MINUS_ZERO:
            return Polarity.MINUS_ZERO
        else:
            return Polarity.ZERO

# ═══════════════════════════════════════════════════════════════
# III. NULL & PHASE (EMERGENT PROPERTIES)
# ═══════════════════════════════════════════════════════════════

@dataclass
class StateProperties:
    """Emergent properties of any state"""
    null_load: float = 0.0       # ✅ STARTS AT 0, EMERGES DYNAMICALLY
    phase: float = 0.0
    tick: int = 0

    def capacity(self) -> float:
        """Available capacity: C = 1 - ∅"""
        return 1.0 - self.null_load

# ═══════════════════════════════════════════════════════════════
# IV. N-STATE CLASSIFICATION (GEOMETRIC STRUCTURE)
# ═══════════════════════════════════════════════════════════════

class NullClass(Enum):
    """Geometric classification of states"""
    N0 = "Stillpoint"
    N1 = "Single-Bias"
    N2 = "Balanced-Pair"
    N3 = "Triple-Mixed"
    N4 = "Unbalanced-Pair"
    N5 = "All-Same"

def classify_state(triple: TernaryTriple) -> NullClass:
    """Pure function: geometric classification"""
    x, y, z = [p.value for p in triple]
    non_zeros = [p for p in [x, y, z] if p != 0]

    if len(non_zeros) == 0:
        return NullClass.N0

    if len(non_zeros) == 1:
        return NullClass.N1

    if len(non_zeros) == 2:
        return NullClass.N2 if non_zeros[0] * non_zeros[1] < 0 else NullClass.N4

    if all(p > 0 for p in non_zeros) or all(p < 0 for p in non_zeros):
        return NullClass.N5

    return NullClass.N3

def k_class(triple: TernaryTriple) -> int:
    """Count non-zero axes"""
    return sum(1 for p in triple if p.value != 0)

# ═══════════════════════════════════════════════════════════════
# V. HARMONIC METRICS (MEASURED FROM TRAJECTORY)
# ═══════════════════════════════════════════════════════════════

@dataclass
class Harmonics:
    """The five observables: α, β, γ, Ω, ∅"""
    alpha: float
    beta: float
    gamma: float
    omega: bool
    null_share: float

# THEORETICAL PREDICTIONS (for comparison only)
THEORETICAL_ALPHA = {0: 0.000, 1: 0.333, 2: 0.667, 3: 1.000}
THEORETICAL_BETA = {0: 0.000, 1: 0.180, 2: 0.420, 3: 0.720}
THEORETICAL_GAMMA = {0: 1.000, 1: 0.999, 2: 0.996, 3: 0.992}
THEORETICAL_NULL = 0.22

def compute_harmonics_measured(triple: TernaryTriple,
                               props: StateProperties,
                               history: List[TernaryTriple],
                               min_history: int = 10) -> Harmonics:
    """
    ✅ MEASURED harmonics from actual trajectory
    Falls back to theoretical only if insufficient history
    """
    k = k_class(triple)

    if len(history) < min_history:
        # Insufficient data - use theoretical as bootstrap
        return Harmonics(
            alpha=THEORETICAL_ALPHA[k],
            beta=THEORETICAL_BETA[k],
            gamma=THEORETICAL_GAMMA[k],
            omega=history.count(triple) <= 1,
            null_share=props.null_load
        )

    # ═══ MEASURE ALPHA: structural alignment ═══
    # Variance of k-class distribution over recent history
    recent = history[-min_history:]
    k_values = [k_class(s) for s in recent]
    k_mean = sum(k_values) / len(k_values)
    k_variance = sum((k - k_mean)**2 for k in k_values) / len(k_values)

    # Alpha = 1 - normalized_variance (high variance → low alignment)
    max_variance = 1.5  # Empirical normalization
    alpha_measured = 1.0 - min(k_variance / max_variance, 1.0)

    # ═══ MEASURE BETA: drift/curvature ═══
    # Rate of change between consecutive states
    if len(history) >= 2:
        changes = []
        for i in range(len(recent) - 1):
            s1, s2 = recent[i], recent[i+1]
            change = sum(abs(s2[j].value - s1[j].value) for j in range(3))
            changes.append(change)

        beta_measured = sum(changes) / len(changes) / 3.0  # Normalize to [0,1]
        beta_measured = min(beta_measured, 1.0)
    else:
        beta_measured = 0.0

    # ═══ MEASURE GAMMA: closure coherence ═══
    # How well does system return to starting regions?
    # Measure distance of current from most common state
    from collections import Counter
    state_counts = Counter(recent)
    most_common_state = state_counts.most_common(1)[0][0]

    distance = sum(abs(triple[i].value - most_common_state[i].value) for i in range(3))
    gamma_measured = 1.0 - (distance / 6.0)  # Max distance is 6 (all axes differ by 2)
    gamma_measured = max(0.0, min(1.0, gamma_measured))

    # ═══ MEASURE OMEGA: no-clone integrity ═══
    omega_measured = history.count(triple) <= 1

    return Harmonics(
        alpha=alpha_measured,
        beta=beta_measured,
        gamma=gamma_measured,
        omega=omega_measured,
        null_share=props.null_load
    )

# ═══════════════════════════════════════════════════════════════
# VI. OPERATORS (THE TEN KERNELS)
# ═══════════════════════════════════════════════════════════════

class O1_Delta:
    """Δ: Temporal difference"""
    @staticmethod
    def apply(s1: TernaryTriple, s2: TernaryTriple) -> TernaryTriple:
        result = tuple(
            Polarity(s2[i].value - s1[i].value) if abs(s2[i].value - s1[i].value) <= 1
            else Polarity.ZERO
            for i in range(3)
        )
        return result

class O2_Gradient:
    """∇: Gradient/divergence"""
    @staticmethod
    def apply(triple: TernaryTriple) -> TernaryTriple:
        if all(p.value == 0 for p in triple):
            return (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO)
        return triple

class O3_Rotation:
    """rot: Curl/rotation"""
    @staticmethod
    def apply(triple: TernaryTriple) -> TernaryTriple:
        return (triple[2], triple[0], triple[1])

class O4_Closure:
    """∮: Line integral"""
    @staticmethod
    def check(path: List[TernaryTriple]) -> bool:
        if not path:
            return True
        total = [0, 0, 0]
        for triple in path:
            for i in range(3):
                total[i] += triple[i].value
        return all(abs(t) <= 1 for t in total)

class O6_Normalize:
    """𝓝: Normalization"""
    @staticmethod
    def apply(triple: TernaryTriple) -> TernaryTriple:
        result = []
        for p in triple:
            if p.value > 0:
                result.append(Polarity.ZERO if p.value == 1 else Polarity.PLUS_ZERO)
            elif p.value < 0:
                result.append(Polarity.ZERO if p.value == -1 else Polarity.MINUS_ZERO)
            else:
                result.append(Polarity.ZERO)
        return tuple(result)

class O7_Exchange:
    """𝓢: Symmetry/exchange"""
    @staticmethod
    def apply(triple: TernaryTriple, axis: int = 0) -> TernaryTriple:
        result = list(triple)
        result[axis] = -result[axis]
        return tuple(result)

class O9_NoClone:
    """𝓘: No-clone check"""
    @staticmethod
    def check(triple: TernaryTriple, history: List[TernaryTriple]) -> bool:
        return history.count(triple) == 0

class O10_Integrate:
    """Σ: Phase accumulation"""
    @staticmethod
    def apply(triple: TernaryTriple, current_phase: float) -> float:
        k = k_class(triple)
        increment = k * 0.1
        return current_phase + increment

# ═══════════════════════════════════════════════════════════════
# VII. GATES (EQUIVALENCE NODES)
# ═══════════════════════════════════════════════════════════════

class Gate:
    """Equivalence node checker"""

    @staticmethod
    def check(triple: TernaryTriple, props: StateProperties,
             history: List[TernaryTriple]) -> Tuple[bool, str]:
        # Gate 1: Closure (O₄)
        if len(history) > 0 and not O4_Closure.check(history[-10:]):
            return False, "Closure failed (O₄)"

        # Gate 2: No-clone (O₉)
        if not O9_NoClone.check(triple, history):
            return False, "No-clone violated (O₉)"

        # Gate 3: Capacity (∅ check)
        if props.null_load > 0.78:
            return False, "NULL capacity exceeded"

        # Gate 4: Forbidden states
        forbidden = [
            (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO),
            (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.PLUS_ZERO),
            (Polarity.MINUS_ZERO, Polarity.ZERO, Polarity.PLUS_ZERO),
        ]
        if triple in forbidden:
            return False, "Forbidden state accessed"

        return True, "PASS"

# ═══════════════════════════════════════════════════════════════
# VIII. THE KERNEL (RECURSIVE CORE)
# ═══════════════════════════════════════════════════════════════

@dataclass
class EMxState:
    """Complete state: geometry + properties + history"""
    triple: TernaryTriple
    properties: StateProperties
    history: List[TernaryTriple]

    def __post_init__(self):
        self.null_class = classify_state(self.triple)
        self.k = k_class(self.triple)
        self.harmonics = compute_harmonics_measured(
            self.triple, self.properties, self.history
        )

    def gate_check(self) -> Tuple[bool, str]:
        return Gate.check(self.triple, self.properties, self.history)

class EMxKernel:
    """The recursive core with MEASURED harmonics"""

    def __init__(self, initial_triple: Optional[TernaryTriple] = None):
        if initial_triple is None:
            initial_triple = (Polarity.ZERO, Polarity.ZERO, Polarity.ZERO)

        self.state = EMxState(
            triple=initial_triple,
            properties=StateProperties(),
            history=[]
        )

    def step(self, operator: str, **kwargs) -> Tuple[bool, str]:
        """Execute one operator step"""
        self.state.history.append(self.state.triple)

        new_triple = self.state.triple

        if operator == 'O1':
            prev = kwargs.get('previous', self.state.triple)
            new_triple = O1_Delta.apply(prev, self.state.triple)

        elif operator == 'O2':
            new_triple = O2_Gradient.apply(self.state.triple)

        elif operator == 'O3':
            new_triple = O3_Rotation.apply(self.state.triple)

        elif operator == 'O6':
            new_triple = O6_Normalize.apply(self.state.triple)

        elif operator == 'O7':
            axis = kwargs.get('axis', 0)
            new_triple = O7_Exchange.apply(self.state.triple, axis)

        elif operator == 'O10':
            self.state.properties.phase = O10_Integrate.apply(
                self.state.triple,
                self.state.properties.phase
            )
            new_triple = self.state.triple

        else:
            return False, f"Unknown operator: {operator}"

        # ✅ EMERGENT NULL DYNAMICS
        k_old = k_class(self.state.triple)
        k_new = k_class(new_triple)

        # NULL increases with activity, decays toward baseline
        activity_delta = (k_new - k_old) * 0.05
        decay_rate = 0.1
        target_null = THEORETICAL_NULL

        self.state.properties.null_load = self.state.properties.null_load + activity_delta
        self.state.properties.null_load += decay_rate * (target_null - self.state.properties.null_load)
        self.state.properties.null_load = max(0.0, min(1.0, self.state.properties.null_load))

        self.state.properties.tick += 1

        self.state = EMxState(
            triple=new_triple,
            properties=self.state.properties,
            history=self.state.history
        )

        passes, reason = self.state.gate_check()
        return passes, reason

    def get_harmonics(self) -> Harmonics:
        """Get current harmonic measurements"""
        return self.state.harmonics

    def __repr__(self):
        t = self.state.triple
        return (f"EMx({t[0]}, {t[1]}, {t[2]}) "
                f"| {self.state.null_class.value} "
                f"| ∅={self.state.properties.null_load:.2f} "
                f"| φ={self.state.properties.phase:.2f}")

# ═══════════════════════════════════════════════════════════════
# IX. ENTRY POINTS (PROBLEM ENCODING)
# ═══════════════════════════════════════════════════════════════

class EntryPoint:
    """Maps external problems → EMx initial states"""

    @staticmethod
    def from_boolean(value: bool) -> TernaryTriple:
        if value:
            return (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO)
        else:
            return (Polarity.MINUS_ZERO, Polarity.ZERO, Polarity.ZERO)

    @staticmethod
    def from_integer(n: int) -> TernaryTriple:
        if n == 0:
            return (Polarity.ZERO, Polarity.ZERO, Polarity.ZERO)

        x = Polarity(max(-1, min(1, n % 3 - 1)))
        y = Polarity(max(-1, min(1, (n // 3) % 3 - 1)))
        z = Polarity(max(-1, min(1, (n // 9) % 3 - 1)))

        return (x, y, z)

    @staticmethod
    def from_vector(vec: List[float]) -> TernaryTriple:
        def sign_to_polarity(x):
            if x > 0:
                return Polarity.PLUS_ZERO
            elif x < 0:
                return Polarity.MINUS_ZERO
            else:
                return Polarity.ZERO

        return tuple(sign_to_polarity(vec[i]) if i < len(vec) else Polarity.ZERO
                    for i in range(3))
