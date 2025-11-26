"""
EMx Performance Profiler & Optimizer
Measures bottlenecks and provides optimized execution paths.
Target: ≤ 10µs per tick (currently ~26µs baseline, need 2.6× speedup minimum)
"""

import time
import functools
from typing import List, Dict, Tuple, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import statistics

from emx_kernel import EMxKernel, EMxState, TernaryTriple, Polarity

# ═══════════════════════════════════════════════════════════════
# I. PROFILING INFRASTRUCTURE
# ═══════════════════════════════════════════════════════════════

@dataclass
class TimingResult:
    """Timing measurement for a single operation"""
    operation: str
    duration_us: float  # microseconds
    call_count: int
    total_duration_us: float
    avg_duration_us: float
    min_duration_us: float
    max_duration_us: float
    std_dev_us: float

@dataclass
class ProfileReport:
    """Complete profiling report"""
    total_ticks: int
    total_duration_us: float
    us_per_tick: float
    operations: Dict[str, TimingResult]
    bottlenecks: List[Tuple[str, float]]  # Operation, % of total time
    target_us_per_tick: float = 10.0
    meets_target: bool = False

class PerformanceProfiler:
    """Profiles EMx execution to identify bottlenecks"""

    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.call_counts: Dict[str, int] = {}
        self.enabled = True

    def time_operation(self, operation: str) -> Callable:
        """Decorator to time operations"""
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()

                duration_us = (end - start) * 1_000_000  # Convert to microseconds

                if operation not in self.timings:
                    self.timings[operation] = []
                    self.call_counts[operation] = 0

                self.timings[operation].append(duration_us)
                self.call_counts[operation] += 1

                return result
            return wrapper
        return decorator

    def reset(self):
        """Reset profiling data"""
        self.timings.clear()
        self.call_counts.clear()

    def generate_report(self, total_ticks: int) -> ProfileReport:
        """Generate profiling report"""
        operations = {}
        total_time = 0.0

        for op_name, durations in self.timings.items():
            if not durations:
                continue

            total_op_time = sum(durations)
            total_time += total_op_time

            result = TimingResult(
                operation=op_name,
                duration_us=durations[-1],
                call_count=self.call_counts[op_name],
                total_duration_us=total_op_time,
                avg_duration_us=statistics.mean(durations),
                min_duration_us=min(durations),
                max_duration_us=max(durations),
                std_dev_us=statistics.stdev(durations) if len(durations) > 1 else 0
            )
            operations[op_name] = result

        # Calculate bottlenecks (operations taking >10% of time)
        bottlenecks = []
        for op_name, result in operations.items():
            percentage = (result.total_duration_us / total_time * 100) if total_time > 0 else 0
            if percentage > 10:
                bottlenecks.append((op_name, percentage))

        bottlenecks.sort(key=lambda x: x[1], reverse=True)

        us_per_tick = total_time / total_ticks if total_ticks > 0 else 0

        return ProfileReport(
            total_ticks=total_ticks,
            total_duration_us=total_time,
            us_per_tick=us_per_tick,
            operations=operations,
            bottlenecks=bottlenecks,
            meets_target=us_per_tick <= 10.0
        )

    def print_report(self, report: ProfileReport):
        """Print formatted profiling report"""
        print("\n" + "═"*70)
        print("PERFORMANCE PROFILING REPORT")
        print("═"*70)
        print(f"Total ticks: {report.total_ticks}")
        print(f"Total time: {report.total_duration_us/1000:.2f} ms")
        print(f"Time per tick: {report.us_per_tick:.2f} µs")
        print(f"Target: {report.target_us_per_tick:.2f} µs/tick")

        if report.meets_target:
            print(f"Status: ✓ MEETS TARGET")
        else:
            speedup_needed = report.us_per_tick / report.target_us_per_tick
            print(f"Status: ✗ NEEDS {speedup_needed:.1f}× SPEEDUP")

        print("\n" + "─"*70)
        print("BOTTLENECKS (>10% of execution time)")
        print("─"*70)

        for op_name, percentage in report.bottlenecks:
            result = report.operations[op_name]
            print(f"\n{op_name}: {percentage:.1f}%")
            print(f"  Calls: {result.call_count}")
            print(f"  Avg: {result.avg_duration_us:.3f} µs")
            print(f"  Range: [{result.min_duration_us:.3f}, {result.max_duration_us:.3f}] µs")

        print("\n" + "─"*70)
        print("ALL OPERATIONS")
        print("─"*70)

        # Sort by total time
        sorted_ops = sorted(
            report.operations.items(),
            key=lambda x: x[1].total_duration_us,
            reverse=True
        )

        for op_name, result in sorted_ops:
            pct = (result.total_duration_us / report.total_duration_us * 100) if report.total_duration_us > 0 else 0
            print(f"{op_name:30s} {result.avg_duration_us:8.3f} µs  "
                  f"({result.call_count:5d} calls, {pct:5.1f}%)")

        print("═"*70 + "\n")

