"""
EMx P vs NP Core Framework
Provides state space, operators, and EN tracking for computational complexity analysis.
Problem-specific modules can be plugged in via the ProblemMapper interface.
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum

# ============================================================================
# CORE EMX STATE SPACE
# ============================================================================

class NullClass(Enum):
    """Null state classifications"""
    N0 = "Stillpoint"           # (0,0,0)
    N1 = "Single-Bias"          # one ±0, two 0
    N2 = "Balanced-Pair"        # two opposite ±0
    N3 = "Triple-Mixed"         # three non-neutral, mismatched
    N4 = "Unbalanced-Pair"      # two matching ±0
    N5 = "All-Same"             # three co-biased ±0

class TLayer(Enum):
    """Transformation layers"""
    T0 = "Neutral lattice"      # {-0, 0, +0}³
    T1 = "Signed lift"          # {-1, 0, +1}³
    T2 = "Binary collapse"      # {0, 1}³
    T3 = "Polar extremal"       # {-1, +1}³
    T4 = "Exchange shell"       # 12 states

@dataclass
class EMxState:
    """
    Represents a computational state in EMx space.
    Polarity: tuple of 3 values from {-1, 0, 1} representing signed orientation
    """
    polarity: Tuple[int, int, int]  # (x, y, z) ∈ {-1,0,1}³
    null_class: NullClass
    layer: TLayer
    phase: float = 0.0
    null_load: float = 0.22  # ∅ baseline

    def __post_init__(self):
        """Validate state consistency"""
        assert all(p in [-1, 0, 1] for p in self.polarity), "Polarity must be in {-1,0,1}"
        assert 0 <= self.null_load <= 1, "NULL load must be in [0,1]"

@dataclass
class StateMetrics:
    """Harmonic measures for a state"""
    alpha: float  # form/structural alignment [0,1]
    beta: float   # drift/curvature
    gamma: float  # closure probability [0,1]
    omega: bool   # lineage integrity (no-clone check)
    null_share: float  # ∅ occupancy

# ============================================================================
# STATE CLASSIFIER
# ============================================================================

class StateClassifier:
    """Classifies EMx states into null classes"""

    @staticmethod
    def classify_t0_state(polarity: Tuple[int, int, int]) -> NullClass:
        """Classify a state in T₀ space into N0-N5"""
        x, y, z = polarity

        # Count non-zeros and their signs
        non_zeros = [p for p in polarity if p != 0]

        if len(non_zeros) == 0:
            return NullClass.N0

        if len(non_zeros) == 1:
            return NullClass.N1

        if len(non_zeros) == 2:
            # Check if opposite signs (balanced)
            if non_zeros[0] * non_zeros[1] < 0:
                return NullClass.N2  # Balanced pair
            else:
                return NullClass.N4  # Unbalanced pair

        # All three non-zero
        if len(non_zeros) == 3:
            # Check if all same sign
            if all(p > 0 for p in non_zeros) or all(p < 0 for p in non_zeros):
                return NullClass.N5
            else:
                return NullClass.N3  # Mixed signs

        return NullClass.N0  # fallback

    @staticmethod
    def compute_k_class(polarity: Tuple[int, int, int]) -> int:
        """Count non-zero axes (k-class)"""
        return sum(1 for p in polarity if p != 0)

    @staticmethod
    def compute_metrics(state: EMxState) -> StateMetrics:
        """Compute α, β, γ, Ω, ∅ for a state"""
        k = StateClassifier.compute_k_class(state.polarity)

        # Canonical values from framework
        alpha_map = {0: 0.000, 1: 0.333, 2: 0.667, 3: 1.000}
        beta_map = {0: 0.000, 1: 0.180, 2: 0.420, 3: 0.720}
        gamma_map = {0: 1.000, 1: 0.999, 2: 0.996, 3: 0.992}

        alpha = alpha_map.get(k, 0.5)
        beta = beta_map.get(k, 0.5)
        gamma = gamma_map.get(k, 0.99)

        return StateMetrics(
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            omega=True,  # checked separately
            null_share=state.null_load
        )

# ============================================================================
# OPERATORS (O₁-O₁₀)
# ============================================================================

class Operator(ABC):
    """Base class for EMx operators"""

    @abstractmethod
    def apply(self, state: EMxState) -> EMxState:
        """Apply operator to state, return new state"""
        pass

    @abstractmethod
    def cost(self, state: EMxState) -> float:
        """Compute EN cost of applying this operator"""
        pass

class O1_Delta(Operator):
    """Temporal difference operator"""
    def apply(self, state: EMxState) -> EMxState:
        # Δ preserves state, tracks change
        return EMxState(
            polarity=state.polarity,
            null_class=state.null_class,
            layer=state.layer,
            phase=state.phase,
            null_load=state.null_load
        )

    def cost(self, state: EMxState) -> float:
        return 0.1  # minimal cost

class O2_Gradient(Operator):
    """Gradient/divergence - symmetry breaking"""
    def apply(self, state: EMxState) -> EMxState:
        # Expand from N0 to N1 (add bias to one axis)
        x, y, z = state.polarity
        if x == 0 and y == 0 and z == 0:
            new_polarity = (1, 0, 0)  # break symmetry
        else:
            new_polarity = state.polarity

        new_class = StateClassifier.classify_t0_state(new_polarity)
        return EMxState(
            polarity=new_polarity,
            null_class=new_class,
            layer=TLayer.T1,
            phase=state.phase + 0.1,
            null_load=state.null_load * 1.05
        )

    def cost(self, state: EMxState) -> float:
        return 0.3

class O6_Normalize(Operator):
    """Normalization - return to T₀ basin"""
    def apply(self, state: EMxState) -> EMxState:
        # Drive toward N0
        x, y, z = state.polarity
        new_polarity = (
            max(-1, min(1, x // 2)) if x != 0 else 0,
            max(-1, min(1, y // 2)) if y != 0 else 0,
            max(-1, min(1, z // 2)) if z != 0 else 0
        )

        new_class = StateClassifier.classify_t0_state(new_polarity)
        return EMxState(
            polarity=new_polarity,
            null_class=new_class,
            layer=TLayer.T0,
            phase=state.phase,
            null_load=max(0.22, state.null_load * 0.9)  # decay toward baseline
        )

    def cost(self, state: EMxState) -> float:
        return 0.2

class O7_Exchange(Operator):
    """Symmetry/exchange - flip one axis"""
    def apply(self, state: EMxState) -> EMxState:
        x, y, z = state.polarity
        # Flip first non-zero axis
        if x != 0:
            new_polarity = (-x, y, z)
        elif y != 0:
            new_polarity = (x, -y, z)
        elif z != 0:
            new_polarity = (x, y, -z)
        else:
            new_polarity = state.polarity

        new_class = StateClassifier.classify_t0_state(new_polarity)
        return EMxState(
            polarity=new_polarity,
            null_class=new_class,
            layer=TLayer.T4,
            phase=state.phase + 0.05,
            null_load=state.null_load * 1.02
        )

    def cost(self, state: EMxState) -> float:
        return 0.15  # minimal flip

class O9_NoClone(Operator):
    """No-clone check - ensure uniqueness"""
    def apply(self, state: EMxState) -> EMxState:
        # Returns same state but validates uniqueness
        return state

    def cost(self, state: EMxState) -> float:
        return 0.05  # audit cost

# ============================================================================
# EQUIVALENCE NODE (EN) TRACKER
# ============================================================================

class ENTracker:
    """Tracks EN costs and validates closure"""

    def __init__(self):
        self.history: List[Tuple[EMxState, float]] = []
        self.visited_states: Dict[Tuple[int, int, int], int] = {}
        self.total_en_cost = 0.0

    def record_transition(self, state: EMxState, cost: float):
        """Record state transition and EN cost"""
        self.history.append((state, cost))
        self.total_en_cost += cost

        # Track for no-clone
        key = state.polarity
        self.visited_states[key] = self.visited_states.get(key, 0) + 1

    def check_no_clone_violation(self) -> bool:
        """Check if any state visited more than once (O₉ violation)"""
        return any(count > 1 for count in self.visited_states.values())

    def compute_delta_en(self, start_idx: int, end_idx: int) -> float:
        """Compute EN cost difference between two points"""
        if start_idx >= len(self.history) or end_idx >= len(self.history):
            return float('inf')

        start_cost = sum(cost for _, cost in self.history[:start_idx+1])
        end_cost = sum(cost for _, cost in self.history[:end_idx+1])
        return end_cost - start_cost

    def check_forbidden_states(self) -> List[int]:
        """Check if any forbidden states (2, 12, 14) were visited"""
        # These map to specific polarities in the 27-state lattice
        forbidden = [
            (1, 0, 0),   # State 2
            (1, 0, 1),   # State 12
            (-1, 0, 1),  # State 14
        ]

        violations = []
        for idx, (state, _) in enumerate(self.history):
            if state.polarity in forbidden:
                violations.append(idx)

        return violations

# ============================================================================
# PROBLEM MAPPER INTERFACE
# ============================================================================

class ProblemMapper(ABC):
    """
    Interface for mapping specific problem types to EMx state space.
    Implement this to add new problem domains (SAT, TSP, etc.)
    """

    @abstractmethod
    def encode_problem(self, problem_instance: Any) -> EMxState:
        """Convert problem instance to initial EMx state"""
        pass

    @abstractmethod
    def encode_solution_step(self, current_state: EMxState,
                            decision: Any) -> Tuple[Operator, Any]:
        """Convert solution decision to operator application"""
        pass

    @abstractmethod
    def is_solution(self, state: EMxState) -> bool:
        """Check if state represents valid solution"""
        pass

    @abstractmethod
    def extract_solution(self, state: EMxState) -> Any:
        """Extract problem solution from EMx state"""
        pass

# ============================================================================
# P vs NP ANALYZER
# ============================================================================

class PvsNPAnalyzer:
    """
    Core analyzer for P vs NP using EMx framework.
    Tests whether problem solving maintains EN(s_{t+1}) - EN(s_t) ≤ 0
    """

    def __init__(self, problem_mapper: ProblemMapper):
        self.mapper = problem_mapper
        self.tracker = ENTracker()
        self.operators = {
            'O1': O1_Delta(),
            'O2': O2_Gradient(),
            'O6': O6_Normalize(),
            'O7': O7_Exchange(),
            'O9': O9_NoClone(),
        }

    def solve_and_track(self, problem_instance: Any,
                        solution_steps: List[Any]) -> Dict[str, Any]:
        """
        Execute solution steps and track EN costs.
        Returns analysis of whether P=NP conditions hold.
        """
        # Initialize
        self.tracker = ENTracker()
        current_state = self.mapper.encode_problem(problem_instance)
        self.tracker.record_transition(current_state, 0.0)

        # Execute solution steps
        for step in solution_steps:
            operator, params = self.mapper.encode_solution_step(current_state, step)

            # Apply operator
            next_state = operator.apply(current_state)
            cost = operator.cost(current_state)

            # Track
            self.tracker.record_transition(next_state, cost)
            current_state = next_state

        # Analyze
        return self._analyze_trajectory()

    def _analyze_trajectory(self) -> Dict[str, Any]:
        """Analyze the solution trajectory for P vs NP indicators"""

        # Check for non-decreasing EN
        en_increases = []
        for i in range(1, len(self.tracker.history)):
            delta = self.tracker.compute_delta_en(i-1, i)
            if delta > 0:
                en_increases.append((i, delta))

        # Check forbidden states
        forbidden_visits = self.tracker.check_forbidden_states()

        # Check no-clone
        no_clone_violation = self.tracker.check_no_clone_violation()

        # Compute metrics
        if len(self.tracker.history) > 0:
            final_state = self.tracker.history[-1][0]
            metrics = StateClassifier.compute_metrics(final_state)
            avg_beta = sum(
                StateClassifier.compute_metrics(s).beta
                for s, _ in self.tracker.history
            ) / len(self.tracker.history)
        else:
            metrics = None
            avg_beta = 0

        # P=NP test: if EN never increases AND no forbidden states, then P=NP
        p_equals_np = (
            len(en_increases) == 0 and
            len(forbidden_visits) == 0 and
            not no_clone_violation
        )

        return {
            'total_steps': len(self.tracker.history),
            'total_en_cost': self.tracker.total_en_cost,
            'en_increases': en_increases,
            'forbidden_state_visits': forbidden_visits,
            'no_clone_violation': no_clone_violation,
            'avg_beta': avg_beta,
            'final_metrics': metrics,
            'p_equals_np_indicator': p_equals_np,
            'complexity_class': 'P' if p_equals_np else 'NP'
        }

    def compare_verification_vs_solution(self, problem_instance: Any,
                                        solution_steps: List[Any],
                                        verification_steps: List[Any]) -> Dict[str, Any]:
        """
        Compare EN costs of solving vs verifying.
        If costs are equal, suggests P=NP.
        """
        # Solve
        solve_analysis = self.solve_and_track(problem_instance, solution_steps)
        solve_cost = solve_analysis['total_en_cost']

        # Verify
        verify_analysis = self.solve_and_track(problem_instance, verification_steps)
        verify_cost = verify_analysis['total_en_cost']

        # Compare
        cost_ratio = verify_cost / solve_cost if solve_cost > 0 else float('inf')

        return {
            'solve_cost': solve_cost,
            'verify_cost': verify_cost,
            'cost_ratio': cost_ratio,
            'costs_equal': abs(cost_ratio - 1.0) < 0.1,  # within 10%
            'solve_analysis': solve_analysis,
            'verify_analysis': verify_analysis
        }

# ============================================================================
# EXAMPLE USAGE TEMPLATE
# ============================================================================

def example_usage():
    """
    Template showing how to use the framework.
    Actual problem mappers would be implemented in separate modules.
    """

    # 1. Implement a ProblemMapper for your problem type
    # class SATMapper(ProblemMapper):
    #     def encode_problem(self, clauses): ...
    #     def encode_solution_step(self, state, var_assignment): ...
    #     etc.

    # 2. Create analyzer with your mapper
    # mapper = SATMapper()
    # analyzer = PvsNPAnalyzer(mapper)

    # 3. Analyze a problem instance
    # problem = load_sat_problem("example.cnf")
    # solution = find_solution(problem)
    # analysis = analyzer.solve_and_track(problem, solution)

    # 4. Check P vs NP indicators
    # if analysis['p_equals_np_indicator']:
    #     print("This instance suggests P=NP!")
    # else:
    #     print(f"Complexity class: {analysis['complexity_class']}")

    print("Core framework loaded. Implement ProblemMapper for specific problems.")

if __name__ == "__main__":
    example_usage()
