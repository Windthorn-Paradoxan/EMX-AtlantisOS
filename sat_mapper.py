"""
EMx SAT Problem Mapper
Maps Boolean Satisfiability (SAT) problems to EMx state space.
Demonstrates P vs NP analysis on a canonical NP-complete problem.
"""

from typing import List, Tuple, Set, Dict, Any, Optional
from dataclasses import dataclass
from emx_pvsnp_core import (
    ProblemMapper, EMxState, Operator, NullClass, TLayer,
    StateClassifier, O1_Delta, O2_Gradient, O6_Normalize, O7_Exchange
)

# ============================================================================
# SAT PROBLEM REPRESENTATION
# ============================================================================

@dataclass
class Literal:
    """A literal is a variable or its negation"""
    variable: int  # variable number (1-indexed)
    negated: bool  # True if ¬variable

    def __repr__(self):
        return f"{'¬' if self.negated else ''}{self.variable}"

    def __hash__(self):
        return hash((self.variable, self.negated))

@dataclass
class Clause:
    """A clause is a disjunction of literals"""
    literals: List[Literal]

    def __repr__(self):
        return f"({' ∨ '.join(str(lit) for lit in self.literals)})"

    def is_satisfied(self, assignment: Dict[int, bool]) -> bool:
        """Check if clause is satisfied by assignment"""
        for lit in self.literals:
            if lit.variable in assignment:
                var_value = assignment[lit.variable]
                if (not lit.negated and var_value) or (lit.negated and not var_value):
                    return True
        return False

@dataclass
class SATInstance:
    """A SAT problem in CNF (Conjunctive Normal Form)"""
    num_variables: int
    clauses: List[Clause]

    def __repr__(self):
        return f"SAT({self.num_variables} vars, {len(self.clauses)} clauses)"

    def is_satisfied(self, assignment: Dict[int, bool]) -> bool:
        """Check if all clauses are satisfied"""
        return all(clause.is_satisfied(assignment) for clause in self.clauses)

    @classmethod
    def from_cnf_string(cls, cnf: str) -> 'SATInstance':
        """
        Parse simple CNF format:
        "3 variables: (1 v -2) & (2 v 3) & (-1 v -3)"
        """
        lines = cnf.strip().split('\n')

        # Parse number of variables
        num_vars = int(lines[0].split()[0])

        # Parse clauses
        clauses = []
        clause_str = ' '.join(lines[1:])
        clause_parts = clause_str.split('&')

        for part in clause_parts:
            part = part.strip().strip('()')
            literals = []
            for lit_str in part.split('v'):
                lit_str = lit_str.strip()
                if lit_str.startswith('-'):
                    literals.append(Literal(int(lit_str[1:]), negated=True))
                else:
                    literals.append(Literal(int(lit_str), negated=False))
            clauses.append(Clause(literals))

        return cls(num_vars, clauses)

# ============================================================================
# SAT DECISION REPRESENTATION
# ============================================================================

@dataclass
class SATDecision:
    """A decision to assign a variable"""
    variable: int
    value: bool  # True or False

    def __repr__(self):
        return f"{self.variable}={'T' if self.value else 'F'}"

# ============================================================================
# SAT TO EMX MAPPER
# ============================================================================

