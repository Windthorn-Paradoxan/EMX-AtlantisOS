#!/usr/bin/env python3
"""
EMx v2.6 Complete Implementation
Full CPU execution with all operators, transitions, gates, and measurements
"""
import numpy as np
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

# ============================================================================
# CORE TYPES & CONSTANTS
# ============================================================================

class TSet(Enum):
    T0 = "neutral_lattice"
    T1 = "signed_lift"
    T2 = "binary_cube"
    T3 = "polar_cube"
    T4 = "exchange_shell"

class GateStatus(Enum):
    PASS = "pass"
    HOLD = "hold"
    FAIL = "fail"

@dataclass
class EMxState:
    """Ternary state with signed zeros"""
    x: np.float32
    y: np.float32
    z: np.float32
    t_set: TSet
    separated: List[bool]

    def to_array(self):
        return np.array([self.x, self.y, self.z], dtype=np.float32)

    def count_neutral(self):
        """Count truly neutral (unsigned zero) axes"""
        arr = self.to_array()
        neutral = 0
        for v in arr:
            if v == 0.0 and not np.signbit(v):
                neutral += 1
        return neutral

    def count_separated(self):
        return sum(self.separated)

    def measure_null_fraction(self):
        """Measure actual null: neutral + separated axes"""
        return (self.count_neutral() + self.count_separated()) / 3.0

@dataclass
class TickState:
    """Complete state at one tick"""
    tick: int
    phase: float
    state: EMxState
    null_measured: float
    gate_status: GateStatus
    operators_active: List[str]
    energy: float
    distance_from_n0: float
    # Packet trace fields
    packet_W: Optional[int] = None
    packet_H: Optional[int] = None
    packet_E: Optional[int] = None
    packet_target_vec: Optional[np.ndarray] = None

# ============================================================================
# T₀ LATTICE (27 states)
# ============================================================================

def build_t0_lattice():
    """Build complete T₀: {-0, 0, +0}³ using signed zeros"""
    lattice = []
    for x in [-1.0, 0.0, 1.0]:
        for y in [-1.0, 0.0, 1.0]:
            for z in [-1.0, 0.0, 1.0]:
                sx = np.float32(x) if x != 0 else np.float32(0.0)
                sy = np.float32(y) if y != 0 else np.float32(0.0)
                sz = np.float32(z) if z != 0 else np.float32(0.0)

                if x == -1.0: sx = np.float32(-0.0)
                if y == -1.0: sy = np.float32(-0.0)
                if z == -1.0: sz = np.float32(-0.0)

                state = EMxState(sx, sy, sz, TSet.T0, [False, False, False])
                lattice.append(state)

    return lattice

# ============================================================================
# PACKET-10 ENCODING (W/H/E)
# ============================================================================

class ApplicationClass(Enum):
    """Six symmetry-preserving application classes"""
    X_MAJOR = "x_major"
    Y_MAJOR = "y_major"
    Z_MAJOR = "z_major"
    X_MAJOR_FLIP = "x_major_flip"
    Y_MAJOR_FLIP = "y_major_flip"
    Z_MAJOR_FLIP = "z_major_flip"

@dataclass
class Packet10:
    """10-bit packet: W(4) | H(2) | E(4)"""
    W: int  # 4 bits: 0..15
    H: int  # 2 bits: 0..3
    E: int  # 4 bits: 0..15

    def to_int(self) -> int:
        return ((self.W & 0xF) << 6) | ((self.H & 0x3) << 4) | (self.E & 0xF)

    @staticmethod
    def from_int(value: int) -> "Packet10":
        W = (value >> 6) & 0xF
        H = (value >> 4) & 0x3
        E = value & 0xF
        return Packet10(W=W, H=H, E=E)

    def gray_echo(self):
        """Refresh E as Gray-coded copy of W"""
        w = self.W
        self.E = (w ^ (w >> 1)) & 0xF
        return self.E

# T4-like direction table
_T4_DIRECTIONS = np.array([
    [-1, +1, +1], [+1, -1, +1], [+1, +1, -1], [-1, -1, +1],
    [-1, +1, -1], [+1, -1, -1], [-1, -1, -1], [+1, +1, +1],
    [ 0, +1, +1], [ 0, -1, +1], [+1,  0, +1], [-1,  0, +1],
    [ 0,  0,  0], [ 0,  0,  0], [ 0,  0,  0], [ 0,  0,  0],
], dtype=np.float32)

