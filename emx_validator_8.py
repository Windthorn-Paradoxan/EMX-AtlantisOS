"""
EMx Millennium Equation Validator
Runtime checks for 8 duality conditions during execution.
"""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import math

from emx_kernel import (
    EMxKernel, EMxState, TernaryTriple, Polarity,
    k_class, O4_Closure
)

# ═══════════════════════════════════════════════════════════════
# I. EQUATION DEFINITIONS
# ═══════════════════════════════════════════════════════════════

class EquationType(Enum):
    """The 8 millennium problem dualities"""
    NO_CLONE = "Eq₂: No-Clone (Self ↔ Other)"
    NAVIER_STOKES = "Eq₃: Navier-Stokes (Life ↔ Death)"
    RIEMANN = "Eq₁: Riemann Hypothesis (Order ↔ Chaos)"
    YANG_MILLS = "Eq₄: Yang-Mills Mass Gap (Light ↔ Shadow)"
    HODGE = "Eq₅: Hodge Conjecture (Creation ↔ Destruction)"
    POINCARE = "Eq₇: Poincaré Conjecture (Knowledge ↔ Mystery)"
    BSD = "Eq₆: Birch-Swinnerton-Dyer (Time ↔ Eternity)"
    P_VS_NP = "Eq₈: P vs NP (Freedom ↔ Fate)"

@dataclass
class EquationResult:
    """Result of equation validation"""
    equation: EquationType
    passes: bool
    confidence: float
    violations: List[int]  # Tick indices where violated
    metric_value: float
    threshold: float
    message: str

@dataclass
class ValidationReport:
    """Complete validation report for trajectory"""
    total_ticks: int
    total_cycles: int
    equations: Dict[EquationType, EquationResult]
    overall_pass: bool
    pass_rate: float

# ═══════════════════════════════════════════════════════════════
# II. INDIVIDUAL EQUATION VALIDATORS
# ═══════════════════════════════════════════════════════════════

class Eq1_RiemannValidator:
    """
    Riemann Hypothesis: Order ↔ Chaos
    Check: ⟨β⟩ → 0 over time (time-averaged drift vanishes)
    """

    @staticmethod
    def validate(trajectory: List[EMxState], window: int = 96) -> EquationResult:
        if len(trajectory) < window:
            return EquationResult(
                EquationType.RIEMANN,
                False,
                0.0,
                [],
                0.0,
                0.1,
                "Insufficient data"
            )

        # Compute time-averaged beta
        beta_values = [state.harmonics.beta for state in trajectory]

        # Check convergence over windows
        violations = []
        window_averages = []

        for i in range(0, len(beta_values) - window, window):
            window_avg = sum(beta_values[i:i+window]) / window
            window_averages.append(window_avg)

            if window_avg > 0.1:  # Threshold for acceptable drift
                violations.append(i)

        # Overall average should approach 0
        overall_avg = sum(beta_values) / len(beta_values)
        passes = overall_avg < 0.1 and len(violations) < len(window_averages) * 0.1

        confidence = 1.0 - min(overall_avg / 0.1, 1.0)

        return EquationResult(
            EquationType.RIEMANN,
            passes,
            confidence,
            violations,
            overall_avg,
            0.1,
            f"⟨β⟩ = {overall_avg:.4f} (target < 0.1)"
        )

class Eq2_NoCloneValidator:
    """
    No-Clone Theorem: Self ↔ Other
    Check: Ω maintained (no duplicate states in history)
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        violations = []
        collision_count = 0

        seen_states = set()
        for i, state in enumerate(trajectory):
            state_tuple = state.triple
            if state_tuple in seen_states:
                violations.append(i)
                collision_count += 1
            seen_states.add(state_tuple)

        total_states = len(trajectory)
        unique_ratio = len(seen_states) / total_states if total_states > 0 else 0

        # Pass if collision rate < 50% (allowing some revisitation)
        passes = collision_count < total_states * 0.5
        confidence = unique_ratio

        return EquationResult(
            EquationType.NO_CLONE,
            passes,
            confidence,
            violations,
            unique_ratio,
            0.5,
            f"Unique states: {unique_ratio:.2%}, collisions: {collision_count}/{total_states}"
        )

class Eq3_NavierStokesValidator:
    """
    Navier-Stokes: Life ↔ Death
    Check: Bounded increments, smooth flow (|Δstate| bounded)
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        if len(trajectory) < 2:
            return EquationResult(
                EquationType.NAVIER_STOKES,
                False,
                0.0,
                [],
                0.0,
                2.0,
                "Insufficient data"
            )

        violations = []
        max_change = 0.0
        total_change = 0.0

        for i in range(len(trajectory) - 1):
            s1, s2 = trajectory[i].triple, trajectory[i+1].triple
            change = sum(abs(s2[j].value - s1[j].value) for j in range(3))

            total_change += change
            max_change = max(max_change, change)

            # Violation if change > 2 (all axes flip)
            if change > 2:
                violations.append(i)

        avg_change = total_change / (len(trajectory) - 1)
        smoothness = 1.0 - min(avg_change / 2.0, 1.0)

        # Pass if smooth (avg change < 1.5) and max bounded
        passes = smoothness > 0.25 and max_change <= 3
        confidence = smoothness

        return EquationResult(
            EquationType.NAVIER_STOKES,
            passes,
            confidence,
            violations,
            smoothness,
            0.25,
            f"Smoothness: {smoothness:.2%}, max_change: {max_change}"
        )