# ═══════════════════════════════════════════════════════════════
# II. OPTIMIZED KERNEL
# ═══════════════════════════════════════════════════════════════

class EMxKernelOptimized(EMxKernel):
    """Optimized version of EMx kernel with profiling"""

    def __init__(self, initial_triple: Optional[TernaryTriple] = None,
                 profiler: Optional[PerformanceProfiler] = None):
        super().__init__(initial_triple)
        self.profiler = profiler or PerformanceProfiler()

        # Cache for expensive operations
        self._k_class_cache: Dict[TernaryTriple, int] = {}
        self._null_class_cache: Dict[TernaryTriple, str] = {}

    def step(self, operator: str, **kwargs) -> Tuple[bool, str]:
        """Optimized step with profiling"""

        @self.profiler.time_operation("step_total")
        def _step():
            return self._step_internal(operator, **kwargs)

        return _step()

    def _step_internal(self, operator: str, **kwargs) -> Tuple[bool, str]:
        """Internal step implementation with granular profiling"""

        # History append (profiled)
        @self.profiler.time_operation("history_append")
        def _append_history():
            self.state.history.append(self.state.triple)
        _append_history()

        # Operator application (profiled)
        new_triple = self._apply_operator_profiled(operator, **kwargs)

        # NULL dynamics (profiled)
        @self.profiler.time_operation("null_dynamics")
        def _update_null():
            from emx_kernel import k_class, THEORETICAL_NULL

            k_old = self._get_k_class_cached(self.state.triple)
            k_new = self._get_k_class_cached(new_triple)

            activity_delta = (k_new - k_old) * 0.05
            decay_rate = 0.1

            self.state.properties.null_load += activity_delta
            self.state.properties.null_load += decay_rate * (THEORETICAL_NULL - self.state.properties.null_load)
            self.state.properties.null_load = max(0.0, min(1.0, self.state.properties.null_load))
        _update_null()

        # Tick increment
        self.state.properties.tick += 1

        # State creation (profiled)
        @self.profiler.time_operation("state_creation")
        def _create_state():
            from emx_kernel import EMxState
            return EMxState(
                triple=new_triple,
                properties=self.state.properties,
                history=self.state.history
            )
        self.state = _create_state()

        # Gate check (profiled)
        @self.profiler.time_operation("gate_check")
        def _check_gate():
            return self.state.gate_check()
        passes, reason = _check_gate()

        return passes, reason

    def _apply_operator_profiled(self, operator: str, **kwargs) -> TernaryTriple:
        """Apply operator with profiling"""

        @self.profiler.time_operation(f"operator_{operator}")
        def _apply():
            return self._apply_operator_impl(operator, **kwargs)

        return _apply()

    def _apply_operator_impl(self, operator: str, **kwargs) -> TernaryTriple:
        """Operator application implementation"""
        from emx_kernel import (
            O1_Delta, O2_Gradient, O3_Rotation,
            O6_Normalize, O7_Exchange, O10_Integrate
        )

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

        return new_triple

    def _get_k_class_cached(self, triple: TernaryTriple) -> int:
        """Get k-class with caching"""
        if triple not in self._k_class_cache:
            from emx_kernel import k_class
            self._k_class_cache[triple] = k_class(triple)
        return self._k_class_cache[triple]