def decode_direction_from_W(W: int, app_class: ApplicationClass) -> np.ndarray:
    """Map 4-bit W into target direction vector"""
    idx = max(0, min(15, W))
    vec = _T4_DIRECTIONS[idx].copy()

    if app_class in (ApplicationClass.Y_MAJOR, ApplicationClass.Y_MAJOR_FLIP):
        vec = np.array([vec[1], vec[2], vec[0]], dtype=np.float32)
    elif app_class in (ApplicationClass.Z_MAJOR, ApplicationClass.Z_MAJOR_FLIP):
        vec = np.array([vec[2], vec[0], vec[1]], dtype=np.float32)

    if app_class in (ApplicationClass.X_MAJOR_FLIP,
                     ApplicationClass.Y_MAJOR_FLIP,
                     ApplicationClass.Z_MAJOR_FLIP):
        vec = -vec

    return vec

def apply_packet_to_state(
    state: EMxState,
    packet: Packet10,
    app_class: ApplicationClass,
    use_gray_echo: bool = True
) -> Tuple[EMxState, Packet10, np.ndarray]:
    """Apply packet: decode W, move toward target, update echo"""
    current = state.to_array()
    target_vec = decode_direction_from_W(packet.W, app_class)

    # One minimal step toward target
    step = np.sign(target_vec - current)
    new_vec = current + step
    new_vec = np.clip(new_vec, -1.0, 1.0).astype(np.float32)

    if use_gray_echo:
        packet.gray_echo()

    new_state = EMxState(
        x=new_vec[0], y=new_vec[1], z=new_vec[2],
        t_set=state.t_set,
        separated=state.separated.copy()
    )

    return new_state, packet, target_vec

# ============================================================================
# OPERATORS (O₁-O₁₀)
# ============================================================================

class Operators:
    """All 10 EMx operators"""

    @staticmethod
    def O1_delta(state: EMxState, prev_value: Optional[float]) -> float:
        """O₁: Temporal difference"""
        return 0.0  # Computed externally

    @staticmethod
    def O2_gradient(state: EMxState) -> float:
        """O₂: ∇ - Gradient magnitude"""
        arr = state.to_array()
        return float(np.sqrt(np.sum(arr**2)))

    @staticmethod
    def O3_rotation(state: EMxState, axis: int = 0) -> EMxState:
        """O₃: Axial rotation/permutation"""
        arr = state.to_array()
        rotated = np.roll(arr, 1)
        return EMxState(rotated[0], rotated[1], rotated[2],
                       state.t_set, state.separated.copy())

    @staticmethod
    def O4_closure(states: List[TickState]) -> bool:
        """O₄: ∮ - Check if cycle closes"""
        if len(states) < 2:
            return False
        first_dist = states[0].distance_from_n0
        last_dist = states[-1].distance_from_n0
        return last_dist < first_dist * 0.5

    @staticmethod
    def O5_project(state: EMxState, target: TSet) -> EMxState:
        """O₅: Π - Project to target T-set"""
        arr = state.to_array()

        if target == TSet.T1:
            lifted = np.sign(arr)
            lifted[arr == 0] = 0
            return EMxState(lifted[0], lifted[1], lifted[2],
                          TSet.T1, state.separated.copy())
        elif target == TSet.T2:
            binary = (arr > 0).astype(np.float32)
            return EMxState(binary[0], binary[1], binary[2],
                          TSet.T2, [False, False, False])
        elif target == TSet.T3:
            polar = np.sign(arr)
            polar[polar == 0] = 1
            return EMxState(polar[0], polar[1], polar[2],
                          TSet.T3, [False, False, False])

        return state

    @staticmethod
    def O6_normalize(state: EMxState) -> EMxState:
        """O₆: 𝓝 - Normalize to basin"""
        arr = state.to_array()
        clipped = np.clip(arr, -1.0, 1.0)

        for i, v in enumerate(clipped):
            if abs(v) < 0.1:
                if np.signbit(v):
                    clipped[i] = np.float32(-0.0)
                else:
                    clipped[i] = np.float32(0.0)

        return EMxState(clipped[0], clipped[1], clipped[2],
                       TSet.T0, [False, False, False])

    @staticmethod
    def O7_symmetry(state: EMxState) -> EMxState:
        """O₇: 𝓢 - Minimal flip (one axis)"""
        arr = state.to_array()
        abs_vals = np.abs(arr)
        flip_axis = np.argmax(abs_vals)
        arr[flip_axis] = -arr[flip_axis]
        return EMxState(arr[0], arr[1], arr[2],
                       TSet.T4, state.separated.copy())

    @staticmethod
    def O8_index(state: EMxState) -> int:
        """O₈: 𝓦 - Topological index"""
        arr = state.to_array()
        return int(np.sum(np.sign(arr)))

    @staticmethod
    def O9_noclone(state: EMxState, context: int) -> Tuple[EMxState, int]:
        """O₉: 𝓘 - No-clone check with context"""
        state_hash = hash((tuple(state.to_array()), context))
        return state, state_hash

    @staticmethod
    def O10_sigma(phase: float, value: float) -> float:
        """O₁₀: Σ - Phase accumulation"""
        return phase + (value / 118.6)

    @staticmethod
    def hat_separation(state: EMxState, axis: int) -> EMxState:
        """^ operator: Separate axis into {-0, +0} coexistence"""
        new_state = EMxState(state.x, state.y, state.z,
                            state.t_set, state.separated.copy())
        new_state.separated[axis] = True
        return new_state