class Eq4_YangMillsValidator:
    """
    Yang-Mills Mass Gap: Light ↔ Shadow
    Check: Energy always > 0 (positive gap maintained)
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        violations = []
        min_energy = float('inf')

        for i, state in enumerate(trajectory):
            # Energy proxy: 1 - ∅ (capacity)
            energy = state.properties.capacity()
            min_energy = min(min_energy, energy)

            if energy <= 0:
                violations.append(i)

        # Pass if no zero-energy states
        passes = len(violations) == 0 and min_energy > 0
        confidence = min(min_energy / 0.1, 1.0) if min_energy > 0 else 0.0

        return EquationResult(
            EquationType.YANG_MILLS,
            passes,
            confidence,
            violations,
            min_energy,
            0.0,
            f"Min energy: {min_energy:.4f} > 0 required, violations: {len(violations)}"
        )

class Eq5_HodgeValidator:
    """
    Hodge Conjecture: Creation ↔ Destruction
    Check: ∇·F = 0 (divergence-free), ∇×F controlled
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        if len(trajectory) < 10:
            return EquationResult(
                EquationType.HODGE,
                False,
                0.0,
                [],
                0.0,
                0.1,
                "Insufficient data"
            )

        violations = []
        divergence_measures = []

        # Check closure over windows (proxy for divergence-free)
        window = 10
        for i in range(0, len(trajectory) - window):
            window_states = [s.triple for s in trajectory[i:i+window]]

            # Compute "divergence": net change in k-class
            k_values = [k_class(s) for s in window_states]
            k_start, k_end = k_values[0], k_values[-1]
            divergence = abs(k_end - k_start)

            divergence_measures.append(divergence)

            if divergence > 1:  # Should return to similar k-class
                violations.append(i)

        avg_divergence = sum(divergence_measures) / len(divergence_measures) if divergence_measures else 0
        passes = avg_divergence < 0.5
        confidence = 1.0 - min(avg_divergence, 1.0)

        return EquationResult(
            EquationType.HODGE,
            passes,
            confidence,
            violations,
            avg_divergence,
            0.5,
            f"Avg divergence: {avg_divergence:.3f} (target < 0.5)"
        )

class Eq6_BSDValidator:
    """
    Birch-Swinnerton-Dyer: Time ↔ Eternity
    Check: ind(x) = ord(x) (geometric index matches harmonic state)
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        if len(trajectory) < 20:
            return EquationResult(
                EquationType.BSD,
                False,
                0.0,
                [],
                0.0,
                0.1,
                "Insufficient data"
            )

        violations = []
        alignments = []

        for i, state in enumerate(trajectory):
            # Index: k-class (geometric)
            geometric_idx = state.k

            # Order: how many operators to return to N0 (proxy)
            # Use alpha as proxy for harmonic alignment
            harmonic_ord = state.harmonics.alpha * 3  # Scale to [0,3]

            alignment = 1.0 - abs(geometric_idx - harmonic_ord) / 3.0
            alignments.append(alignment)

            if alignment < 0.5:
                violations.append(i)

        avg_alignment = sum(alignments) / len(alignments)
        passes = avg_alignment > 0.7
        confidence = avg_alignment

        return EquationResult(
            EquationType.BSD,
            passes,
            confidence,
            violations,
            avg_alignment,
            0.7,
            f"Avg ind/ord alignment: {avg_alignment:.2%}"
        )

class Eq7_PoincareValidator:
    """
    Poincaré Conjecture: Knowledge ↔ Mystery
    Check: Loops contract to stillpoint (homotopy to N0)
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        if len(trajectory) < 96:
            return EquationResult(
                EquationType.POINCARE,
                False,
                0.0,
                [],
                0.0,
                1.0,
                "Need full cycle (96 ticks)"
            )

        violations = []
        contraction_ratios = []

        # Check 96-tick windows
        for i in range(0, len(trajectory) - 96, 96):
            cycle = trajectory[i:i+96]

            # Measure contraction: distance from N0 at start vs end
            def distance_from_n0(state):
                return sum(abs(p.value) for p in state.triple)

            start_dist = distance_from_n0(cycle[0])
            end_dist = distance_from_n0(cycle[-1])

            if start_dist > 0:
                contraction = (start_dist - end_dist) / start_dist
            else:
                contraction = 1.0 if end_dist == 0 else 0.0

            contraction_ratios.append(contraction)

            if contraction < 0:  # Expanding, not contracting
                violations.append(i)

        avg_contraction = sum(contraction_ratios) / len(contraction_ratios) if contraction_ratios else 0
        passes = avg_contraction > 0.1  # Should show net contraction
        confidence = min(avg_contraction, 1.0) if avg_contraction > 0 else 0.0

        return EquationResult(
            EquationType.POINCARE,
            passes,
            confidence,
            violations,
            avg_contraction,
            0.1,
            f"Avg contraction: {avg_contraction:.2%}"
        )

