"""
EMx Financial Suite Integration
Maps financial markets, economic indicators, and monetary dynamics to EMx state space.
Tests if financial cycles correlate with NULL baseline and harmonic metrics.
"""

from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import math

from emx_kernel import (
    EMxKernel, EMxState, TernaryTriple, Polarity,
    Harmonics, k_class, THEORETICAL_NULL
)
from emx_statistical_validator import StatisticalValidator

# ═══════════════════════════════════════════════════════════════
# I. FINANCIAL STATE ENCODING
# ═══════════════════════════════════════════════════════════════

class MarketCondition(Enum):
    """Market sentiment/condition"""
    BEARISH = -1      # Declining
    NEUTRAL = 0       # Sideways
    BULLISH = 1       # Rising

@dataclass
class FinancialState:
    """Complete financial system state"""
    # Market indicators
    price_momentum: float          # Rate of change
    volume_trend: float            # Trading volume trend
    volatility: float              # Market volatility

    # Economic indicators
    inflation_rate: float          # CPI change
    interest_rate: float           # Central bank rate
    unemployment_rate: float       # Jobless rate

    # System health
    liquidity: float              # Market liquidity
    leverage: float               # System leverage
    confidence: float             # Investor confidence

    # EMx mapping
    null_financial: float         # Financial NULL (∅_fin)

    def to_ternary_triple(self) -> TernaryTriple:
        """
        Encode financial state as ternary triple

        x-axis: Price momentum (bear/neutral/bull)
        y-axis: Liquidity (low/neutral/high)
        z-axis: Volatility (low/neutral/high)
        """
        # Price momentum
        if self.price_momentum < -0.1:
            x = Polarity.MINUS_ZERO
        elif self.price_momentum > 0.1:
            x = Polarity.PLUS_ZERO
        else:
            x = Polarity.ZERO

        # Liquidity
        if self.liquidity < 0.4:
            y = Polarity.MINUS_ZERO
        elif self.liquidity > 0.6:
            y = Polarity.PLUS_ZERO
        else:
            y = Polarity.ZERO

        # Volatility
        if self.volatility < 0.15:
            z = Polarity.MINUS_ZERO
        elif self.volatility > 0.25:
            z = Polarity.PLUS_ZERO
        else:
            z = Polarity.ZERO

        return (x, y, z)

class FinancialEncoder:
    """Encode financial data into EMx state space"""

    @staticmethod
    def compute_null_financial(inflation: float,
                               interest_rate: float,
                               unemployment: float,
                               leverage: float) -> float:
        """
        Compute financial NULL (∅_fin)

        Hypothesis: Financial NULL tracks systemic uncertainty/slack
        - High when: inflation uncertain, rates low, unemployment high
        - Low when: economy overheated, no slack

        Baseline ~22% represents healthy reserve capacity
        """
        # Components (normalized to [0,1])
        inflation_component = min(abs(inflation - 0.02) / 0.10, 1.0)  # Distance from 2% target
        rate_component = 1.0 - min(interest_rate / 0.10, 1.0)  # Low rates → high NULL
        unemployment_component = min(unemployment / 0.10, 1.0)  # High unemployment → high NULL
        leverage_component = min(leverage / 5.0, 1.0)  # High leverage → high NULL

        # Weighted average
        null_fin = (
            0.25 * inflation_component +
            0.30 * rate_component +
            0.25 * unemployment_component +
            0.20 * leverage_component
        )

        return null_fin

    @staticmethod
    def encode_market_state(price_change: float,
                           volume: float,
                           volatility: float,
                           inflation: float = 0.02,
                           interest_rate: float = 0.05,
                           unemployment: float = 0.04) -> FinancialState:
        """Encode market conditions into FinancialState"""

        # Compute derived metrics
        liquidity = volume / (1.0 + volatility)  # Simplified
        leverage = 2.0 + volatility * 10  # Proxy: volatility implies leverage
        confidence = 0.5 + 0.3 * price_change - 0.2 * volatility

        # Compute financial NULL
        null_fin = FinancialEncoder.compute_null_financial(
            inflation, interest_rate, unemployment, leverage
        )

        return FinancialState(
            price_momentum=price_change,
            volume_trend=volume,
            volatility=volatility,
            inflation_rate=inflation,
            interest_rate=interest_rate,
            unemployment_rate=unemployment,
            liquidity=liquidity,
            leverage=leverage,
            confidence=confidence,
            null_financial=null_fin
        )

# ═══════════════════════════════════════════════════════════════
# II. FINANCIAL CRISIS DETECTION
# ═══════════════════════════════════════════════════════════════