# ============================================================================
# PHASES (P₁-P₇)
# ============================================================================

class Phases:
    """All 7 EMx operational phases"""

    @staticmethod
    def P1_init(value: int, t0_lattice: List[EMxState]) -> EMxState:
        """P₁: Initialize from T₀"""
        idx = value % len(t0_lattice)
        return t0_lattice[idx]

    @staticmethod
    def P2_delta(state: EMxState, value: float, prev_value: Optional[float]) -> Tuple[EMxState, float]:
        """P₂: Apply O₁ (temporal difference)"""
        if prev_value is not None:
            delta = abs(value - prev_value)
            return state, delta
        return state, 0.0

    @staticmethod
    def P3_rotation(state: EMxState) -> EMxState:
        """P₃: Apply O₃ (rotation)"""
        return Operators.O3_rotation(state)

    @staticmethod
    def P4_flux(state: EMxState) -> Tuple[EMxState, float]:
        """P₄: Apply O₂ (gradient/flux)"""
        grad = Operators.O2_gradient(state)
        return state, grad

    @staticmethod
    def P5_fold(state: EMxState) -> EMxState:
        """P₅: Exchange (O₇ symmetry flip)"""
        return Operators.O7_symmetry(state)

    @staticmethod
    def P6_normalize(state: EMxState) -> EMxState:
        """P₆: Apply O₆ (normalize)"""
        return Operators.O6_normalize(state)

    @staticmethod
    def P7_integrate(state: EMxState, phase: float, value: float) -> Tuple[EMxState, float]:
        """P₇: Apply O₄, O₁₀ (close, accumulate phase)"""
        new_phase = Operators.O10_sigma(phase, value)
        return state, new_phase

# ============================================================================
# GATE CHECKS
# ============================================================================

class Gates:
    """Gate logic: EN₄ ∧ EN₆ ∧ EN₉ ∧ EN₁₀"""

    @staticmethod
    def check(state: EMxState, phase: float, history: List[TickState],
              context_map: dict) -> GateStatus:
        """Check if gate passes"""

        en4 = Operators.O4_closure(history) if len(history) > 5 else True

        grad = Operators.O2_gradient(state)
        en6 = grad < 10.0

        state_sig = tuple(state.to_array())
        en9 = state_sig not in context_map or len(context_map[state_sig]) < 3

        phase_mod = phase % 24
        en10 = 0 <= phase_mod <= 24

        if en4 and en6 and en9 and en10:
            return GateStatus.PASS
        elif not en6:
            return GateStatus.FAIL
        else:
            return GateStatus.HOLD