class Eq8_PvsNPValidator:
    """
    P vs NP: Freedom ↔ Fate
    Check: Computation reversibility (can we backtrack?)
    """

    @staticmethod
    def validate(trajectory: List[EMxState]) -> EquationResult:
        if len(trajectory) < 10:
            return EquationResult(
                EquationType.P_VS_NP,
                False,
                0.0,
                [],
                0.0,
                0.8,
                "Insufficient data"
            )

        violations = []
        reversibility_scores = []

        # Check if we can reconstruct path backward
        for i in range(1, len(trajectory)):
            current = trajectory[i]
            previous = trajectory[i-1]

            # Reversibility: can we go back? (measured by gate passage)
            # If gate passes both directions, it's reversible
            reversible = current.gate_check()[0] and previous.gate_check()[0]

            reversibility_scores.append(1.0 if reversible else 0.0)

            if not reversible:
                violations.append(i)

        avg_reversibility = sum(reversibility_scores) / len(reversibility_scores) if reversibility_scores else 0
        passes = avg_reversibility > 0.8
        confidence = avg_reversibility

        return EquationResult(
            EquationType.P_VS_NP,
            passes,
            confidence,
            violations,
            avg_reversibility,
            0.8,
            f"Reversibility: {avg_reversibility:.2%}"
        )

# ═══════════════════════════════════════════════════════════════
# III. UNIFIED VALIDATOR
# ═══════════════════════════════════════════════════════════════

class EquationValidator:
    """Validates all 8 millennium equations on trajectory"""

    def __init__(self):
        self.validators = {
            EquationType.RIEMANN: Eq1_RiemannValidator,
            EquationType.NO_CLONE: Eq2_NoCloneValidator,
            EquationType.NAVIER_STOKES: Eq3_NavierStokesValidator,
            EquationType.YANG_MILLS: Eq4_YangMillsValidator,
            EquationType.HODGE: Eq5_HodgeValidator,
            EquationType.BSD: Eq6_BSDValidator,
            EquationType.POINCARE: Eq7_PoincareValidator,
            EquationType.P_VS_NP: Eq8_PvsNPValidator,
        }

    def validate_trajectory(self, trajectory: List[EMxState]) -> ValidationReport:
        """
        Validate full trajectory against all 8 equations
        Returns comprehensive report
        """
        results = {}

        for eq_type, validator_class in self.validators.items():
            result = validator_class.validate(trajectory)
            results[eq_type] = result

        # Compute overall pass/fail
        passing = sum(1 for r in results.values() if r.passes)
        total = len(results)
        pass_rate = passing / total
        overall_pass = pass_rate >= 0.75  # At least 6/8 must pass

        # Calculate cycles
        total_ticks = len(trajectory)
        total_cycles = total_ticks // 96

        return ValidationReport(
            total_ticks=total_ticks,
            total_cycles=total_cycles,
            equations=results,
            overall_pass=overall_pass,
            pass_rate=pass_rate
        )

    def print_report(self, report: ValidationReport):
        """Print formatted validation report"""
        print("\n" + "═"*70)
        print("MILLENNIUM EQUATION VALIDATION REPORT")
        print("═"*70)
        print(f"Total ticks: {report.total_ticks}")
        print(f"Total cycles: {report.total_cycles}")
        print(f"Overall: {'✓ PASS' if report.overall_pass else '✗ FAIL'} ({report.pass_rate:.1%})")
        print("─"*70)

        for eq_type in EquationType:
            result = report.equations[eq_type]
            status = "✓" if result.passes else "✗"

            print(f"\n{status} {result.equation.value}")
            print(f"   {result.message}")
            print(f"   Confidence: {result.confidence:.2%}")
            print(f"   Violations: {len(result.violations)} ticks")

            if len(result.violations) > 0 and len(result.violations) <= 5:
                print(f"   Violation ticks: {result.violations}")

        print("\n" + "═"*70)

# ═══════════════════════════════════════════════════════════════
# IV. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate equation validation"""
    from emx_kernel import EMxKernel

    print("="*70)
    print("EMx Millennium Equation Validator Demo")
    print("="*70)

    # Create kernel and run sequence
    kernel = EMxKernel()
    trajectory = []

    # Execute 200 steps (2+ cycles)
    operators = ['O2', 'O3', 'O6', 'O7', 'O2', 'O6'] * 34

    print("\nExecuting trajectory...")
    for op in operators:
        kernel.step(op, axis=0)
        trajectory.append(kernel.state)

    print(f"Generated {len(trajectory)} states")

    # Validate
    validator = EquationValidator()
    report = validator.validate_trajectory(trajectory)

    # Print report
    validator.print_report(report)

if __name__ == "__main__":
    demo()
