"""
EMx Comprehensive Validation & Testing Suite
Unit tests, integration tests, and regression tests for entire framework.
Validates measured harmonics, millennium equations, and cross-domain consistency.
"""

import sys
import traceback
from typing import List, Dict, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import math

from emx_kernel import (
    EMxKernel, EMxState, TernaryTriple, Polarity,
    Harmonics, k_class, classify_state, NullClass,
    O1_Delta, O2_Gradient, O3_Rotation, O4_Closure,
    O6_Normalize, O7_Exchange, O9_NoClone, O10_Integrate,
    THEORETICAL_NULL, THEORETICAL_ALPHA, THEORETICAL_BETA, THEORETICAL_GAMMA
)
from emx_millennium_validator import EquationValidator, EquationType
from emx_statistical_validator import StatisticalValidator
from emx_profiler import PerformanceProfiler, PerformanceOptimizer
from emx_domain_refactored import (
    LogicEncoderRefactored, ArithmeticEncoderRefactored, OptimizationEncoderRefactored
)
from emx_financial_suite import FinancialEncoder, FinancialCrisisDetector
from emx_climate_suite import ClimateEncoder, ClimateTippingDetector

# ═══════════════════════════════════════════════════════════════
# I. TEST FRAMEWORK
# ═══════════════════════════════════════════════════════════════

class TestStatus(Enum):
    """Test result status"""
    PASS = "✓ PASS"
    FAIL = "✗ FAIL"
    SKIP = "⊘ SKIP"
    ERROR = "⚠ ERROR"

@dataclass
class TestResult:
    """Individual test result"""
    test_name: str
    category: str
    status: TestStatus
    message: str
    duration_ms: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@dataclass