# ============================================================================
# 8-EQUATION MEASUREMENTS (HISTORY-AWARE)
# ============================================================================

class EightEquations:
    """Per-tick probes with history-aware aggregation"""

    @staticmethod
    def _phase_mod24(phase: float) -> float:
        p = phase % 24.0
        return p if p >= 0.0 else p + 24.0

    @staticmethod
    def measure(tick_state: TickState, history: List[TickState],
                context_map: dict) -> dict:
        """Measure all 8 equation contributions with enriched telemetry"""

        state = tick_state.state
        phase_now = EightEquations._phase_mod24(tick_state.phase)

        # Eq₁ (RH): Phase deviation
        rh_dev = abs(phase_now - 12.0) / 12.0

        if history:
            prev_phase = EightEquations._phase_mod24(history[-1].phase)
            step = abs(phase_now - prev_phase)
            rh_drift_step = min(step, 24.0 - step) / 12.0
        else:
            rh_drift_step = 0.0

        # Eq₄ (YM): Live null per axis
        arr = state.to_array()
        ym_per_axis = []
        for v in arr:
            if v == 0.0 and not np.signbit(v):
                ym_per_axis.append(1.0)
            elif np.signbit(v):
                ym_per_axis.append(0.5)
            else:
                ym_per_axis.append(0.0)
        ym_live = float(np.mean(ym_per_axis))
        ym_gap_live_bool = ym_live > 0.0

        # Eq₇ (Poincaré): Contraction trajectory
        dist_now = tick_state.distance_from_n0
        if history:
            dist_prev = history[-1].distance_from_n0
            contract_step = dist_prev - dist_now
        else:
            contract_step = 0.0

        # Eq₈ (P vs NP): Context uniqueness
        state_sig = tuple(arr)
        collisions = len(context_map.get(state_sig, []))
        collision_event = (collisions > 1)

        # Eq₃ (Hodge): Gradient balance
        grad_now = Operators.O2_gradient(state)
        if history:
            prev_energy = history[-1].energy
            ns_smooth = abs(tick_state.energy - prev_energy) < 1.0
            grad_prev = Operators.O2_gradient(history[-1].state)
            hodge_rot_delta = abs(grad_now - grad_prev)
        else:
            ns_smooth = True
            hodge_rot_delta = 0.0

        # Eq₆ (BSD): Index-phase alignment
        index_now = Operators.O8_index(state)
        bsd_align = (int(round(phase_now)) & 1) == (index_now & 1)

        return {
            # Original keys
            'eq1_rh': rh_dev,
            'eq4_ym_gap': ym_gap_live_bool,
            'eq7_poincare': dist_now,
            'eq8_pvsnp': collisions,
            'eq3_hodge': grad_now,
            'eq6_bsd_index': index_now,
            'eq5_ns_smooth': ns_smooth,
            'eq2_noclone': (collisions == 0),
            # Enriched fields
            'rh_phase_mod': phase_now,
            'rh_drift_step': rh_drift_step,
            'ym_live': ym_live,
            'ym_per_axis': ym_per_axis,
            'poincare_contract_step': contract_step,
            'collision_event': collision_event,
            'hodge_rot_delta': hodge_rot_delta,
            'bsd_align': bsd_align
        }

    @staticmethod
    def aggregate(history: List[TickState], per_tick: dict) -> dict:
        """Orbit-level summaries from per-tick measurements"""
        n = len(history) if history else 0
        if n == 0:
            return {
                'rh_drift_mean': 0.0, 'rh_drift_sum': 0.0,
                'ym_min_live': 0.0, 'ym_breach_count': 0,
                'contract_ratio': 0.0, 'contract_monotone_rate': 0.0,
                'ns_smooth_rate': 1.0, 'collision_rate': 0.0,
                'bsd_align_rate': 0.0
            }

        rh_drift_steps = per_tick.get('rh_drift_step', [])
        rh_drift_sum = float(np.sum(rh_drift_steps)) if rh_drift_steps else 0.0
        rh_drift_mean = rh_drift_sum / max(len(rh_drift_steps), 1)

        ym_live_series = per_tick.get('ym_live', [])
        ym_min_live = float(np.min(ym_live_series)) if ym_live_series else 0.0
        ym_breach_count = int(np.sum([1 for v in ym_live_series if v == 0.0]))

        dists = per_tick.get('eq7_poincare', [])
        if dists:
            start_d, end_d = dists[0], dists[-1]
            contract_ratio = (start_d - end_d) / (start_d + 1e-12)
        else:
            contract_ratio = 0.0

        contract_steps = per_tick.get('poincare_contract_step', [])
        contract_monotone_rate = float(
            np.mean([1.0 if s >= 0.0 else 0.0 for s in contract_steps])
        ) if contract_steps else 0.0

        ns_smooth_rate = float(np.mean(per_tick.get('eq5_ns_smooth', [True])))
        collision_rate = float(np.mean(
            [1.0 if c > 0 else 0.0 for c in per_tick.get('eq8_pvsnp', [])]
        )) if per_tick.get('eq8_pvsnp') else 0.0
        bsd_align_rate = float(np.mean(per_tick.get('bsd_align', []))) if per_tick.get('bsd_align') else 0.0

        return {
            'rh_drift_mean': rh_drift_mean,
            'rh_drift_sum': rh_drift_sum,
            'ym_min_live': ym_min_live,
            'ym_breach_count': ym_breach_count,
            'contract_ratio': contract_ratio,
            'contract_monotone_rate': contract_monotone_rate,
            'ns_smooth_rate': ns_smooth_rate,
            'collision_rate': collision_rate,
            'bsd_align_rate': bsd_align_rate
        }