@dataclass
class CrisisIndicator:
    """Crisis warning indicators"""
    name: str
    threshold: float
    current_value: float
    triggered: bool
    severity: float  # 0-1
    message: str

class FinancialCrisisDetector:
    """Detect financial crises using EMx metrics"""

    # Crisis thresholds
    NULL_CRISIS_THRESHOLD = 0.78      # ∅_fin > 0.78 → system overload
    NULL_DEFLATION_THRESHOLD = 0.10   # ∅_fin < 0.10 → overheated
    BETA_INSTABILITY = 0.60           # β > 0.60 → high drift/instability
    GAMMA_BREAKDOWN = 0.85            # γ < 0.85 → loss of coherence

    @staticmethod
    def detect_crisis(financial_state: FinancialState,
                     emx_harmonics: Harmonics,
                     trajectory: List[EMxState]) -> Tuple[bool, List[CrisisIndicator]]:
        """
        Detect financial crisis conditions

        Crisis indicators:
        1. NULL overload (∅_fin > 0.78): System capacity exceeded
        2. NULL depletion (∅_fin < 0.10): No slack, overheated
        3. High beta (β > 0.60): Excessive drift/instability
        4. Low gamma (γ < 0.85): System coherence breaking down
        5. Rapid leverage expansion
        6. Liquidity crunch
        """
        indicators = []
        crisis_detected = False

        # Indicator 1: NULL overload
        null_overload = financial_state.null_financial > FinancialCrisisDetector.NULL_CRISIS_THRESHOLD
        if null_overload:
            severity = (financial_state.null_financial - FinancialCrisisDetector.NULL_CRISIS_THRESHOLD) / 0.22
            indicators.append(CrisisIndicator(
                name="NULL Overload",
                threshold=FinancialCrisisDetector.NULL_CRISIS_THRESHOLD,
                current_value=financial_state.null_financial,
                triggered=True,
                severity=min(severity, 1.0),
                message=f"Financial NULL {financial_state.null_financial:.2%} exceeds capacity"
            ))
            crisis_detected = True

        # Indicator 2: NULL depletion (overheating)
        null_depleted = financial_state.null_financial < FinancialCrisisDetector.NULL_DEFLATION_THRESHOLD
        if null_depleted:
            severity = (FinancialCrisisDetector.NULL_DEFLATION_THRESHOLD - financial_state.null_financial) / 0.10
            indicators.append(CrisisIndicator(
                name="NULL Depletion",
                threshold=FinancialCrisisDetector.NULL_DEFLATION_THRESHOLD,
                current_value=financial_state.null_financial,
                triggered=True,
                severity=min(severity, 1.0),
                message=f"Economy overheated, no reserve capacity"
            ))
            crisis_detected = True

        # Indicator 3: High beta (instability)
        beta_high = emx_harmonics.beta > FinancialCrisisDetector.BETA_INSTABILITY
        if beta_high:
            severity = (emx_harmonics.beta - FinancialCrisisDetector.BETA_INSTABILITY) / 0.40
            indicators.append(CrisisIndicator(
                name="High Drift",
                threshold=FinancialCrisisDetector.BETA_INSTABILITY,
                current_value=emx_harmonics.beta,
                triggered=True,
                severity=min(severity, 1.0),
                message=f"Market drift β={emx_harmonics.beta:.3f} indicates instability"
            ))
            crisis_detected = True

        # Indicator 4: Low gamma (coherence breakdown)
        gamma_low = emx_harmonics.gamma < FinancialCrisisDetector.GAMMA_BREAKDOWN
        if gamma_low:
            severity = (FinancialCrisisDetector.GAMMA_BREAKDOWN - emx_harmonics.gamma) / 0.15
            indicators.append(CrisisIndicator(
                name="Coherence Breakdown",
                threshold=FinancialCrisisDetector.GAMMA_BREAKDOWN,
                current_value=emx_harmonics.gamma,
                triggered=True,
                severity=min(severity, 1.0),
                message=f"System coherence γ={emx_harmonics.gamma:.3f} deteriorating"
            ))
            crisis_detected = True

        # Indicator 5: Excessive leverage
        leverage_excessive = financial_state.leverage > 4.0
        if leverage_excessive:
            severity = (financial_state.leverage - 4.0) / 6.0
            indicators.append(CrisisIndicator(
                name="Excessive Leverage",
                threshold=4.0,
                current_value=financial_state.leverage,
                triggered=True,
                severity=min(severity, 1.0),
                message=f"Leverage {financial_state.leverage:.1f}× exceeds safe levels"
            ))
            crisis_detected = True

        # Indicator 6: Liquidity crunch
        liquidity_low = financial_state.liquidity < 0.3
        if liquidity_low:
            severity = (0.3 - financial_state.liquidity) / 0.3
            indicators.append(CrisisIndicator(
                name="Liquidity Crunch",
                threshold=0.3,
                current_value=financial_state.liquidity,
                triggered=True,
                severity=min(severity, 1.0),
                message=f"Liquidity {financial_state.liquidity:.2%} dangerously low"
            ))
            crisis_detected = True

        return crisis_detected, indicators

