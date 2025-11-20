#!/usr/bin/env python3
"""
EMx Millennium-Equation Evaluator
---------------------------------

Implements EMx-style diagnostics for the 7 Millennium Problems + No-Clone:

  Eq1  RH      – Riemann Hypothesis / Harmonic boundedness
  Eq2  PvsNP   – Reversibility / forbidden states
  Eq3  Hodge   – Alignment of indices / compatibility
  Eq4  YM      – Yang–Mills mass gap (positive energy floor)
  Eq5  NS      – Navier–Stokes smoothness (bounded Δ)
  Eq6  BSD     – Birch–Swinnerton–Dyer equilibrium / index match
  Eq7  Poincare – Contractibility back to T₀
  Eq8  NC      – No-Clone / uniqueness of lineage

From the EMx perspective, each is an invariant or inequality over an
EMx trajectory (sequence of EMx steps with α, β, γ, ∅, energy, etc.)
evolving on the 96-tick lattice with null share ∅ ≈ 0.22.

This file is *not* a proof engine; it’s a concrete, executable skeleton that
expresses how each equation is monitored inside EMx.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
import math
import random


# ---------------------------------------------------------------------------
# Core EMx data structures
# ---------------------------------------------------------------------------

@dataclass
class EMxStep:
    """
    One tick of EMx evolution.

    Fields are chosen to mirror your harmonics and equation map:

      t           – tick index (0..95 within a loop, can be extended)
      alpha       – form metric α ∈ [0,1]
      beta        – drift metric β (class-escape tendency)
      gamma       – closure metric γ (return probability)
      null_share  – ∅(t), local null occupancy
      energy      – E(s_t) – generic “field energy”
      state_class – one of {"N0","N1","N2","N3","N4","N5"}
      phase       – Σ-accumulated phase φ(t)
      winding_idx – O₈-based local index (orbit / regime label)
      en_value    – EN(s_t) – some scalar “equivalence node” score
      lineage_id  – Ω hash surrogate for no-clone checks
    """
    t: int
    alpha: float
    beta: float
    gamma: float
    null_share: float
    energy: float
    state_class: str
    phase: float
    winding_idx: int
    en_value: float
    lineage_id: int


@dataclass
class EMxTrajectory:
    """A finite sequence of EMx steps across ticks."""
    steps: List[EMxStep]

    def __iter__(self):
        return iter(self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    def time_window(self) -> Tuple[int, int]:
        if not self.steps:
            return (0, 0)
        return (self.steps[0].t, self.steps[-1].t)

    def mean_beta(self) -> float:
        return sum(s.beta for s in self.steps) / max(1, len(self.steps))

    def mean_null(self) -> float:
        return sum(s.null_share for s in self.steps) / max(1, len(self.steps))

    def energy_floor(self) -> float:
        return min(s.energy for s in self.steps) if self.steps else 0.0

    def max_energy_jump(self) -> float:
        if len(self.steps) < 2:
            return 0.0
        return max(
            abs(self.steps[i+1].energy - self.steps[i].energy)
            for i in range(len(self.steps)-1)
        )

    def max_state_class(self) -> str:
        """
        Rough “peak complexity” as the max N-class encountered by index:
        N0=0 ... N5=5; returns the class with max index seen.
        """
        order = {"N0": 0, "N1": 1, "N2": 2, "N3": 3, "N4": 4, "N5": 5}
        best = "N0"
        best_order = -1
        for s in self.steps:
            o = order.get(s.state_class, -1)
            if o > best_order:
                best_order = o
                best = s.state_class
        return best

    def delta_norm_bound(self) -> float:
        """
        Navier–Stokes-like “Δs bounded”: we approximate by looking at
        per-step differences in (alpha, beta, gamma, null_share, energy)
        and returning the maximum L2 norm of those jumps.
        """
        if len(self.steps) < 2:
            return 0.0
        max_norm = 0.0
        for a, b in zip(self.steps, self.steps[1:]):
            dv = (
                (a.alpha - b.alpha),
                (a.beta - b.beta),
                (a.gamma - b.gamma),
                (a.null_share - b.null_share),
                (a.energy - b.energy),
            )
            norm = math.sqrt(sum(x*x for x in dv))
            max_norm = max(max_norm, norm)
        return max_norm

    def closure_error(self) -> float:
        """
        Poincaré / closure: compare first and last state in a simple way.
        0 means perfect contractibility back to T₀; larger means worse.
        """
        if len(self.steps) < 2:
            return 0.0
        a = self.steps[0]
        b = self.steps[-1]
        dv = (
            (a.alpha - b.alpha),
            (a.beta - b.beta),
            (a.gamma - b.gamma),
            (a.null_share - b.null_share),
            (a.energy - b.energy),
        )
        return math.sqrt(sum(x*x for x in dv))


# ---------------------------------------------------------------------------
# Equation reports
# ---------------------------------------------------------------------------

@dataclass
class EquationReport:
    name: str
    code: str
    satisfied: bool
    metrics: Dict[str, float]
    notes: str

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Base class for EMx equations
# ---------------------------------------------------------------------------

class EMxEquation:
    """Abstract base for all EMx equation-checkers."""

    code: str = "Eq?"
    name: str = "Abstract Equation"

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Eq1 – Riemann Hypothesis / Harmonic (RH)
# ---------------------------------------------------------------------------

class Eq1_RH(EMxEquation):
    """
    EMx RH view:
      - φ(t) (phase) is harmonically bounded on the 96-tick lattice.
      - β(t) (ray offset) averages to ~0 over a loop.
      - γ(t) (closure) stays above a threshold (≈0.992 in your table).

    We check:
      * |<β>| small,
      * γ_min ≥ gamma_min,
      * phase variance bounded.
    """
    code = "Eq1"
    name = "Riemann Hypothesis / Harmonic"

    def __init__(self,
                 max_abs_mean_beta: float = 0.02,
                 gamma_min: float = 0.992,
                 max_phase_var: float = 10.0):
        self.max_abs_mean_beta = max_abs_mean_beta
        self.gamma_min = gamma_min
        self.max_phase_var = max_phase_var

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        mean_beta = traj.mean_beta()
        gamma_min_val = min(s.gamma for s in traj.steps)
        phases = [s.phase for s in traj.steps]
        mean_phase = sum(phases) / len(phases)
        phase_var = sum((p - mean_phase)**2 for p in phases) / len(phases)

        ok = (
            abs(mean_beta) <= self.max_abs_mean_beta
            and gamma_min_val >= self.gamma_min
            and phase_var <= self.max_phase_var
        )

        notes = (
            "β(t) averages near 0 and γ(t) stays above threshold; "
            "phase remains harmonically bounded."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "mean_beta": mean_beta,
                "gamma_min": gamma_min_val,
                "phase_var": phase_var,
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq2 – P vs NP / Reversibility
# ---------------------------------------------------------------------------

class Eq2_P_vs_NP(EMxEquation):
    """
    EMx P vs NP view:
      - Local inverse f^{-1} should be computable on allowed region.
      - Certain forbidden states (2, 12, 14 in your extended map) or
        their EMx analogues should not appear in valid reversible loops.
      - EN(s_{t+1}) - EN(s_t) ≤ 0 along EN-coherent evolution.

    We approximate:
      * No “forbidden” N-class spike (e.g. N5 at wrong places).
      * Mean ΔEN ≤ 0 (non-increasing EN on average).
    """
    code = "Eq2"
    name = "P vs NP / Reversibility"

    def __init__(self,
                 forbid_classes: Optional[List[str]] = None,
                 allow_positive_en_drift: float = 1e-3):
        # You can customize which N-classes you treat as “forbidden”
        self.forbid_classes = forbid_classes or []
        self.allow_positive_en_drift = allow_positive_en_drift

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        # Forbidden-class presence
        forbidden_hits = sum(
            s.state_class in self.forbid_classes for s in traj.steps
        )

        # EN drift
        if len(traj.steps) < 2:
            mean_en_delta = 0.0
        else:
            deltas = [
                traj.steps[i+1].en_value - traj.steps[i].en_value
                for i in range(len(traj.steps) - 1)
            ]
            mean_en_delta = sum(deltas) / len(deltas)

        ok = (
            forbidden_hits == 0
            and mean_en_delta <= self.allow_positive_en_drift
        )

        notes = (
            "No forbidden null-classes encountered and EN drift is "
            "non-increasing on average, suggesting EMx-style reversibility."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "forbidden_hits": float(forbidden_hits),
                "mean_en_delta": mean_en_delta,
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq3 – Hodge / Alignment
# ---------------------------------------------------------------------------

class Eq3_Hodge(EMxEquation):
    """
    EMx Hodge view:
      - Alignment between index-like quantities ind(x) and ord(x).
      - Divergence and curl remain “compatible” with normalization.

    Here we treat:
      * winding_idx as a proxy for ind(x),
      * a quantized orbit-length-based quantity as ord(x),
      * and we demand they match statistically.

    This is very stylized but expresses the intended invariant.
    """
    code = "Eq3"
    name = "Hodge / Alignment"

    def __init__(self,
                 allowed_mismatch_rate: float = 0.05):
        self.allowed_mismatch_rate = allowed_mismatch_rate

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        # Toy “ord(x)” from phase – wrap phase/2π and scale
        mismatches = 0
        total = 0
        for s in traj.steps:
            approx_ord = int(round((s.phase / (2 * math.pi)) % 8))
            if approx_ord != s.winding_idx:
                mismatches += 1
            total += 1

        mismatch_rate = mismatches / max(1, total)
        ok = mismatch_rate <= self.allowed_mismatch_rate

        notes = (
            "Index-like winding label matches an order-like phase index "
            f"for most steps (mismatch_rate={mismatch_rate:.3f})."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "mismatch_rate": mismatch_rate,
                "total_steps": float(total),
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq4 – Yang–Mills / Mass Gap
# ---------------------------------------------------------------------------

class Eq4_YM(EMxEquation):
    """
    EMx YM view:
      - There is a positive energy gap: E(s_t) ≥ E₀ > 0.
      - Gap arises from normalization O₆ + Ω + ∅_* > 0.

    We check:
      * min(energy) ≥ energy_gap,
      * mean null_share near baseline.
    """
    code = "Eq4"
    name = "Yang–Mills / Mass Gap"

    def __init__(self,
                 energy_gap: float = 0.1,
                 null_baseline: float = 0.22,
                 null_tolerance: float = 0.05):
        self.energy_gap = energy_gap
        self.null_baseline = null_baseline
        self.null_tolerance = null_tolerance

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        e_floor = traj.energy_floor()
        mean_null = traj.mean_null()
        null_err = abs(mean_null - self.null_baseline)
        ok = (
            e_floor >= self.energy_gap
            and null_err <= self.null_tolerance
        )

        notes = (
            "Energy remains above a positive floor and null share hovers "
            "near the EMx baseline, consistent with a mass gap."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "energy_floor": e_floor,
                "mean_null": mean_null,
                "null_error": null_err,
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq5 – Navier–Stokes / Smoothness
# ---------------------------------------------------------------------------

class Eq5_NS(EMxEquation):
    """
    EMx NS view:
      - Temporal differences Δs_n are bounded (no blow-up).
      - Energy dissipation vs injection is controlled.

    We:
      * bound the L2 norm of Δ per tick,
      * bound max energy jumps.
    """
    code = "Eq5"
    name = "Navier–Stokes / Smoothness"

    def __init__(self,
                 max_delta_norm: float = 0.5,
                 max_energy_jump: float = 0.5):
        self.max_delta_norm = max_delta_norm
        self.max_energy_jump = max_energy_jump

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        d_norm = traj.delta_norm_bound()
        e_jump = traj.max_energy_jump()
        ok = (
            d_norm <= self.max_delta_norm
            and e_jump <= self.max_energy_jump
        )

        notes = (
            "Per-tick state changes and energy jumps remain bounded, "
            "indicating smooth EMx evolution (no blow-up)."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "delta_norm_bound": d_norm,
                "max_energy_jump": e_jump,
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq6 – BSD / Equilibrium
# ---------------------------------------------------------------------------

class Eq6_BSD(EMxEquation):
    """
    EMx BSD view:
      - Index(s_n) = harmonic_class(s_n) (ind(x) = ord(x)).
      - Equilibrium of topological vs harmonic labels.

    Here:
      * we treat winding_idx as index,
      * and a discrete “harmonic bucket” of phase as harmonic_class.
    """
    code = "Eq6"
    name = "Birch–Swinnerton–Dyer / Equilibrium"

    def __init__(self,
                 allowed_mismatch_rate: float = 0.05):
        self.allowed_mismatch_rate = allowed_mismatch_rate

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        mismatches = 0
        total = 0
        for s in traj.steps:
            # Harmonic bucket: 0..7 from phase, similar to Eq3 but can
            # be tuned differently if you like.
            harmonic_class = int(math.floor((s.phase / (2 * math.pi)) % 8))
            if harmonic_class != s.winding_idx:
                mismatches += 1
            total += 1

        mismatch_rate = mismatches / max(1, total)
        ok = mismatch_rate <= self.allowed_mismatch_rate

        notes = (
            "Topological and harmonic labels agree for most steps, "
            "consistent with EMx BSD alignment."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "mismatch_rate": mismatch_rate,
                "total_steps": float(total),
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq7 – Poincaré / Contractibility
# ---------------------------------------------------------------------------

class Eq7_Poincare(EMxEquation):
    """
    EMx Poincaré view:
      - Over a loop, the configuration is contractible back to T₀.
      - After some horizon K, s_{n+K} ~ T₀ (N0) up to homotopy.

    We:
      * check that closure_error is small,
      * and that we end in (or near) N0.
    """
    code = "Eq7"
    name = "Poincaré / Contractibility"

    def __init__(self,
                 max_closure_error: float = 0.3):
        self.max_closure_error = max_closure_error

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        cerr = traj.closure_error()
        final_class = traj.steps[-1].state_class
        ok = (
            cerr <= self.max_closure_error
            and final_class == "N0"
        )

        notes = (
            "Loop returns near its starting configuration and ends "
            "in stillpoint class N0, indicating contractibility."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "closure_error": cerr,
                "final_state_class": 1.0 if final_class == "N0" else 0.0,
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Eq8 – No-Clone / Uniqueness
# ---------------------------------------------------------------------------

class Eq8_NoClone(EMxEquation):
    """
    EMx No-Clone view:
      - Global injectivity: trajectories must not duplicate lineage state.
      - Ω hash uniqueness: no (lineage_id, phase, t) triple repeats.

    Here we:
      * require lineage_id uniqueness across steps,
      * plus a stronger check: (lineage_id, phase_bucket) never repeats.
    """
    code = "Eq8"
    name = "No-Clone / Uniqueness"

    def evaluate(self, traj: EMxTrajectory) -> EquationReport:
        if not traj.steps:
            return EquationReport(
                name=self.name,
                code=self.code,
                satisfied=False,
                metrics={},
                notes="Empty trajectory"
            )

        ids = [s.lineage_id for s in traj.steps]
        unique_ids = len(set(ids))
        id_collisions = len(ids) - unique_ids

        buckets_seen = set()
        bucket_collisions = 0
        for s in traj.steps:
            phase_bucket = int(math.floor((s.phase / (2 * math.pi)) * 1024))  # fine-ish bins
            key = (s.lineage_id, phase_bucket)
            if key in buckets_seen:
                bucket_collisions += 1
            else:
                buckets_seen.add(key)

        ok = (id_collisions == 0 and bucket_collisions == 0)

        notes = (
            "Lineage IDs and phase-bucket pairs remain unique, consistent "
            "with EMx No-Clone (Ω) discipline."
        )

        return EquationReport(
            name=self.name,
            code=self.code,
            satisfied=ok,
            metrics={
                "id_collisions": float(id_collisions),
                "bucket_collisions": float(bucket_collisions),
                "total_steps": float(len(traj.steps)),
            },
            notes=notes
        )


# ---------------------------------------------------------------------------
# Simple EMx-like trajectory simulator (you can swap in real dynamics)
# ---------------------------------------------------------------------------

STATE_CLASSES = ["N0", "N1", "N2", "N3", "N4", "N5"]

def simulate_emx_trajectory(
    ticks: int = 96,
    seed: int = 42,
) -> EMxTrajectory:
    """
    Very lightweight EMx-looking simulator to feed the equation-checkers.

    - β(t) oscillates around 0 with mild noise.
    - γ(t) is high (≈1) with small dips.
    - null_share(t) fluctuates around 0.22.
    - energy(t) bounded away from 0.
    - phase(t) walks with small steps.
    - winding_idx derived from phase with small jitter.
    - state_class cycles through N0..N3 mostly, rare N4/N5 spikes.
    - lineage_id unique per step (Ω-friendly).
    """
    rng = random.Random(seed)
    steps: List[EMxStep] = []

    phase = 0.0
    energy = 1.0
    for t in range(ticks):
        # Beta – small oscillation around 0
        beta = 0.02 * math.sin(2 * math.pi * t / ticks) + rng.uniform(-0.01, 0.01)

        # Gamma – high closure probability
        gamma = 0.992 + 0.005 * math.sin(4 * math.pi * t / ticks)

        # Null share – around 0.22
        null_share = 0.22 + rng.uniform(-0.03, 0.03)

        # Energy – above 0.1, small random walk
        energy += rng.uniform(-0.05, 0.05)
        energy = max(0.15, energy)

        # Alpha – correlated with |beta|
        alpha = min(1.0, abs(beta) * 3 + 0.3)

        # Phase – integrate small increments
        phase += 0.2 + rng.uniform(-0.05, 0.05)

        # Winding index – from phase
        winding_idx = int(math.floor((phase / (2 * math.pi)) % 8))

        # EN – slowly decreasing (for P vs NP flavor)
        en_value = 1.0 - 0.001 * t + rng.uniform(-0.002, 0.002)

        # State class – simple cycle with occasional bumps
        base_class = STATE_CLASSES[(t // 8) % 4]  # mostly N0..N3
        if rng.random() < 0.05:
            base_class = rng.choice(["N4", "N5"])
        state_class = base_class

        lineage_id = t  # unique per step in this synthetic example

        step = EMxStep(
            t=t,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            null_share=null_share,
            energy=energy,
            state_class=state_class,
            phase=phase,
            winding_idx=winding_idx,
            en_value=en_value,
            lineage_id=lineage_id,
        )
        steps.append(step)

    return EMxTrajectory(steps=steps)


# ---------------------------------------------------------------------------
# Combined evaluation for all 8 equations
# ---------------------------------------------------------------------------

def evaluate_all_equations(traj: EMxTrajectory) -> List[EquationReport]:
    """
    Run all EMx Millennium-equation checkers on a trajectory and return
    their reports.
    """
    eqs: List[EMxEquation] = [
        Eq1_RH(),
        Eq2_P_vs_NP(forbid_classes=["N4", "N5"]),
        Eq3_Hodge(),
        Eq4_YM(),
        Eq5_NS(),
        Eq6_BSD(),
        Eq7_Poincare(),
        Eq8_NoClone(),
    ]
    return [eq.evaluate(traj) for eq in eqs]


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------

def main() -> None:
    traj = simulate_emx_trajectory(ticks=96, seed=42)
    reports = evaluate_all_equations(traj)

    t0, t1 = traj.time_window()
    print(f"EMx trajectory: ticks {t0}..{t1}, steps={len(traj)}")
    print(f"mean_beta={traj.mean_beta():.4f}, mean_null={traj.mean_null():.4f}")
    print(f"energy_floor={traj.energy_floor():.4f}")
    print()

    for r in reports:
        status = "OK" if r.satisfied else "!!"
        print(f"[{status}] {r.code} – {r.name}")
        for k, v in r.metrics.items():
            print(f"    {k}: {v:.6f}")
        print(f"    notes: {r.notes}")
        print()


if __name__ == "__main__":
    main()