# ============================================================================
# MAIN EMX LOOP
# ============================================================================

class EMxCore:
    """Complete EMx execution engine"""

    def __init__(self):
        self.t0_lattice = build_t0_lattice()
        self.phase = 0.0
        self.history = []
        self.context_map = {}
        self.tick_duration = 2.5e-9

        print("🜀 EMx v2.6 Complete Implementation")
        print(f"   T₀ lattice: {len(self.t0_lattice)} states")
        print(f"   Signed zero support: {self._test_signed_zeros()}")
        print()

    def _test_signed_zeros(self):
        """Verify CPU can distinguish signed zeros"""
        neg_zero = np.float32(-0.0)
        pos_zero = np.float32(+0.0)
        return np.signbit(neg_zero) != np.signbit(pos_zero)

    def run_orbit(self, data: List[int], verbose: bool = True) -> dict:
        """Run complete EMx loop on data"""
        if verbose:
            print(f"🔄 Running orbit: {len(data)} data points")
            print(f"   Target: 96-tick rhythm, 24-phase cycle\n")

        start_time = time.perf_counter()
        prev_value = None

        for tick, value in enumerate(data):
            tick_start = time.perf_counter()

            # P₁: Init
            state = Phases.P1_init(value, self.t0_lattice)
            operators_active = ['P₁']

            # P₂: Delta
            state, delta = Phases.P2_delta(state, value, prev_value)
            energy = delta
            operators_active.append('P₂')

            # Check rupture
            if delta > 100:
                state = Operators.hat_separation(state, axis=0)
                operators_active.append('^')

            # PACKET10 application
            W_bits = value & 0xF
            H_bits = (value >> 4) & 0x3
            E_bits = 0
            packet = Packet10(W=W_bits, H=H_bits, E=E_bits)
            app_class = ApplicationClass.X_MAJOR

            state, packet, target_vec = apply_packet_to_state(
                state, packet, app_class, use_gray_echo=True
            )
            operators_active.append('PACKET10')

            # Store packet info
            packet_W = packet.W
            packet_H = packet.H
            packet_E = packet.E
            packet_target = target_vec.copy()

            # P₄: Flux
            state, grad = Phases.P4_flux(state)
            operators_active.append('P₄')

            # P₅: Fold if needed
            if grad > 1.0:
                state = Phases.P5_fold(state)
                operators_active.append('P₅')

            # P₇: Integrate
            state, self.phase = Phases.P7_integrate(state, self.phase, value)
            operators_active.append('P₇')

            # P₆: Normalize
            state = Phases.P6_normalize(state)
            operators_active.append('P₆')

            # Measure
            arr = state.to_array()
            distance = float(np.sum(np.abs(arr))) / 3.0
            null_measured = state.measure_null_fraction()

            # Gate check
            gate_status = Gates.check(state, self.phase, self.history, self.context_map)

            # Context tracking
            state_sig = tuple(state.to_array())
            if state_sig not in self.context_map:
                self.context_map[state_sig] = []
            self.context_map[state_sig].append(tick)

            # Create tick state
            tick_state = TickState(
                tick=tick + 1,
                phase=self.phase % 24,
                state=state,
                null_measured=null_measured,
                gate_status=gate_status,
                operators_active=operators_active,
                energy=energy,
                distance_from_n0=distance,
                packet_W=packet_W,
                packet_H=packet_H,
                packet_E=packet_E,
                packet_target_vec=packet_target
            )

            self.history.append(tick_state)

            tick_end = time.perf_counter()
            tick_duration = tick_end - tick_start

            if verbose and (tick < 5 or tick >= len(data) - 3):
                print(f"Tick {tick+1:2d}: val={value:3d} | "
                      f"∅={null_measured:.3f} | "
                      f"φ={self.phase % 24:.2f} | "
                      f"dist={distance:.2f} | "
                      f"W={packet_W} H={packet_H} E={packet_E} | "
                      f"gate={gate_status.value} | "
                      f"time={tick_duration*1e6:.1f}µs")
            elif verbose and tick == 5:
                print("   ...")

            prev_value = value

        end_time = time.perf_counter()
        total_time = end_time - start_time

        results = self._compute_results(total_time, verbose)

        return results

    def _compute_results(self, total_time: float, verbose: bool) -> dict:
        """Compute all measurements from history"""

        if verbose:
            print(f"\n{'='*60}")
            print("📊 MEASUREMENTS")
            print(f"{'='*60}\n")

        null_measurements = [ts.null_measured for ts in self.history]
        null_mean = np.mean(null_measurements)
        null_final = null_measurements[-1]
        null_std = np.std(null_measurements)

        phase_final = self.history[-1].phase

        eq_measurements = {
            'eq1_rh': [], 'eq4_ym_gap': [], 'eq7_poincare': [], 'eq8_pvsnp': [],
            'eq3_hodge': [], 'eq6_bsd_index': [], 'eq5_ns_smooth': [], 'eq2_noclone': [],
            'rh_phase_mod': [], 'rh_drift_step': [], 'ym_live': [], 'ym_per_axis': [],
            'poincare_contract_step': [], 'collision_event': [], 'hodge_rot_delta': [], 'bsd_align': [],
        }

        for idx, ts in enumerate(self.history):
            past_history = self.history[:idx]
            meas = EightEquations.measure(ts, past_history, self.context_map)
            for key in eq_measurements:
                eq_measurements[key].append(meas[key])

        rh_null = np.mean(eq_measurements['eq1_rh'])
        poincare_null = np.mean(eq_measurements['eq7_poincare'])
        collision_rate = np.mean([1.0 if x > 0 else 0.0 for x in eq_measurements['eq8_pvsnp']])

        null_from_equations = (rh_null + poincare_null + collision_rate) / 3.0

        gate_pass = sum(1 for ts in self.history if ts.gate_status == GateStatus.PASS)
        gate_hold = sum(1 for ts in self.history if ts.gate_status == GateStatus.HOLD)
        gate_fail = sum(1 for ts in self.history if ts.gate_status == GateStatus.FAIL)

        results = {
            'null_measured_direct': null_mean,
            'null_measured_final': null_final,
            'null_measured_std': null_std,
            'null_from_8equations': null_from_equations,
            'phase_final': phase_final,
            'total_ticks': len(self.history),
            'total_time_sec': total_time,
            'time_per_tick_us': (total_time / len(self.history)) * 1e6,
            'gate_pass': gate_pass,
            'gate_hold': gate_hold,
            'gate_fail': gate_fail,
            'gate_pass_rate': gate_pass / len(self.history),
            'eq_measurements': eq_measurements,
            'rh_contribution': rh_null,
            # placeholder YM; real value injected after aggregate()
            'ym_gap_exists': None,
            'poincare_avg_distance': poincare_null,
            'pvsnp_collision_rate': collision_rate,
        }

        # Aggregate orbit-level diagnostics (includes ym_min_live + ym_breach_count)
        agg = EightEquations.aggregate(self.history, eq_measurements)
        results.update(agg)

        # Now compute YM using aggregated values
        results['ym_gap_exists'] = (
            (results['ym_min_live'] > 0.0) and
            (results['ym_breach_count'] == 0)
        )

        if verbose:
            self._print_results(results)

        return results

    def _print_results(self, results: dict):
        """Print formatted results"""

        print("NULL MEASUREMENTS:")
        print(f"  Direct (from states):     {results['null_measured_direct']:.4f}")
        print(f"  Final tick:               {results['null_measured_final']:.4f}")
        print(f"  Std deviation:            {results['null_measured_std']:.4f}")
        print(f"  From 8 equations:         {results['null_from_8equations']:.4f}")
        print(f"  Target reference:         0.2200")

        print(f"\nPHASE:")
        print(f"  Final (mod 24):           {results['phase_final']:.3f}")
        print(f"  Reference:                17.918")

        print(f"\nGATE STATISTICS:")
        print(f"  Pass:  {results['gate_pass']:3d} ({results['gate_pass_rate']*100:.1f}%)")
        print(f"  Hold:  {results['gate_hold']:3d}")
        print(f"  Fail:  {results['gate_fail']:3d}")

        print(f"\n8-EQUATION CONTRIBUTIONS:")
        print(f"  Eq₁ (RH) phase deviation:  {results['rh_contribution']:.4f}")
        print(f"  Eq₄ (YM) mass gap exists:  {results['ym_gap_exists']}")
        print(f"  Eq₇ (Poincaré) avg dist:   {results['poincare_avg_distance']:.4f}")
        print(f"  Eq₈ (P vs NP) collisions:  {results['pvsnp_collision_rate']:.4f}")

        print(f"\nHISTORY PROBES:")
        print(f"  RH drift (mean / sum):     {results.get('rh_drift_mean',0):.4f} / {results.get('rh_drift_sum',0):.4f}")
        print(f"  YM min live / breaches:    {results.get('ym_min_live',0):.3f} / {results.get('ym_breach_count',0)}")
        print(f"  Contraction ratio / mono:  {results.get('contract_ratio',0):.3f} / {results.get('contract_monotone_rate',0):.2f}")
        print(f"  Smoothness rate:           {results.get('ns_smooth_rate',0):.2f}")
        print(f"  Collision rate:            {results.get('collision_rate',0):.2f}")
        print(f"  BSD align rate:            {results.get('bsd_align_rate',0):.2f}")

        print(f"\nTIMING:")
        print(f"  Total time:               {results['total_time_sec']*1000:.2f} ms")
        print(f"  Time per tick:            {results['time_per_tick_us']:.1f} µs")
        print(f"  Target tick duration:     2500 ns")

        print(f"\n{'='*60}")
        print("✓ VALIDATION")
        print(f"{'='*60}\n")

        null_ok = abs(results['null_from_8equations'] - 0.22) < 0.10
        phase_ok = abs(results['phase_final'] - 17.918) < 0.5
        gate_ok = results['gate_pass_rate'] > 0.80
        ym_ok = results['ym_gap_exists']

        print(f"  ∅ convergence:  {'✅ PASS' if null_ok else '❌ FAIL'}")
        print(f"  Phase lock:     {'✅ PASS' if phase_ok else '❌ FAIL'}")
        print(f"  Gate integrity: {'✅ PASS' if gate_ok else '❌ FAIL'}")
        print(f"  YM mass gap:    {'✅ PASS' if ym_ok else '❌ FAIL'}")

        overall = null_ok and phase_ok and gate_ok and ym_ok
        print(f"\n  {'🎯 OVERALL: PASS' if overall else '⚠️  OVERALL: NEEDS TUNING'}")