class SATMapper(ProblemMapper):
    """
    Maps SAT problems to EMx state space.

    Encoding strategy:
    - Each variable assignment affects polarity
    - Satisfied clauses reduce drift (β)
    - Conflicts increase NULL load (∅)
    - Full solution reaches N0 (stillpoint)
    """

    def __init__(self):
        self.current_instance: Optional[SATInstance] = None
        self.current_assignment: Dict[int, bool] = {}

    def encode_problem(self, problem_instance: SATInstance) -> EMxState:
        """
        Encode SAT problem as initial EMx state.
        Start at N0 (no assignments made yet).
        """
        self.current_instance = problem_instance
        self.current_assignment = {}

        # Initial state: neutral (0,0,0) at N0
        return EMxState(
            polarity=(0, 0, 0),
            null_class=NullClass.N0,
            layer=TLayer.T0,
            phase=0.0,
            null_load=0.22  # baseline
        )

    def encode_solution_step(self, current_state: EMxState,
                            decision: SATDecision) -> Tuple[Operator, Any]:
        """
        Encode a variable assignment as operator application.

        Strategy:
        - Assignment adds bias (O2 gradient)
        - Conflict triggers exchange (O7 flip)
        - Progress toward solution uses normalize (O6)
        """
        # Record assignment
        self.current_assignment[decision.variable] = decision.value

        # Check current satisfaction
        satisfied_clauses = sum(
            1 for clause in self.current_instance.clauses
            if clause.is_satisfied(self.current_assignment)
        )
        total_clauses = len(self.current_instance.clauses)
        satisfaction_ratio = satisfied_clauses / total_clauses if total_clauses > 0 else 0

        # Determine operator based on decision impact
        if satisfaction_ratio < 0.3:
            # Early stage: expand search space (O2)
            return O2_Gradient(), {'satisfaction': satisfaction_ratio}
        elif satisfaction_ratio < 0.7:
            # Middle stage: exchange/flip to resolve conflicts (O7)
            return O7_Exchange(), {'satisfaction': satisfaction_ratio}
        else:
            # Late stage: normalize toward solution (O6)
            return O6_Normalize(), {'satisfaction': satisfaction_ratio}

    def _compute_polarity_from_assignment(self) -> Tuple[int, int, int]:
        """
        Map variable assignments to 3D polarity.
        Uses hash-based projection to 3 axes.
        """
        if not self.current_assignment:
            return (0, 0, 0)

        # Project variables onto 3 axes
        x_vars = [v for v in self.current_assignment.keys() if v % 3 == 1]
        y_vars = [v for v in self.current_assignment.keys() if v % 3 == 2]
        z_vars = [v for v in self.current_assignment.keys() if v % 3 == 0]

        def axis_polarity(vars_list):
            if not vars_list:
                return 0
            true_count = sum(1 for v in vars_list if self.current_assignment[v])
            false_count = len(vars_list) - true_count
            if true_count > false_count:
                return 1
            elif false_count > true_count:
                return -1
            else:
                return 0

        return (
            axis_polarity(x_vars),
            axis_polarity(y_vars),
            axis_polarity(z_vars)
        )

    def is_solution(self, state: EMxState) -> bool:
        """Check if current assignment satisfies all clauses"""
        if self.current_instance is None:
            return False

        # All variables must be assigned
        if len(self.current_assignment) < self.current_instance.num_variables:
            return False

        # All clauses must be satisfied
        return self.current_instance.is_satisfied(self.current_assignment)

    def extract_solution(self, state: EMxState) -> Dict[int, bool]:
        """Extract variable assignment from state"""
        return self.current_assignment.copy()

# ============================================================================
# SAT SOLVER (DPLL-style for demonstration)
# ============================================================================

class SimpleSATSolver:
    """
    Simple SAT solver using DPLL algorithm.
    Generates solution steps for EMx analysis.
    """

    def __init__(self, instance: SATInstance):
        self.instance = instance
        self.solution_steps: List[SATDecision] = []

    def solve(self) -> Tuple[bool, List[SATDecision]]:
        """
        Attempt to solve SAT instance.
        Returns (satisfiable, list of decisions).
        """
        assignment = {}
        self.solution_steps = []

        result = self._dpll(assignment, 0)
        return result, self.solution_steps

    def _dpll(self, assignment: Dict[int, bool], depth: int) -> bool:
        """DPLL recursive solver"""
        # Check if satisfied
        if self.instance.is_satisfied(assignment):
            return True

        # Check if any clause is unsatisfiable
        for clause in self.instance.clauses:
            all_false = True
            for lit in clause.literals:
                if lit.variable not in assignment:
                    all_false = False
                    break
                var_value = assignment[lit.variable]
                if (not lit.negated and var_value) or (lit.negated and not var_value):
                    all_false = False
                    break
            if all_false:
                return False

        # Unit propagation
        unit_clause = self._find_unit_clause(assignment)
        if unit_clause:
            lit = unit_clause[0]
            value = not lit.negated
            assignment[lit.variable] = value
            self.solution_steps.append(SATDecision(lit.variable, value))
            return self._dpll(assignment, depth + 1)

        # Choose next variable
        next_var = self._choose_variable(assignment)
        if next_var is None:
            return self.instance.is_satisfied(assignment)

        # Try True
        assignment[next_var] = True
        self.solution_steps.append(SATDecision(next_var, True))
        if self._dpll(assignment, depth + 1):
            return True

        # Backtrack, try False
        del assignment[next_var]
        self.solution_steps.pop()

        assignment[next_var] = False
        self.solution_steps.append(SATDecision(next_var, False))
        if self._dpll(assignment, depth + 1):
            return True

        # Backtrack
        del assignment[next_var]
        self.solution_steps.pop()

        return False

    def _find_unit_clause(self, assignment: Dict[int, bool]) -> Optional[List[Literal]]:
        """Find a clause with only one unassigned literal"""
        for clause in self.instance.clauses:
            unassigned = []
            satisfied = False

            for lit in clause.literals:
                if lit.variable in assignment:
                    var_value = assignment[lit.variable]
                    if (not lit.negated and var_value) or (lit.negated and not var_value):
                        satisfied = True
                        break
                else:
                    unassigned.append(lit)

            if not satisfied and len(unassigned) == 1:
                return unassigned

        return None

    def _choose_variable(self, assignment: Dict[int, bool]) -> Optional[int]:
        """Choose next unassigned variable"""
        for var in range(1, self.instance.num_variables + 1):
            if var not in assignment:
                return var
        return None