# ═══════════════════════════════════════════════════════════════
# III. INTEREST RATE CONVERGENCE
# ═══════════════════════════════════════════════════════════════

class InterestRateModel:
    """
    Test hypothesis: Interest rates converge to NULL baseline (~22%)

    Rationale:
    - NULL represents system slack/uncertainty
    - Interest rates price time-uncertainty
    - Equilibrium rate should reflect systemic NULL
    """

    @staticmethod
    def compute_natural_rate(null_financial: float,
                            inflation: float,
                            productivity_growth: float = 0.02) -> float:
        """
        Compute natural/neutral interest rate from financial NULL

        Formula: r* = ∅_fin × scaling + inflation + productivity
        """
        # Base rate from NULL (scaled to percentage)
        base_rate = null_financial * 0.30  # Scale 0.22 → ~6.6%

        # Add inflation compensation
        natural_rate = base_rate + inflation + productivity_growth

        return natural_rate

    @staticmethod
    def test_convergence_hypothesis(historical_rates: List[float],
                                   historical_null: List[float],
                                   inflation_series: List[float]) -> Dict[str, Any]:
        """
        Test if interest rates converge to NULL-derived natural rate

        Returns correlation metrics and convergence test
        """
        if len(historical_rates) != len(historical_null) or len(historical_rates) != len(inflation_series):
            return {'error': 'Series length mismatch'}

        # Compute natural rates from NULL
        natural_rates = [
            InterestRateModel.compute_natural_rate(null, inflation)
            for null, inflation in zip(historical_null, inflation_series)
        ]

        # Compute correlation
        mean_actual = sum(historical_rates) / len(historical_rates)
        mean_natural = sum(natural_rates) / len(natural_rates)

        covariance = sum(
            (actual - mean_actual) * (natural - mean_natural)
            for actual, natural in zip(historical_rates, natural_rates)
        ) / len(historical_rates)

        var_actual = sum((r - mean_actual)**2 for r in historical_rates) / len(historical_rates)
        var_natural = sum((r - mean_natural)**2 for r in natural_rates) / len(natural_rates)

        correlation = covariance / (math.sqrt(var_actual) * math.sqrt(var_natural)) if var_actual > 0 and var_natural > 0 else 0

        # Compute RMSE
        rmse = math.sqrt(
            sum((actual - natural)**2 for actual, natural in zip(historical_rates, natural_rates)) / len(historical_rates)
        )

        # Test convergence
        recent_window = min(10, len(historical_rates) // 4)
        recent_actual = historical_rates[-recent_window:]
        recent_natural = natural_rates[-recent_window:]

        recent_diff = [abs(a - n) for a, n in zip(recent_actual, recent_natural)]
        avg_recent_diff = sum(recent_diff) / len(recent_diff)

        converging = avg_recent_diff < 0.02  # Within 2%

        return {
            'correlation': correlation,
            'rmse': rmse,
            'mean_actual_rate': mean_actual,
            'mean_natural_rate': mean_natural,
            'recent_divergence': avg_recent_diff,
            'converging': converging,
            'natural_rate_series': natural_rates
        }

# ═══════════════════════════════════════════════════════════════
# IV. INFLATION-NULL CONNECTION
# ═══════════════════════════════════════════════════════════════

class InflationNullModel:
    """
    Model inflation dynamics using financial NULL

    Hypothesis: Inflation correlates with (1 - ∅_fin)
    - High NULL (slack) → Low inflation
    - Low NULL (tight) → High inflation
    """

    @staticmethod
    def predict_inflation(null_financial: float,
                         current_inflation: float,
                         velocity: float = 1.0) -> float:
        """
        Predict inflation based on financial NULL

        Formula: π_predicted = velocity × (1 - ∅_fin) × scale
        """
        # Capacity utilization proxy
        utilization = 1.0 - null_financial

        # Inflation pressure from utilization
        inflation_pressure = utilization * 0.10 * velocity  # Scale to realistic range

        # Momentum from current inflation
        predicted_inflation = 0.7 * current_inflation + 0.3 * inflation_pressure

        return predicted_inflation

    @staticmethod
    def detect_regime_shift(null_trajectory: List[float],
                           threshold: float = 0.05) -> Tuple[bool, str]:
        """
        Detect inflation regime shifts from NULL trajectory

        Shift occurs when NULL crosses critical thresholds rapidly
        """
        if len(null_trajectory) < 10:
            return False, "Insufficient data"

        recent = null_trajectory[-10:]

        # Check for rapid changes
        max_change = max(abs(recent[i] - recent[i-1]) for i in range(1, len(recent)))

        # Check for threshold crossing
        crosses_high = any(n > 0.78 for n in recent)
        crosses_low = any(n < 0.10 for n in recent)

        if max_change > threshold:
            if crosses_high:
                return True, "Deflationary regime (NULL overload)"
            elif crosses_low:
                return True, "Inflationary regime (NULL depletion)"
            else:
                return True, "Transitional regime"

        return False, "Stable regime"

# ═══════════════════════════════════════════════════════════════
# V. MARKET CYCLE SIMULATOR
# ═══════════════════════════════════════════════════════════════

class MarketCycleSimulator:
    """Simulate market cycles through EMx dynamics"""

    def __init__(self):
        self.kernel = EMxKernel()
        self.financial_history: List[FinancialState] = []
        self.crisis_events: List[Tuple[int, List[CrisisIndicator]]] = []

    def simulate_cycle(self,
                      initial_state: FinancialState,
                      quarters: int = 40,  # 10 years
                      shock_quarters: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Simulate market cycle through multiple quarters

        Returns trajectory, crisis events, and metrics
        """
        current_state = initial_state
        trajectory = []
        null_trajectory = []
        crisis_count = 0

        for quarter in range(quarters):
            # Encode as EMx state
            triple = current_state.to_ternary_triple()
            self.kernel.state.triple = triple
            self.kernel.state.properties.null_load = current_state.null_financial

            # Apply market dynamics operators
            # Expansion: O2 (gradient)
            # Peak: O3 (rotation to downturn)
            # Contraction: O6 (normalize)
            # Trough: O7 (flip to recovery)

            cycle_phase = quarter % 40  # 10-year cycle

            if cycle_phase < 15:  # Expansion
                self.kernel.step('O2', axis=0)
                price_change = 0.02 + 0.01 * (cycle_phase / 15)
            elif cycle_phase < 20:  # Peak
                self.kernel.step('O3', axis=0)
                price_change = 0.01
            elif cycle_phase < 30:  # Contraction
                self.kernel.step('O6', axis=0)
                price_change = -0.03
            else:  # Trough/Recovery
                self.kernel.step('O7', axis=0)
                price_change = -0.01 + 0.02 * ((cycle_phase - 30) / 10)

            # Apply shock if scheduled
            if shock_quarters and quarter in shock_quarters:
                price_change -= 0.10  # Major shock
                self.kernel.step('O6', axis=0)  # Force normalization

            # Update financial state
            harmonics = self.kernel.get_harmonics()

            # Evolve metrics
            volatility = 0.20 + 0.10 * harmonics.beta
            volume = 0.5 + 0.3 * (1 - harmonics.beta)
            inflation = 0.02 + 0.01 * (1 - current_state.null_financial)
            interest_rate = InterestRateModel.compute_natural_rate(
                current_state.null_financial, inflation
            )

            current_state = FinancialEncoder.encode_market_state(
                price_change, volume, volatility,
                inflation, interest_rate, 0.04
            )

            # Store trajectory
            trajectory.append(self.kernel.state)
            null_trajectory.append(current_state.null_financial)
            self.financial_history.append(current_state)

            # Detect crises
            crisis, indicators = FinancialCrisisDetector.detect_crisis(
                current_state, harmonics, trajectory
            )

            if crisis:
                self.crisis_events.append((quarter, indicators))
                crisis_count += 1

        # Compute summary statistics
        avg_null = sum(null_trajectory) / len(null_trajectory)
        null_variance = sum((n - avg_null)**2 for n in null_trajectory) / len(null_trajectory)

        return {
            'trajectory': trajectory,
            'financial_history': self.financial_history,
            'null_trajectory': null_trajectory,
            'crisis_events': self.crisis_events,
            'crisis_count': crisis_count,
            'avg_null': avg_null,
            'null_variance': null_variance,
            'quarters_simulated': quarters
        }

# ═══════════════════════════════════════════════════════════════
# VI. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate financial suite integration"""
    print("="*70)
    print("EMx Financial Suite Integration Demo")
    print("="*70)

    # Test 1: Crisis detection
    print("\n--- Test 1: Crisis Detection ---")

    # Normal conditions
    normal_state = FinancialEncoder.encode_market_state(
        price_change=0.02,
        volume=0.6,
        volatility=0.15,
        inflation=0.02,
        interest_rate=0.05,
        unemployment=0.04
    )

    kernel = EMxKernel(normal_state.to_ternary_triple())
    kernel.state.properties.null_load = normal_state.null_financial

    # Build trajectory
    trajectory = [kernel.state]
    for _ in range(20):
        kernel.step('O2', axis=0)
        trajectory.append(kernel.state)

    harmonics = kernel.get_harmonics()

    crisis, indicators = FinancialCrisisDetector.detect_crisis(
        normal_state, harmonics, trajectory
    )

    print(f"Normal conditions:")
    print(f"  ∅_fin: {normal_state.null_financial:.2%}")
    print(f"  Crisis detected: {crisis}")
    print(f"  Indicators triggered: {len(indicators)}")

    # Crisis conditions
    crisis_state = FinancialEncoder.encode_market_state(
        price_change=-0.15,
        volume=0.2,
        volatility=0.45,
        inflation=0.08,
        interest_rate=0.10,
        unemployment=0.12
    )

    kernel_crisis = EMxKernel(crisis_state.to_ternary_triple())
    kernel_crisis.state.properties.null_load = crisis_state.null_financial

    trajectory_crisis = [kernel_crisis.state]
    for _ in range(20):
        kernel_crisis.step('O6', axis=0)  # Contraction
        trajectory_crisis.append(kernel_crisis.state)

    harmonics_crisis = kernel_crisis.get_harmonics()

    crisis_detected, indicators = FinancialCrisisDetector.detect_crisis(
        crisis_state, harmonics_crisis, trajectory_crisis
    )

    print(f"\nCrisis conditions:")
    print(f"  ∅_fin: {crisis_state.null_financial:.2%}")
    print(f"  Crisis detected: {crisis_detected}")
    print(f"  Indicators:")
    for indicator in indicators:
        print(f"    - {indicator.name}: {indicator.message}")

    # Test 2: Interest rate convergence
    print("\n--- Test 2: Interest Rate - NULL Convergence ---")

    # Simulate historical data
    historical_null = [0.22 + 0.05 * math.sin(i * 0.3) for i in range(40)]
    historical_inflation = [0.02 + 0.01 * math.sin(i * 0.2) for i in range(40)]

    # Actual rates (with some noise)
    historical_rates = [
        InterestRateModel.compute_natural_rate(null, infl) + 0.005 * math.sin(i * 0.5)
        for i, (null, infl) in enumerate(zip(historical_null, historical_inflation))
    ]

    convergence = InterestRateModel.test_convergence_hypothesis(
        historical_rates, historical_null, historical_inflation
    )

    print(f"Historical analysis (40 quarters):")
    print(f"  Correlation: {convergence['correlation']:.3f}")
    print(f"  RMSE: {convergence['rmse']:.4f}")
    print(f"  Mean actual rate: {convergence['mean_actual_rate']:.2%}")
    print(f"  Mean natural rate: {convergence['mean_natural_rate']:.2%}")
    print(f"  Converging: {convergence['converging']}")

    # Test 3: Market cycle simulation
    print("\n--- Test 3: Market Cycle Simulation ---")

    initial_state = FinancialEncoder.encode_market_state(
        price_change=0.01,
        volume=0.5,
        volatility=0.18,
        inflation=0.02,
        interest_rate=0.04,
        unemployment=0.05
    )

    simulator = MarketCycleSimulator()
    result = simulator.simulate_cycle(
        initial_state,
        quarters=80,  # 20 years
        shock_quarters=[25, 55]  # Two shocks
    )

    print(f"Simulation: {result['quarters_simulated']} quarters")
    print(f"  Average ∅_fin: {result['avg_null']:.2%}")
    print(f"  ∅ variance: {result['null_variance']:.4f}")
    print(f"  Crisis events: {result['crisis_count']}")

    if result['crisis_events']:
        print(f"\n  Crisis timeline:")
        for quarter, indicators in result['crisis_events'][:5]:  # Show first 5
            print(f"    Q{quarter}: {len(indicators)} indicators triggered")

    print("\n" + "="*70)
    print("✓ Financial suite integration complete")
    print("="*70)

if __name__ == "__main__":
    demo()