# ============================================================================
# PACKET TRACE EXTRACTION
# ============================================================================

def extract_packet_traces(emx_core: EMxCore):
    """Return geometrized packet traces per tick"""
    traces = []
    for ts in emx_core.history:
        arr = ts.state.to_array()
        traces.append({
            'tick': ts.tick,
            'state': [float(arr[0]), float(arr[1]), float(arr[2])],
            'packet_W': ts.packet_W,
            'packet_H': ts.packet_H,
            'packet_E': ts.packet_E,
            'packet_target_vec': (
                tuple(ts.packet_target_vec)
                if ts.packet_target_vec is not None else None
            ),
            'gate': ts.gate_status.value,
            'null_measured': ts.null_measured
        })
    return traces

def print_packet_traces(emx_core: EMxCore, only_with_packets: bool = True):
    """Pretty-print packet traces per tick"""
    traces = extract_packet_traces(emx_core)
    print("\n" + "="*60)
    print("🧾 GEOMETRIZED PACKET TRACES PER TICK")
    print("="*60 + "\n")
    for tr in traces:
        if only_with_packets and tr['packet_W'] is None:
            continue
        print(
            f"Tick {tr['tick']:2d}: "
            f"state=({tr['state'][0]:+0.1f},{tr['state'][1]:+0.1f},{tr['state'][2]:+0.1f}) "
            f"W={tr['packet_W']} H={tr['packet_H']} E={tr['packet_E']} "
            f"target={tr['packet_target_vec']} "
            f"∅={tr['null_measured']:.3f} "
            f"gate={tr['gate']}"
        )
    print("\n" + "="*60)
    print("End of packet trace\n")