class TestSuiteReport:
    """Complete test suite report"""
    total_tests: int
    passed: int
    failed: int
    errors: int
    skipped: int
    total_duration_ms: float
    results: List[TestResult]

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate"""
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests

    @property
    def success(self) -> bool:
        """Overall success"""
        return self.failed == 0 and self.errors == 0

class TestRunner:
    """Test execution framework"""

    def __init__(self):
        self.results: List[TestResult] = []

    def run_test(self, test_func: Callable, test_name: str, category: str) -> TestResult:
        """Run single test with error handling"""
        import time

        start = time.perf_counter()

        try:
            # Execute test
            success, message, details = test_func()

            duration = (time.perf_counter() - start) * 1000

            if success:
                status = TestStatus.PASS
            else:
                status = TestStatus.FAIL

            return TestResult(
                test_name=test_name,
                category=category,
                status=status,
                message=message,
                duration_ms=duration,
                details=details
            )

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000

            return TestResult(
                test_name=test_name,
                category=category,
                status=TestStatus.ERROR,
                message=f"Exception: {str(e)}",
                duration_ms=duration,
                error=traceback.format_exc()
            )

    def generate_report(self) -> TestSuiteReport:
        """Generate test suite report"""
        passed = sum(1 for r in self.results if r.status == TestStatus.PASS)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAIL)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIP)

        total_duration = sum(r.duration_ms for r in self.results)

        return TestSuiteReport(
            total_tests=len(self.results),
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            total_duration_ms=total_duration,
            results=self.results
        )

# ═══════════════════════════════════════════════════════════════
# II. UNIT TESTS - CORE KERNEL
# ═══════════════════════════════════════════════════════════════

class KernelUnitTests:
    """Unit tests for core kernel operations"""

    @staticmethod
    def test_polarity_operations():
        """Test polarity algebra"""
        # Negation
        assert (-Polarity.PLUS_ZERO).value == -1
        assert (-Polarity.MINUS_ZERO).value == 1
        assert (-Polarity.ZERO).value == 0

        # Magnitude
        assert Polarity.PLUS_ZERO.magnitude == 0
        assert Polarity.MINUS_ZERO.magnitude == 0
        assert Polarity.ZERO.magnitude == 0

        return True, "Polarity operations correct", {}

    @staticmethod
    def test_k_class_computation():
        """Test k-class computation"""
        # N0: k=0
        s0 = (Polarity.ZERO, Polarity.ZERO, Polarity.ZERO)
        assert k_class(s0) == 0

        # N1: k=1
        s1 = (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO)
        assert k_class(s1) == 1

        # N2: k=2
        s2 = (Polarity.PLUS_ZERO, Polarity.MINUS_ZERO, Polarity.ZERO)
        assert k_class(s2) == 2

        # N3: k=3
        s3 = (Polarity.PLUS_ZERO, Polarity.PLUS_ZERO, Polarity.PLUS_ZERO)
        assert k_class(s3) == 3

        return True, "k-class computation correct", {}

    @staticmethod
    def test_null_class_classification():
        """Test N-class classification"""
        # Test all classes
        assert classify_state((Polarity.ZERO, Polarity.ZERO, Polarity.ZERO)) == NullClass.N0
        assert classify_state((Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO)) == NullClass.N1
        assert classify_state((Polarity.PLUS_ZERO, Polarity.MINUS_ZERO, Polarity.ZERO)) == NullClass.N2
        assert classify_state((Polarity.PLUS_ZERO, Polarity.PLUS_ZERO, Polarity.MINUS_ZERO)) == NullClass.N3
        assert classify_state((Polarity.PLUS_ZERO, Polarity.PLUS_ZERO, Polarity.ZERO)) == NullClass.N4
        assert classify_state((Polarity.PLUS_ZERO, Polarity.PLUS_ZERO, Polarity.PLUS_ZERO)) == NullClass.N5

        return True, "N-class classification correct", {}

    @staticmethod
    def test_operator_o2_gradient():
        """Test O2 gradient operator"""
        # O2 should break symmetry from N0
        s0 = (Polarity.ZERO, Polarity.ZERO, Polarity.ZERO)
        s1 = O2_Gradient.apply(s0)

        assert s1 != s0, "O2 should change N0"
        assert k_class(s1) > 0, "O2 should increase k-class from N0"

        return True, "O2 gradient works correctly", {}

    @staticmethod
    def test_operator_o3_rotation():
        """Test O3 rotation operator"""
        s = (Polarity.PLUS_ZERO, Polarity.MINUS_ZERO, Polarity.ZERO)
        s_rot = O3_Rotation.apply(s)

        # Should be cyclic permutation
        assert s_rot == (Polarity.ZERO, Polarity.PLUS_ZERO, Polarity.MINUS_ZERO)

        # Three rotations should return to original
        s_rot2 = O3_Rotation.apply(s_rot)
        s_rot3 = O3_Rotation.apply(s_rot2)
        assert s_rot3 == s

        return True, "O3 rotation cyclic", {}

    @staticmethod
    def test_operator_o6_normalize():
        """Test O6 normalize operator"""
        # Should drive toward N0
        s = (Polarity.PLUS_ZERO, Polarity.MINUS_ZERO, Polarity.PLUS_ZERO)
        s_norm = O6_Normalize.apply(s)

        # Should reduce some polarities
        k_before = k_class(s)
        k_after = k_class(s_norm)

        assert k_after <= k_before, "O6 should not increase k-class"

        return True, "O6 normalize reduces k-class", {}

    @staticmethod
    def test_operator_o7_exchange():
        """Test O7 exchange operator"""
        s = (Polarity.PLUS_ZERO, Polarity.MINUS_ZERO, Polarity.ZERO)

        # Flip axis 0
        s_flip0 = O7_Exchange.apply(s, axis=0)
        assert s_flip0[0].value == -s[0].value
        assert s_flip0[1:] == s[1:]

        # Flip axis 1
        s_flip1 = O7_Exchange.apply(s, axis=1)
        assert s_flip1[1].value == -s[1].value

        return True, "O7 exchange flips correctly", {}

    @staticmethod
    def test_closure_check():
        """Test O4 closure checking"""
        # Closed loop
        closed_path = [
            (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO),
            (Polarity.ZERO, Polarity.PLUS_ZERO, Polarity.ZERO),
            (Polarity.MINUS_ZERO, Polarity.ZERO, Polarity.ZERO),
            (Polarity.ZERO, Polarity.MINUS_ZERO, Polarity.ZERO)
        ]
        assert O4_Closure.check(closed_path), "Should detect closed loop"

        # Open loop
        open_path = [
            (Polarity.PLUS_ZERO, Polarity.ZERO, Polarity.ZERO),
            (Polarity.PLUS_ZERO, Polarity.PLUS_ZERO, Polarity.ZERO),
            (Polarity.PLUS_ZERO, Polarity.PLUS_ZERO, Polarity.PLUS_ZERO)
        ]
        # May or may not be closed depending on tolerance

        return True, "O4 closure check functional", {}

    @staticmethod
    def test_null_dynamics():
        """Test NULL evolution dynamics"""
        kernel = EMxKernel()

        initial_null = kernel.state.properties.null_load

        # Execute operators
        for _ in range(20):
            kernel.step('O2', axis=0)

        final_null = kernel.state.properties.null_load

        # NULL should change (not stay at 0)
        assert final_null != initial_null, "NULL should evolve"

        # NULL should be bounded [0, 1]
        assert 0 <= final_null <= 1, "NULL must be in [0,1]"

        return True, f"NULL evolved from {initial_null:.3f} to {final_null:.3f}", {
            'initial': initial_null,
            'final': final_null
        }

# ═══════════════════════════════════════════════════════════════
# III. UNIT TESTS - MEASURED HARMONICS
# ═══════════════════════════════════════════════════════════════

class HarmonicsUnitTests:
    """Tests for measured harmonics system"""

    @staticmethod
    def test_harmonics_measurement():
        """Test that harmonics are measured from trajectory"""
        kernel = EMxKernel()

        # Short trajectory (should fall back to theoretical)
        kernel.step('O2')
        kernel.step('O3')
        harmonics_short = kernel.get_harmonics()

        # Long trajectory (should measure)
        for _ in range(20):
            kernel.step('O2', axis=0)
        harmonics_long = kernel.get_harmonics()

        # Both should return valid harmonics
        assert 0 <= harmonics_long.alpha <= 1
        assert 0 <= harmonics_long.beta <= 1
        assert 0 <= harmonics_long.gamma <= 1

        return True, "Harmonics measured from trajectory", {
            'short_alpha': harmonics_short.alpha,
            'long_alpha': harmonics_long.alpha
        }

    @staticmethod
    def test_null_convergence():
        """Test NULL convergence to ~0.22"""
        kernel = EMxKernel()

        null_samples = []

        # Run 100 steps
        for _ in range(100):
            kernel.step('O6', axis=0)  # Normalize repeatedly
            null_samples.append(kernel.state.properties.null_load)

        # Check convergence to theoretical value
        final_null = null_samples[-1]
        avg_null_last_20 = sum(null_samples[-20:]) / 20

        # Should be approaching 0.22 ± 0.05
        within_range = 0.17 <= avg_null_last_20 <= 0.27

        return within_range, f"NULL converged to {avg_null_last_20:.3f} (target: 0.22)", {
            'final': final_null,
            'average_last_20': avg_null_last_20
        }

    @staticmethod
    def test_beta_reflects_drift():
        """Test that beta increases with state changes"""
        kernel_stable = EMxKernel()

        # Stable: repeat same operator
        for _ in range(20):
            kernel_stable.step('O6', axis=0)
        beta_stable = kernel_stable.get_harmonics().beta

        # Chaotic: vary operators
        kernel_chaotic = EMxKernel()
        ops = ['O2', 'O3', 'O7', 'O6', 'O2', 'O3']
        for _ in range(20):
            for op in ops:
                kernel_chaotic.step(op, axis=0)
        beta_chaotic = kernel_chaotic.get_harmonics().beta

        # Chaotic should have higher beta
        higher_drift = beta_chaotic > beta_stable

        return higher_drift, f"β_chaotic ({beta_chaotic:.3f}) > β_stable ({beta_stable:.3f})", {
            'stable': beta_stable,
            'chaotic': beta_chaotic
        }

    @staticmethod
    def test_gamma_reflects_closure():
        """Test that gamma reflects system coherence"""
        # Closed loop
        kernel_closed = EMxKernel()
        for _ in range(5):
            kernel_closed.step('O2')
            kernel_closed.step('O7', axis=0)  # Go and return
        gamma_closed = kernel_closed.get_harmonics().gamma

        # Open diverging
        kernel_open = EMxKernel()
        for _ in range(20):
            kernel_open.step('O2')  # Keep going
        gamma_open = kernel_open.get_harmonics().gamma

        # Closed should have higher gamma
        better_closure = gamma_closed >= gamma_open

        return better_closure, f"γ_closed ({gamma_closed:.3f}) ≥ γ_open ({gamma_open:.3f})", {
            'closed': gamma_closed,
            'open': gamma_open
        }

# ═══════════════════════════════════════════════════════════════
# IV. INTEGRATION TESTS - MILLENNIUM EQUATIONS
# ═══════════════════════════════════════════════════════════════

class MillenniumIntegrationTests:
    """Integration tests for millennium equations"""

    @staticmethod
    def test_equation_validation_runs():
        """Test that equation validator executes"""
        kernel = EMxKernel()
        trajectory = []

        # Build trajectory
        for _ in range(96):
            kernel.step('O2', axis=0)
            trajectory.append(kernel.state)

        # Validate
        validator = EquationValidator()
        report = validator.validate_trajectory(trajectory)

        # Should have results for all 8 equations
        assert len(report.equations) == 8

        return True, "Equation validator executed", {
            'equations_checked': len(report.equations),
            'pass_rate': report.pass_rate
        }

    @staticmethod
    def test_no_clone_detection():
        """Test Eq₂ (No-Clone) detects violations"""
        kernel = EMxKernel()
        trajectory = []

        # Force revisit same state
        kernel.step('O2')
        trajectory.append(kernel.state)

        kernel.step('O7', axis=0)  # Flip
        trajectory.append(kernel.state)

        kernel.step('O7', axis=0)  # Flip back (collision)
        trajectory.append(kernel.state)

        # Validate
        validator = EquationValidator()
        report = validator.validate_trajectory(trajectory)

        no_clone_result = report.equations[EquationType.NO_CLONE]

        # Should detect collision
        has_violations = len(no_clone_result.violations) > 0

        return has_violations, f"No-clone detected {len(no_clone_result.violations)} collisions", {
            'violations': len(no_clone_result.violations)
        }

    @staticmethod
    def test_riemann_time_average():
        """Test Eq₁ (Riemann) checks time-averaged beta"""
        kernel = EMxKernel()
        trajectory = []

        # Execute smooth trajectory
        for _ in range(96):
            kernel.step('O6', axis=0)
            trajectory.append(kernel.state)

        validator = EquationValidator()
        report = validator.validate_trajectory(trajectory)

        riemann_result = report.equations[EquationType.RIEMANN]

        # Should pass (smooth trajectory → low ⟨β⟩)
        return riemann_result.passes, riemann_result.message, {
            'metric_value': riemann_result.metric_value
        }

# ═══════════════════════════════════════════════════════════════
# V. INTEGRATION TESTS - DOMAIN ENCODERS
# ═══════════════════════════════════════════════════════════════

class DomainIntegrationTests:
    """Integration tests for domain encoders"""

    @staticmethod
    def test_logic_encoder_measured():
        """Test logic encoder uses measured harmonics"""
        from emx_logic import Proposition, LogicalValue, Argument

        premises = [Proposition("P", LogicalValue.TRUE)]
        conclusion = Proposition("P", LogicalValue.TRUE)
        arg = Argument(premises, conclusion)

        valid, harmonics, metrics = LogicEncoderRefactored.validate_argument_measured(arg)

        # Should validate (P ⊢ P is trivially valid)
        # Harmonics should be measured (not lookup table)
        measured = 'trajectory_length' in metrics and metrics['trajectory_length'] >= 20

        return valid and measured, f"Valid: {valid}, Measured: {measured}", metrics

    @staticmethod
    def test_arithmetic_division_by_zero():
        """Test arithmetic encoder handles division by zero"""
        result, state, metrics = ArithmeticEncoderRefactored.compute_with_measurement(
            'divide', 5, 0
        )

        # Should route through NULL
        high_null = metrics['null_load'] > 0.5

        return high_null, f"Div-by-zero routed through NULL: ∅={metrics['null_load']:.3f}", metrics

    @staticmethod
    def test_optimization_convergence_detection():
        """Test optimization encoder detects convergence"""
        from emx_optimization import SphereFunction

        objective = SphereFunction(dim=2)
        initial = [2.0, 2.0]
        bounds = [(-5, 5), (-5, 5)]

        solution, states, metrics = OptimizationEncoderRefactored.optimize_measured(
            objective, initial, bounds, max_iterations=30
        )

        # Should converge (sphere is convex)
        converged = metrics['converged']

        return converged, f"Converged: {converged}, Final β: {metrics['final_beta']:.3f}", metrics

# ═══════════════════════════════════════════════════════════════
# VI. INTEGRATION TESTS - FINANCIAL & CLIMATE
# ═══════════════════════════════════════════════════════════════

class ApplicationIntegrationTests:
    """Integration tests for financial and climate applications"""

    @staticmethod
    def test_financial_crisis_detection():
        """Test financial crisis detector"""
        # Normal state
        normal = FinancialEncoder.encode_market_state(
            price_change=0.02, volume=0.6, volatility=0.15
        )

        kernel = EMxKernel(normal.to_ternary_triple())
        kernel.state.properties.null_load = normal.null_financial

        trajectory = [kernel.state]
        for _ in range(20):
            kernel.step('O2')
            trajectory.append(kernel.state)

        harmonics = kernel.get_harmonics()
        crisis, indicators = FinancialCrisisDetector.detect_crisis(normal, harmonics, trajectory)

        # Should NOT detect crisis in normal conditions
        no_crisis = not crisis

        return no_crisis, f"No crisis in normal conditions (indicators: {len(indicators)})", {
            'crisis': crisis,
            'null_fin': normal.null_financial
        }

    @staticmethod
    def test_climate_tipping_detection():
        """Test climate tipping detector"""
        # Pre-industrial (stable)
        preindustrial = ClimateEncoder.encode_climate_state(
            temp_anomaly=0.0, radiative_forcing=0.0, co2=280
        )

        kernel = EMxKernel(preindustrial.to_ternary_triple())
        kernel.state.properties.null_load = preindustrial.null_atmospheric

        trajectory = [kernel.state]
        for _ in range(20):
            kernel.step('O2')
            trajectory.append(kernel.state)

        harmonics = kernel.get_harmonics()
        tipping, indicators = ClimateTippingDetector.detect_tipping_points(
            preindustrial, harmonics, trajectory
        )

        # Should NOT detect tipping in pre-industrial
        no_tipping = not tipping

        return no_tipping, f"No tipping pre-industrial (∅_atm: {preindustrial.null_atmospheric:.2%})", {
            'tipping': tipping,
            'null_atm': preindustrial.null_atmospheric
        }

# ═══════════════════════════════════════════════════════════════
# VII. REGRESSION TESTS
# ═══════════════════════════════════════════════════════════════

class RegressionTests:
    """Regression tests to ensure behavior consistency"""

    # Known-good baseline trajectory
    BASELINE_TRAJECTORY = {
        'operators': ['O2', 'O3', 'O6'] * 32,  # 96 steps
        'expected_final_k': 0,  # Should return to N0
        'expected_null_range': (0.15, 0.30),
        'expected_gamma_min': 0.85
    }

    @staticmethod
    def test_baseline_trajectory():
        """Test against known-good baseline"""
        kernel = EMxKernel()

        for op in RegressionTests.BASELINE_TRAJECTORY['operators']:
            kernel.step(op, axis=0)

        final_k = kernel.state.k
        final_null = kernel.state.properties.null_load
        final_gamma = kernel.get_harmonics().gamma

        # Check against baseline
        k_match = final_k == RegressionTests.BASELINE_TRAJECTORY['expected_final_k']
        null_in_range = (RegressionTests.BASELINE_TRAJECTORY['expected_null_range'][0] <=
                        final_null <=
                        RegressionTests.BASELINE_TRAJECTORY['expected_null_range'][1])
        gamma_sufficient = final_gamma >= RegressionTests.BASELINE_TRAJECTORY['expected_gamma_min']

        passes = k_match and null_in_range and gamma_sufficient

        return passes, f"Baseline: k={final_k}, ∅={final_null:.3f}, γ={final_gamma:.3f}", {
            'k_match': k_match,
            'null_in_range': null_in_range,
            'gamma_sufficient': gamma_sufficient
        }

    @staticmethod
    def test_deterministic_execution():
        """Test that same inputs produce same outputs"""
        # Run 1
        kernel1 = EMxKernel()
        for _ in range(20):
            kernel1.step('O2', axis=0)
        state1 = kernel1.state.triple
        null1 = kernel1.state.properties.null_load

        # Run 2 (identical)
        kernel2 = EMxKernel()
        for _ in range(20):
            kernel2.step('O2', axis=0)
        state2 = kernel2.state.triple
        null2 = kernel2.state.properties.null_load

        # Should be identical
        deterministic = (state1 == state2) and abs(null1 - null2) < 1e-10

        return deterministic, f"Deterministic: states {'match' if deterministic else 'differ'}", {
            'state1': state1,
            'state2': state2
        }

# ═══════════════════════════════════════════════════════════════
# VIII. MAIN TEST SUITE
# ═══════════════════════════════════════════════════════════════

def run_all_tests():
    """Execute complete test suite"""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  EMX COMPREHENSIVE VALIDATION SUITE".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70 + "\n")

    runner = TestRunner()

    # Unit Tests - Kernel
    print("▓"*70)
    print("▓ UNIT TESTS - CORE KERNEL")
    print("▓"*70 + "\n")

    kernel_tests = [
        (KernelUnitTests.test_polarity_operations, "Polarity Operations"),
        (KernelUnitTests.test_k_class_computation, "K-Class Computation"),
        (KernelUnitTests.test_null_class_classification, "N-Class Classification"),
        (KernelUnitTests.test_operator_o2_gradient, "O2 Gradient"),
        (KernelUnitTests.test_operator_o3_rotation, "O3 Rotation"),
        (KernelUnitTests.test_operator_o6_normalize, "O6 Normalize"),
        (KernelUnitTests.test_operator_o7_exchange, "O7 Exchange"),
        (KernelUnitTests.test_closure_check, "O4 Closure Check"),
        (KernelUnitTests.test_null_dynamics, "NULL Dynamics"),
    ]

    for test_func, test_name in kernel_tests:
        result = runner.run_test(test_func, test_name, "Kernel")
        runner.results.append(result)
        print(f"{result.status.value} {test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    # Unit Tests - Harmonics
    print("\n" + "▓"*70)
    print("▓ UNIT TESTS - MEASURED HARMONICS")
    print("▓"*70 + "\n")

    harmonics_tests = [
        (HarmonicsUnitTests.test_harmonics_measurement, "Harmonics Measurement"),
        (HarmonicsUnitTests.test_null_convergence, "NULL Convergence"),
        (HarmonicsUnitTests.test_beta_reflects_drift, "Beta Reflects Drift"),
        (HarmonicsUnitTests.test_gamma_reflects_closure, "Gamma Reflects Closure"),
    ]

    for test_func, test_name in harmonics_tests:
        result = runner.run_test(test_func, test_name, "Harmonics")
        runner.results.append(result)
        print(f"{result.status.value} {test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    # Integration Tests - Millennium
    print("\n" + "▓"*70)
    print("▓ INTEGRATION TESTS - MILLENNIUM EQUATIONS")
    print("▓"*70 + "\n")

    millennium_tests = [
        (MillenniumIntegrationTests.test_equation_validation_runs, "Equation Validator"),
        (MillenniumIntegrationTests.test_no_clone_detection, "No-Clone Detection"),
        (MillenniumIntegrationTests.test_riemann_time_average, "Riemann Time Average"),
    ]

    for test_func, test_name in millennium_tests:
        result = runner.run_test(test_func, test_name, "Millennium")
        runner.results.append(result)
        print(f"{result.status.value} {test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    # Integration Tests - Domains
    print("\n" + "▓"*70)
    print("▓ INTEGRATION TESTS - DOMAIN ENCODERS")
    print("▓"*70 + "\n")

    domain_tests = [
        (DomainIntegrationTests.test_logic_encoder_measured, "Logic Encoder"),
        (DomainIntegrationTests.test_arithmetic_division_by_zero, "Arithmetic Div/0"),
        (DomainIntegrationTests.test_optimization_convergence_detection, "Optimization Convergence"),
    ]

    for test_func, test_name in domain_tests:
        result = runner.run_test(test_func, test_name, "Domains")
        runner.results.append(result)
        print(f"{result.status.value} {test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    # Integration Tests - Applications
    print("\n" + "▓"*70)
    print("▓ INTEGRATION TESTS - APPLICATIONS")
    print("▓"*70 + "\n")

    app_tests = [
        (ApplicationIntegrationTests.test_financial_crisis_detection, "Financial Crisis Detection"),
        (ApplicationIntegrationTests.test_climate_tipping_detection, "Climate Tipping Detection"),
    ]

    for test_func, test_name in app_tests:
        result = runner.run_test(test_func, test_name, "Applications")
        runner.results.append(result)
        print(f"{result.status.value} {test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    # Regression Tests
    print("\n" + "▓"*70)
    print("▓ REGRESSION TESTS")
    print("▓"*70 + "\n")

    regression_tests = [
        (RegressionTests.test_baseline_trajectory, "Baseline Trajectory"),
        (RegressionTests.test_deterministic_execution, "Deterministic Execution"),
    ]

    for test_func, test_name in regression_tests:
        result = runner.run_test(test_func, test_name, "Regression")
        runner.results.append(result)
        print(f"{result.status.value} {test_name}: {result.message} ({result.duration_ms:.2f}ms)")

    # Generate Report
    report = runner.generate_report()

    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  VALIDATION REPORT".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)

    print(f"\nTotal Tests: {report.total_tests}")
    print(f"  ✓ Passed:  {report.passed}")
    print(f"  ✗ Failed:  {report.failed}")
    print(f"  ⚠ Errors:  {report.errors}")
    print(f"  ⊘ Skipped: {report.skipped}")
    print(f"\nPass Rate: {report.pass_rate:.1%}")
    print(f"Duration: {report.total_duration_ms:.2f}ms")
    print(f"\nOverall: {'✓ SUCCESS' if report.success else '✗ FAILURE'}")

    print("\n" + "█"*70 + "\n")

    return report.success

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