# ============================================================================
# VERIFICATION STEPS GENERATOR
# ============================================================================

class SATVerifier:
    """
    Generate verification steps for a SAT solution.
    Verification is checking each clause once.
    """

    @staticmethod
    def generate_verification_steps(instance: SATInstance,
                                    solution: Dict[int, bool]) -> List[SATDecision]:
        """
        Generate steps to verify a solution.
        In SAT, verification is O(n*m) where n=vars, m=clauses.
        """
        # Verification just assigns variables in order and checks
        steps = []
        for var in range(1, instance.num_variables + 1):
            if var in solution:
                steps.append(SATDecision(var, solution[var]))

        return steps

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def demo_sat_pvsnp():
    """Demonstrate SAT P vs NP analysis using EMx"""
    from emx_pvsnp_core import PvsNPAnalyzer

    print("="*70)
    print("EMx P vs NP Analysis: SAT Problem")
    print("="*70)

    # Create a simple SAT instance
    # (1 ∨ 2) ∧ (¬1 ∨ 3) ∧ (¬2 ∨ ¬3)
    sat_cnf = """3
(1 v 2) & (-1 v 3) & (-2 v -3)"""

    instance = SATInstance.from_cnf_string(sat_cnf)
    print(f"\nProblem: {instance}")
    for i, clause in enumerate(instance.clauses):
        print(f"  Clause {i+1}: {clause}")

    # Solve
    print("\n" + "-"*70)
    print("SOLVING...")
    print("-"*70)
    solver = SimpleSATSolver(instance)
    satisfiable, solution_steps = solver.solve()

    if satisfiable:
        print(f"✓ Satisfiable! Found solution in {len(solution_steps)} steps:")
        for step in solution_steps:
            print(f"  {step}")
    else:
        print("✗ Unsatisfiable")
        return

    # Extract final assignment
    mapper = SATMapper()
    initial_state = mapper.encode_problem(instance)
    for step in solution_steps:
        mapper.encode_solution_step(initial_state, step)
    final_assignment = mapper.extract_solution(initial_state)

    print(f"\nFinal assignment: {final_assignment}")
    print(f"Verified: {instance.is_satisfied(final_assignment)}")

    # Generate verification steps
    print("\n" + "-"*70)
    print("VERIFICATION...")
    print("-"*70)
    verification_steps = SATVerifier.generate_verification_steps(instance, final_assignment)
    print(f"Verification requires {len(verification_steps)} steps:")
    for step in verification_steps:
        print(f"  {step}")

    # EMx Analysis
    print("\n" + "="*70)
    print("EMx P vs NP ANALYSIS")
    print("="*70)

    analyzer = PvsNPAnalyzer(mapper)
    comparison = analyzer.compare_verification_vs_solution(
        instance,
        solution_steps,
        verification_steps
    )

    print(f"\nSolving EN cost:      {comparison['solve_cost']:.3f}")
    print(f"Verification EN cost: {comparison['verify_cost']:.3f}")
    print(f"Cost ratio (V/S):     {comparison['cost_ratio']:.3f}")
    print(f"Costs equal:          {comparison['costs_equal']}")

    solve_analysis = comparison['solve_analysis']
    print(f"\n--- Solving Analysis ---")
    print(f"Steps: {solve_analysis['total_steps']}")
    print(f"EN increases: {len(solve_analysis['en_increases'])}")
    print(f"Forbidden states: {solve_analysis['forbidden_state_visits']}")
    print(f"No-clone violation: {solve_analysis['no_clone_violation']}")
    print(f"Average β (drift): {solve_analysis['avg_beta']:.3f}")
    print(f"Complexity class: {solve_analysis['complexity_class']}")

    verify_analysis = comparison['verify_analysis']
    print(f"\n--- Verification Analysis ---")
    print(f"Steps: {verify_analysis['total_steps']}")
    print(f"EN increases: {len(verify_analysis['en_increases'])}")
    print(f"Average β (drift): {verify_analysis['avg_beta']:.3f}")
    print(f"Complexity class: {verify_analysis['complexity_class']}")

    print("\n" + "="*70)
    if comparison['costs_equal']:
        print("⚠️  COSTS ARE EQUAL → Suggests P=NP for this instance!")
    else:
        print(f"✓ Solving is {comparison['cost_ratio']:.2f}x harder than verification")
        print("  (Expected for NP-complete problems)")
    print("="*70)

if __name__ == "__main__":
    demo_sat_pvsnp()
