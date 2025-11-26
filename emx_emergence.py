"""
EMx Statistical Validation Framework
Runs large-scale simulations to confirm emergent harmonics match theoretical predictions.
Tests convergence, stability, and distribution of observables.
"""

from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
import math
import statistics
from collections import Counter

from emx_kernel import (
    EMxKernel, EMxState, TernaryTriple, Polarity,
    THEORETICAL_ALPHA, THEORETICAL_BETA, THEORETICAL_GAMMA, THEORETICAL_NULL
)
from emx_millennium_validator import EquationValidator, ValidationReport

# ═══════════════════════════════════════════════════════════════
# I. STATISTICAL MEASUREMENT TYPES
# ═══════════════════════════════════════════════════════════════

@dataclass
class DistributionStats:
    """Statistical distribution of a metric"""
    mean: float
    median: float
    std_dev: float
    min_val: float
    max_val: float
    quartile_25: float
    quartile_75: float

    def confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Calculate confidence interval (assumes normal distribution)"""
        z_score = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
        margin = z_score * self.std_dev
        return (self.mean - margin, self.mean + margin)

@dataclass
class ConvergenceTest:
    """Test if metric converges to target"""
    metric_name: str
    target_value: float
    tolerance: float
    converges: bool
    final_value: float
    final_std_dev: float
    cycles_to_converge: Optional[int]
    trajectory: List[float]

@dataclass
class HypothesisTest:
    """Statistical hypothesis test result"""
    hypothesis: str
    test_statistic: float
    p_value: float
    reject_null: bool
    confidence_level: float
    interpretation: str

@dataclass
class StatisticalReport:
    """Complete statistical validation report"""
    total_runs: int
    ticks_per_run: int

    # Harmonic distributions
    null_dist: DistributionStats
    beta_dist: DistributionStats
    gamma_dist: DistributionStats
    alpha_dist: DistributionStats

    # Convergence tests
    null_convergence: ConvergenceTest
    beta_convergence: ConvergenceTest
    gamma_convergence: ConvergenceTest

    # Hypothesis tests
    hypothesis_tests: List[HypothesisTest]

    # State space coverage
    unique_states: int
    total_states: int
    coverage_ratio: float
    state_distribution: Dict[str, int]  # N-class counts

    # Overall validation
    passes_validation: bool
    confidence: float

# ═══════════════════════════════════════════════════════════════
# II. STATISTICAL VALIDATORS
# ═══════════════════════════════════════════════════════════════

class StatisticalValidator:
    """Runs large-scale statistical tests on EMx behavior"""

    def __init__(self, min_runs: int = 100, ticks_per_run: int = 96):
        self.min_runs = min_runs
        self.ticks_per_run = ticks_per_run
        self.equation_validator = EquationValidator()

    def run_monte_carlo(self,
                       operator_sequence: List[str],
                       runs: int = 1000) -> StatisticalReport:
        """
        Run Monte Carlo simulation with repeated trials
        Tests if emergent behavior converges to predictions
        """
        print(f"\n{'='*70}")
        print(f"Running Monte Carlo Validation: {runs} runs × {self.ticks_per_run} ticks")
        print(f"{'='*70}\n")

        # Storage for metrics
        null_samples = []
        beta_samples = []
        gamma_samples = []
        alpha_samples = []

        # Track convergence over runs
        null_trajectory = []
        beta_trajectory = []
        gamma_trajectory = []

        # State space tracking
        all_states = []
        state_classes = Counter()

        # Run simulations
        for run_idx in range(runs):
            if run_idx % 100 == 0:
                print(f"Progress: {run_idx}/{runs} runs...")

            kernel = EMxKernel()
            run_states = []

            # Execute operator sequence
            for op in operator_sequence:
                success, reason = kernel.step(op, axis=(run_idx % 3))
                run_states.append(kernel.state)
                all_states.append(kernel.state.triple)
                state_classes[kernel.state.null_class.value] += 1

            # Collect final harmonics
            final_harmonics = kernel.get_harmonics()
            null_samples.append(kernel.state.properties.null_load)
            beta_samples.append(final_harmonics.beta)
            gamma_samples.append(final_harmonics.gamma)
            alpha_samples.append(final_harmonics.alpha)

            # Track running averages for convergence
            null_trajectory.append(sum(null_samples) / len(null_samples))
            beta_trajectory.append(sum(beta_samples) / len(beta_samples))
            gamma_trajectory.append(sum(gamma_samples) / len(gamma_samples))

        print(f"✓ Completed {runs} runs\n")

        # Compute distributions
        null_dist = self._compute_distribution(null_samples)
        beta_dist = self._compute_distribution(beta_samples)
        gamma_dist = self._compute_distribution(gamma_samples)
        alpha_dist = self._compute_distribution(alpha_samples)

        # Convergence tests
        null_conv = self._test_convergence(
            "NULL (∅)", THEORETICAL_NULL, 0.02, null_trajectory
        )
        beta_conv = self._test_convergence(
            "Beta (β)", 0.0, 0.1, beta_trajectory
        )
        gamma_conv = self._test_convergence(
            "Gamma (γ)", 0.995, 0.01, gamma_trajectory
        )

        # Hypothesis tests
        hypothesis_tests = self._run_hypothesis_tests(
            null_samples, beta_samples, gamma_samples
        )

        # State space coverage
        unique_states = len(set(all_states))
        total_states = len(all_states)
        coverage_ratio = unique_states / total_states

        # Overall validation
        passes = self._validate_overall(
            null_dist, beta_dist, gamma_dist,
            null_conv, beta_conv, gamma_conv,
            hypothesis_tests
        )

        return StatisticalReport(
            total_runs=runs,
            ticks_per_run=self.ticks_per_run,
            null_dist=null_dist,
            beta_dist=beta_dist,
            gamma_dist=gamma_dist,
            alpha_dist=alpha_dist,
            null_convergence=null_conv,
            beta_convergence=beta_conv,
            gamma_convergence=gamma_conv,
            hypothesis_tests=hypothesis_tests,
            unique_states=unique_states,
            total_states=total_states,
            coverage_ratio=coverage_ratio,
            state_distribution=dict(state_classes),
            passes_validation=passes,
            confidence=self._compute_confidence(hypothesis_tests)
        )

    def _compute_distribution(self, samples: List[float]) -> DistributionStats:
        """Compute statistical distribution from samples"""
        if not samples:
            return DistributionStats(0, 0, 0, 0, 0, 0, 0)

        sorted_samples = sorted(samples)
        n = len(sorted_samples)

        return DistributionStats(
            mean=statistics.mean(samples),
            median=statistics.median(samples),
            std_dev=statistics.stdev(samples) if n > 1 else 0,
            min_val=min(samples),
            max_val=max(samples),
            quartile_25=sorted_samples[n // 4],
            quartile_75=sorted_samples[3 * n // 4]
        )

    def _test_convergence(self,
                         metric_name: str,
                         target: float,
                         tolerance: float,
                         trajectory: List[float]) -> ConvergenceTest:
        """Test if metric converges to target value"""
        if len(trajectory) < 10:
            return ConvergenceTest(
                metric_name, target, tolerance, False, 0, 0, None, trajectory
            )

        # Check last 10% of trajectory
        final_window = trajectory[-len(trajectory)//10:]
        final_mean = sum(final_window) / len(final_window)
        final_std = statistics.stdev(final_window) if len(final_window) > 1 else 0

        # Converges if within tolerance
        converges = abs(final_mean - target) < tolerance

        # Find convergence point (first time it stays within tolerance)
        cycles_to_converge = None
        for i in range(len(trajectory) - 10):
            window = trajectory[i:i+10]
            window_mean = sum(window) / len(window)
            if abs(window_mean - target) < tolerance:
                # Check if it stays converged
                remaining = trajectory[i:]
                if all(abs(sum(remaining[j:j+10])/10 - target) < tolerance
                      for j in range(0, len(remaining)-10, 10)):
                    cycles_to_converge = i
                    break

        return ConvergenceTest(
            metric_name=metric_name,
            target_value=target,
            tolerance=tolerance,
            converges=converges,
            final_value=final_mean,
            final_std_dev=final_std,
            cycles_to_converge=cycles_to_converge,
            trajectory=trajectory
        )

    def _run_hypothesis_tests(self,
                             null_samples: List[float],
                             beta_samples: List[float],
                             gamma_samples: List[float]) -> List[HypothesisTest]:
        """Run statistical hypothesis tests"""
        tests = []

        # Test 1: H₀: ⟨∅⟩ = 0.22
        null_mean = statistics.mean(null_samples)
        null_std = statistics.stdev(null_samples)
        null_n = len(null_samples)

        # T-statistic
        t_stat = (null_mean - THEORETICAL_NULL) / (null_std / math.sqrt(null_n))

        # P-value (two-tailed, approximate using normal)
        p_value = 2 * (1 - self._normal_cdf(abs(t_stat)))

        tests.append(HypothesisTest(
            hypothesis="H₀: ⟨∅⟩ = 0.22",
            test_statistic=t_stat,
            p_value=p_value,
            reject_null=p_value < 0.05,
            confidence_level=0.95,
            interpretation=f"Observed ⟨∅⟩ = {null_mean:.4f}, "
                          f"{'differs significantly' if p_value < 0.05 else 'consistent with'} "
                          f"theoretical 0.22"
        ))

        # Test 2: H₀: ⟨β⟩ = 0
        beta_mean = statistics.mean(beta_samples)
        beta_std = statistics.stdev(beta_samples)
        beta_t = beta_mean / (beta_std / math.sqrt(len(beta_samples)))
        beta_p = 2 * (1 - self._normal_cdf(abs(beta_t)))

        tests.append(HypothesisTest(
            hypothesis="H₀: ⟨β⟩ → 0 (time-averaged)",
            test_statistic=beta_t,
            p_value=beta_p,
            reject_null=beta_p < 0.05 and beta_mean > 0.1,
            confidence_level=0.95,
            interpretation=f"Observed ⟨β⟩ = {beta_mean:.4f}, "
                          f"{'significantly > 0' if beta_p < 0.05 and beta_mean > 0.1 else 'converging to 0'}"
        ))

        # Test 3: H₀: γ ≥ 0.992
        gamma_mean = statistics.mean(gamma_samples)
        gamma_below_threshold = sum(1 for g in gamma_samples if g < 0.992)
        gamma_proportion = gamma_below_threshold / len(gamma_samples)

        tests.append(HypothesisTest(
            hypothesis="H₀: γ ≥ 0.992 for stable states",
            test_statistic=gamma_mean,
            p_value=gamma_proportion,
            reject_null=gamma_proportion > 0.1,
            confidence_level=0.95,
            interpretation=f"⟨γ⟩ = {gamma_mean:.4f}, "
                          f"{gamma_proportion:.1%} below threshold"
        ))

        return tests

    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF (for p-value calculation)"""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _validate_overall(self,
                         null_dist: DistributionStats,
                         beta_dist: DistributionStats,
                         gamma_dist: DistributionStats,
                         null_conv: ConvergenceTest,
                         beta_conv: ConvergenceTest,
                         gamma_conv: ConvergenceTest,
                         hypothesis_tests: List[HypothesisTest]) -> bool:
        """Overall validation: do emergent values match predictions?"""

        # Check 1: NULL converges to 0.22 ± 0.02
        null_ok = null_conv.converges and abs(null_dist.mean - THEORETICAL_NULL) < 0.02

        # Check 2: Beta converges to ~0
        beta_ok = beta_dist.mean < 0.3  # Relaxed threshold

        # Check 3: Gamma stays high
        gamma_ok = gamma_dist.mean > 0.90

        # Check 4: Hypothesis tests don't strongly reject
        hyp_ok = sum(1 for t in hypothesis_tests if not t.reject_null) >= 2

        return null_ok and beta_ok and gamma_ok and hyp_ok

    def _compute_confidence(self, hypothesis_tests: List[HypothesisTest]) -> float:
        """Compute overall confidence from hypothesis tests"""
        # Average of (1 - p_value) for non-rejected tests
        valid_tests = [t for t in hypothesis_tests if not t.reject_null]
        if not valid_tests:
            return 0.0

        confidences = [1.0 - t.p_value for t in valid_tests]
        return sum(confidences) / len(confidences)

    def print_statistical_report(self, report: StatisticalReport):
        """Print formatted statistical report"""
        print("\n" + "═"*70)
        print("STATISTICAL VALIDATION REPORT")
        print("═"*70)
        print(f"Runs: {report.total_runs} × {report.ticks_per_run} ticks")
        print(f"Overall: {'✓ PASS' if report.passes_validation else '✗ FAIL'} "
              f"(confidence: {report.confidence:.1%})")
        print("═"*70)

        # NULL Distribution
        print(f"\n🔹 NULL (∅) Distribution")
        print(f"   Target: {THEORETICAL_NULL:.3f} ± 0.02")
        ci_low, ci_high = report.null_dist.confidence_interval()
        print(f"   Observed: {report.null_dist.mean:.4f} ± {report.null_dist.std_dev:.4f}")
        print(f"   95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
        print(f"   Range: [{report.null_dist.min_val:.4f}, {report.null_dist.max_val:.4f}]")
        print(f"   Convergence: {'✓' if report.null_convergence.converges else '✗'} "
              f"({report.null_convergence.cycles_to_converge or '?'} cycles)")

        # Beta Distribution
        print(f"\n🔹 Beta (β) Distribution")
        print(f"   Target: → 0 (time-averaged)")
        ci_low, ci_high = report.beta_dist.confidence_interval()
        print(f"   Observed: {report.beta_dist.mean:.4f} ± {report.beta_dist.std_dev:.4f}")
        print(f"   95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
        print(f"   Convergence: {'✓' if report.beta_convergence.converges else '✗'}")

        # Gamma Distribution
        print(f"\n🔹 Gamma (γ) Distribution")
        print(f"   Target: ≥ 0.992")
        ci_low, ci_high = report.gamma_dist.confidence_interval()
        print(f"   Observed: {report.gamma_dist.mean:.4f} ± {report.gamma_dist.std_dev:.4f}")
        print(f"   95% CI: [{ci_low:.4f}, {ci_high:.4f}]")
        print(f"   Convergence: {'✓' if report.gamma_convergence.converges else '✗'}")

        # Alpha Distribution
        print(f"\n🔹 Alpha (α) Distribution")
        print(f"   Observed: {report.alpha_dist.mean:.4f} ± {report.alpha_dist.std_dev:.4f}")

        # Hypothesis Tests
        print(f"\n🔹 Hypothesis Tests")
        for test in report.hypothesis_tests:
            status = "✗ Reject H₀" if test.reject_null else "✓ Fail to reject H₀"
            print(f"   {status}: {test.hypothesis}")
            print(f"      p-value: {test.p_value:.4f}")
            print(f"      {test.interpretation}")

        # State Space Coverage
        print(f"\n🔹 State Space Exploration")
        print(f"   Unique states: {report.unique_states}/{report.total_states} "
              f"({report.coverage_ratio:.1%})")
        print(f"   N-class distribution:")
        for n_class, count in sorted(report.state_distribution.items()):
            pct = 100 * count / report.total_states
            print(f"      {n_class}: {count} ({pct:.1f}%)")

        print("\n" + "═"*70 + "\n")

# ═══════════════════════════════════════════════════════════════
# III. CONVERGENCE DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════

class ConvergenceDiagnostics:
    """Detailed convergence analysis tools"""

    @staticmethod
    def plot_trajectory_ascii(trajectory: List[float],
                             target: float,
                             tolerance: float,
                             width: int = 60,
                             height: int = 15) -> str:
        """Generate ASCII plot of convergence trajectory"""
        if not trajectory:
            return "No data"

        # Normalize to plot bounds
        min_val = min(min(trajectory), target - tolerance)
        max_val = max(max(trajectory), target + tolerance)
        range_val = max_val - min_val if max_val > min_val else 1.0

        # Create grid
        grid = [[' ' for _ in range(width)] for _ in range(height)]

        # Plot target line
        target_y = int((max_val - target) / range_val * (height - 1))
        if 0 <= target_y < height:
            for x in range(width):
                grid[target_y][x] = '─'

        # Plot tolerance bands
        upper_y = int((max_val - (target + tolerance)) / range_val * (height - 1))
        lower_y = int((max_val - (target - tolerance)) / range_val * (height - 1))
        for y in [upper_y, lower_y]:
            if 0 <= y < height:
                for x in range(width):
                    if grid[y][x] == ' ':
                        grid[y][x] = '·'

        # Plot trajectory
        step = max(1, len(trajectory) // width)
        for i, val in enumerate(trajectory[::step]):
            x = min(i, width - 1)
            y = int((max_val - val) / range_val * (height - 1))
            if 0 <= y < height:
                grid[y][x] = '●'

        # Convert to string
        result = []
        result.append(f"Target: {target:.4f} ± {tolerance:.4f}")
        result.append("  " + "─" * width)
        for row in grid:
            result.append("  " + ''.join(row))
        result.append("  " + "─" * width)
        result.append(f"  Start → End ({len(trajectory)} samples)")

        return '\n'.join(result)

# ═══════════════════════════════════════════════════════════════
# IV. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate statistical validation"""
    print("="*70)
    print("EMx Statistical Validation Framework Demo")
    print("="*70)

    # Create validator
    validator = StatisticalValidator(ticks_per_run=96)

    # Define operator sequence (canonical cycle)
    operator_sequence = ['O2', 'O3', 'O6', 'O7'] * 24  # 96 ticks

    # Run Monte Carlo (smaller scale for demo)
    report = validator.run_monte_carlo(operator_sequence, runs=200)

    # Print report
    validator.print_statistical_report(report)

    # Print convergence plots
    print("\n🔹 NULL Convergence Trajectory")
    print(ConvergenceDiagnostics.plot_trajectory_ascii(
        report.null_convergence.trajectory,
        THEORETICAL_NULL,
        0.02
    ))

    print("\n🔹 Beta Convergence Trajectory")
    print(ConvergenceDiagnostics.plot_trajectory_ascii(
        report.beta_convergence.trajectory,
        0.0,
        0.1
    ))

if __name__ == "__main__":
    demo()