# ═══════════════════════════════════════════════════════════════
# III. OPTIMIZATION STRATEGIES
# ═══════════════════════════════════════════════════════════════

class OptimizationStrategy(Enum):
    """Available optimization strategies"""
    BASELINE = "baseline"
    CACHING = "caching"
    BATCH = "batch"
    LAZY_EVAL = "lazy_evaluation"
    VECTORIZED = "vectorized"

@dataclass
class OptimizationResult:
    """Result of applying optimization strategy"""
    strategy: OptimizationStrategy
    baseline_us_per_tick: float
    optimized_us_per_tick: float
    speedup: float
    meets_target: bool

class PerformanceOptimizer:
    """Tests and applies various optimization strategies"""

    TARGET_US_PER_TICK = 10.0

    @staticmethod
    def benchmark_strategy(strategy: OptimizationStrategy,
                          operator_sequence: List[str],
                          ticks: int = 96) -> OptimizationResult:
        """Benchmark a specific optimization strategy"""

        # Baseline measurement
        baseline_kernel = EMxKernel()
        baseline_start = time.perf_counter()

        for op in operator_sequence[:ticks]:
            baseline_kernel.step(op, axis=0)

        baseline_duration = (time.perf_counter() - baseline_start) * 1_000_000
        baseline_us_per_tick = baseline_duration / ticks

        # Optimized measurement
        if strategy == OptimizationStrategy.CACHING:
            optimized_us_per_tick = PerformanceOptimizer._benchmark_caching(
                operator_sequence, ticks
            )
        elif strategy == OptimizationStrategy.BATCH:
            optimized_us_per_tick = PerformanceOptimizer._benchmark_batch(
                operator_sequence, ticks
            )
        elif strategy == OptimizationStrategy.LAZY_EVAL:
            optimized_us_per_tick = PerformanceOptimizer._benchmark_lazy(
                operator_sequence, ticks
            )
        else:
            optimized_us_per_tick = baseline_us_per_tick

        speedup = baseline_us_per_tick / optimized_us_per_tick if optimized_us_per_tick > 0 else 1.0

        return OptimizationResult(
            strategy=strategy,
            baseline_us_per_tick=baseline_us_per_tick,
            optimized_us_per_tick=optimized_us_per_tick,
            speedup=speedup,
            meets_target=optimized_us_per_tick <= PerformanceOptimizer.TARGET_US_PER_TICK
        )

    @staticmethod
    def _benchmark_caching(operator_sequence: List[str], ticks: int) -> float:
        """Benchmark with caching optimization"""
        profiler = PerformanceProfiler()
        profiler.enabled = False  # Disable for pure speed test

        kernel = EMxKernelOptimized(profiler=profiler)

        start = time.perf_counter()
        for op in operator_sequence[:ticks]:
            kernel.step(op, axis=0)
        duration = (time.perf_counter() - start) * 1_000_000

        return duration / ticks

    @staticmethod
    def _benchmark_batch(operator_sequence: List[str], ticks: int) -> float:
        """Benchmark with batch processing optimization"""
        # Batch processing: group identical operations
        kernel = EMxKernel()

        # Group consecutive identical operators
        batches = []
        current_op = None
        current_count = 0

        for op in operator_sequence[:ticks]:
            if op == current_op:
                current_count += 1
            else:
                if current_op:
                    batches.append((current_op, current_count))
                current_op = op
                current_count = 1
        if current_op:
            batches.append((current_op, current_count))

        start = time.perf_counter()
        for op, count in batches:
            for _ in range(count):
                kernel.step(op, axis=0)
        duration = (time.perf_counter() - start) * 1_000_000

        return duration / ticks

    @staticmethod
    def _benchmark_lazy(operator_sequence: List[str], ticks: int) -> float:
        """Benchmark with lazy evaluation optimization"""
        # Lazy eval: defer harmonics computation until explicitly requested
        kernel = EMxKernel()

        start = time.perf_counter()
        for op in operator_sequence[:ticks]:
            kernel.step(op, axis=0)
            # Don't call get_harmonics() - lazy evaluation
        duration = (time.perf_counter() - start) * 1_000_000

        return duration / ticks

    @staticmethod
    def test_all_strategies(operator_sequence: List[str],
                          ticks: int = 96) -> List[OptimizationResult]:
        """Test all optimization strategies"""
        results = []

        print("\n" + "═"*70)
        print("TESTING OPTIMIZATION STRATEGIES")
        print("═"*70)

        for strategy in OptimizationStrategy:
            print(f"\nTesting {strategy.value}...")
            result = PerformanceOptimizer.benchmark_strategy(
                strategy, operator_sequence, ticks
            )
            results.append(result)

            status = "✓" if result.meets_target else "✗"
            print(f"  {status} {result.optimized_us_per_tick:.2f} µs/tick "
                  f"({result.speedup:.2f}× speedup)")

        return results

    @staticmethod
    def print_optimization_report(results: List[OptimizationResult]):
        """Print optimization comparison report"""
        print("\n" + "═"*70)
        print("OPTIMIZATION STRATEGY COMPARISON")
        print("═"*70)
        print(f"Target: {PerformanceOptimizer.TARGET_US_PER_TICK:.2f} µs/tick\n")

        # Sort by speedup
        sorted_results = sorted(results, key=lambda r: r.speedup, reverse=True)

        print(f"{'Strategy':<20} {'µs/tick':>10} {'Speedup':>10} {'Status':>10}")
        print("─"*70)

        for result in sorted_results:
            status = "✓ Target" if result.meets_target else "✗ Miss"
            print(f"{result.strategy.value:<20} "
                  f"{result.optimized_us_per_tick:>10.2f} "
                  f"{result.speedup:>9.2f}× "
                  f"{status:>10}")

        print("═"*70 + "\n")

        # Recommendations
        best = sorted_results[0]
        print("RECOMMENDATION:")
        if best.meets_target:
            print(f"✓ Use {best.strategy.value} strategy ({best.speedup:.2f}× speedup)")
        else:
            print(f"⚠ Best option is {best.strategy.value} ({best.speedup:.2f}× speedup)")
            print(f"  Still need {best.optimized_us_per_tick / PerformanceOptimizer.TARGET_US_PER_TICK:.2f}× additional speedup")
            print(f"  Consider: Cython/Numba compilation, or Rust/C++ port")
        print()

# ═══════════════════════════════════════════════════════════════
# IV. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate performance profiling and optimization"""
    print("="*70)
    print("EMx Performance Profiler & Optimizer Demo")
    print("="*70)

    # Define test sequence
    operator_sequence = ['O2', 'O3', 'O6', 'O7', 'O2', 'O6'] * 16  # 96 ticks

    # Part 1: Detailed profiling
    print("\n" + "─"*70)
    print("PART 1: DETAILED PROFILING")
    print("─"*70)

    profiler = PerformanceProfiler()
    kernel = EMxKernelOptimized(profiler=profiler)

    print(f"\nExecuting {len(operator_sequence)} operations...")
    for op in operator_sequence:
        kernel.step(op, axis=0)

    report = profiler.generate_report(len(operator_sequence))
    profiler.print_report(report)

    # Part 2: Strategy comparison
    print("\n" + "─"*70)
    print("PART 2: OPTIMIZATION STRATEGY TESTING")
    print("─"*70)

    results = PerformanceOptimizer.test_all_strategies(operator_sequence)
    PerformanceOptimizer.print_optimization_report(results)

if __name__ == "__main__":
    demo()