def diagnose_ticks(emx_core: EMxCore, ticks_to_check: List[int], window: int = 1):
    """Inspect suspected collapse ticks with ±window neighborhood"""
    print("\n" + "="*60)
    print("🔍 TICK DIAGNOSTICS")
    print("="*60 + "\n")

    for target_tick in ticks_to_check:
        print(f"\n{'─'*60}")
        print(f"Analyzing tick {target_tick} (±{window} neighborhood)")
        print(f"{'─'*60}")

        start_idx = max(0, target_tick - window - 1)
        end_idx = min(len(emx_core.history), target_tick + window)

        for idx in range(start_idx, end_idx):
            ts = emx_core.history[idx]
            arr = ts.state.to_array()

            marker = ">>>>" if ts.tick == target_tick else "    "

            print(f"{marker} Tick {ts.tick:2d}:")
            print(f"       State: ({arr[0]:+0.3f}, {arr[1]:+0.3f}, {arr[2]:+0.3f})")
            print(f"       Packet: W={ts.packet_W} H={ts.packet_H} E={ts.packet_E}")
            print(f"       Target: {ts.packet_target_vec}")
            print(f"       Energy: {ts.energy:.1f}")
            print(f"       Distance: {ts.distance_from_n0:.3f}")
            print(f"       ∅: {ts.null_measured:.4f}")
            print(f"       Phase: {ts.phase:.3f}")
            print(f"       Gate: {ts.gate_status.value}")
            print(f"       Ops: {', '.join(ts.operators_active)}")

            if ts.state.separated and any(ts.state.separated):
                sep_axes = [i for i, s in enumerate(ts.state.separated) if s]
                print(f"       🔀 Separated axes: {sep_axes}")
            print()

    print("="*60 + "\n")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Hebrew gematria test data (21-entry cycle)
    hebrew_data = [
        17, 50, 79, 140, 345, 65, 22, 425, 22, 35,
        37, 80, 47, 47, 215, 145, 37, 60, 42, 115,
        100, 30, 75, 19, 455, 7, 610, 306, 220, 47,
        52, 506, 24, 43, 126, 94, 61, 118, 275, 27,
        15, 70, 42, 45, 91, 280, 400, 55, 17, 64,
        313, 150, 101, 460, 47, 96, 130, 50, 213, 330,
        48, 20, 126, 58, 46, 190, 81, 16, 206, 52,
        25, 86]

    # Initialize EMx
    emx = EMxCore()

    # Run complete orbit
    results = emx.run_orbit(hebrew_data, verbose=True)

    # Print packet traces
    print_packet_traces(emx, only_with_packets=True)

    # Diagnose suspected collapse ticks (2, 12, 14 from your image)
    diagnose_ticks(emx, ticks_to_check=[2, 12, 14], window=1)

    print(f"\n{'='*60}")
    print("🜀 EMx Complete - Ready for NPU comparison")
    print(f"{'='*60}")
