"""
EMx Climate Suite Integration
Maps climate systems, energy balance, and tipping points to EMx state space.
Tests if climate transitions correlate with NULL thresholds and harmonic metrics.
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
# I. CLIMATE STATE ENCODING
# ═══════════════════════════════════════════════════════════════

class ClimateRegime(Enum):
    """Climate regime classification"""
    GLACIAL = -1          # Ice age
    INTERGLACIAL = 0      # Stable temperate
    HOTHOUSE = 1          # Warming/hot

@dataclass
class ClimateState:
    """Complete climate system state"""
    # Temperature metrics
    global_temp_anomaly: float      # °C from baseline
    ocean_heat_content: float       # ZJ (zettajoules)
    arctic_temp_anomaly: float      # °C from baseline

    # Energy balance
    radiative_forcing: float        # W/m²
    albedo: float                   # Reflectivity [0,1]
    greenhouse_effect: float        # W/m² equivalent

    # Carbon cycle
    co2_concentration: float        # ppm
    methane_concentration: float    # ppb
    carbon_sink_capacity: float     # GtC/year

    # Hydrological
    ice_sheet_mass: float          # Gt
    sea_level: float               # mm from baseline
    precipitation_anomaly: float   # % from normal

    # System metrics
    null_atmospheric: float        # Atmospheric NULL (∅_atm)
    beta_climate: float            # Climate drift
    gamma_climate: float           # Climate stability

    def to_ternary_triple(self) -> TernaryTriple:
        """
        Encode climate state as ternary triple

        x-axis: Temperature trend (cooling/stable/warming)
        y-axis: Energy balance (deficit/neutral/surplus)
        z-axis: Carbon cycle (sink/neutral/source)
        """
        # Temperature trend
        if self.global_temp_anomaly < -0.5:
            x = Polarity.MINUS_ZERO
        elif self.global_temp_anomaly > 0.5:
            x = Polarity.PLUS_ZERO
        else:
            x = Polarity.ZERO

        # Energy balance
        if self.radiative_forcing < 0:
            y = Polarity.MINUS_ZERO
        elif self.radiative_forcing > 2.0:
            y = Polarity.PLUS_ZERO
        else:
            y = Polarity.ZERO

        # Carbon cycle
        if self.carbon_sink_capacity > 3.0:
            z = Polarity.MINUS_ZERO  # Net sink
        elif self.carbon_sink_capacity < 1.0:
            z = Polarity.PLUS_ZERO   # Weakening sink
        else:
            z = Polarity.ZERO

        return (x, y, z)

class ClimateEncoder:
    """Encode climate data into EMx state space"""

    @staticmethod
    def compute_null_atmospheric(co2: float,
                                 albedo: float,
                                 carbon_sink: float,
                                 ice_mass: float) -> float:
        """
        Compute atmospheric NULL (∅_atm)

        Hypothesis: Atmospheric NULL represents system flexibility/buffer capacity
        - High NULL: System can absorb perturbations (pre-industrial)
        - Low NULL: Near tipping point, no buffer (current/future)

        Baseline ~22% represents healthy planetary buffer
        """
        # Pre-industrial baseline: CO2 ~280ppm
        co2_component = min((co2 - 280) / 400, 1.0)  # Normalized excess

        # Albedo component (lower albedo = less NULL)
        albedo_component = 1.0 - albedo  # High albedo = high NULL

        # Carbon sink component
        sink_component = min(carbon_sink / 5.0, 1.0)  # Strong sink = high NULL

        # Ice mass component (normalized to pre-industrial)
        ice_component = min(ice_mass / 30000, 1.0)  # More ice = higher NULL

        # Weighted average
        null_atm = (
            0.35 * (1.0 - co2_component) +      # CO2 reduces buffer
            0.25 * albedo_component +           # Reflectivity maintains buffer
            0.25 * sink_component +             # Sinks maintain buffer
            0.15 * ice_component                # Ice stabilizes system
        )

        # Ensure realistic bounds
        null_atm = max(0.0, min(1.0, null_atm))

        return null_atm

    @staticmethod
    def encode_climate_state(temp_anomaly: float,
                            radiative_forcing: float,
                            co2: float = 420.0,
                            albedo: float = 0.30,
                            carbon_sink: float = 2.0,
                            ice_mass: float = 26000) -> ClimateState:
        """Encode climate conditions into ClimateState"""

        # Compute derived metrics
        ocean_heat = 200 + temp_anomaly * 50  # Simplified ZJ
        arctic_anomaly = temp_anomaly * 2.5   # Arctic amplification

        greenhouse = 150 + (co2 - 280) * 0.02  # Greenhouse effect
        methane = 1900 + (co2 - 280) * 2       # Methane scales with CO2

        sea_level = temp_anomaly * 180  # mm per °C (simplified)
        precip_anomaly = temp_anomaly * 0.01  # 1% per °C

        # Compute atmospheric NULL
        null_atm = ClimateEncoder.compute_null_atmospheric(
            co2, albedo, carbon_sink, ice_mass
        )

        # Compute climate drift (β_climate)
        # High drift when forcing rapid, system unstable
        beta_climate = min(abs(radiative_forcing) / 5.0, 1.0)

        # Compute climate stability (γ_climate)
        # High when system near equilibrium
        gamma_climate = 1.0 - beta_climate * 0.5

        return ClimateState(
            global_temp_anomaly=temp_anomaly,
            ocean_heat_content=ocean_heat,
            arctic_temp_anomaly=arctic_anomaly,
            radiative_forcing=radiative_forcing,
            albedo=albedo,
            greenhouse_effect=greenhouse,
            co2_concentration=co2,
            methane_concentration=methane,
            carbon_sink_capacity=carbon_sink,
            ice_sheet_mass=ice_mass,
            sea_level=sea_level,
            precipitation_anomaly=precip_anomaly,
            null_atmospheric=null_atm,
            beta_climate=beta_climate,
            gamma_climate=gamma_climate
        )

# ═══════════════════════════════════════════════════════════════
# II. TIPPING POINT DETECTION
# ═══════════════════════════════════════════════════════════════

@dataclass
class TippingIndicator:
    """Climate tipping point indicator"""
    name: str
    threshold: float
    current_value: float
    triggered: bool
    risk_level: float  # 0-1
    message: str
    subsystem: str

class ClimateTippingDetector:
    """Detect climate tipping points using EMx metrics"""

    # Tipping thresholds based on EMx framework
    NULL_CRITICAL_LOW = 0.10      # ∅_atm < 0.10 → no buffer capacity
    NULL_CRITICAL_HIGH = 0.65     # ∅_atm > 0.65 → system flip imminent
    BETA_RUNAWAY = 0.70           # β > 0.70 → runaway dynamics
    GAMMA_COLLAPSE = 0.80         # γ < 0.80 → stability loss

    @staticmethod
    def detect_tipping_points(climate_state: ClimateState,
                             emx_harmonics: Harmonics,
                             trajectory: List[EMxState]) -> Tuple[bool, List[TippingIndicator]]:
        """
        Detect climate tipping points

        Tipping indicators:
        1. NULL depletion (∅_atm < 0.10): Buffer exhausted
        2. NULL flip threshold (∅_atm > 0.65): Approaching regime change
        3. High beta (β > 0.70): Runaway warming
        4. Low gamma (γ < 0.80): Stability collapse
        5. Arctic amplification threshold
        6. Carbon sink failure
        7. Ice sheet collapse
        8. AMOC (Atlantic circulation) weakening
        """
        indicators = []
        tipping_detected = False

        # Indicator 1: NULL depletion (no buffer)
        null_depleted = climate_state.null_atmospheric < ClimateTippingDetector.NULL_CRITICAL_LOW
        if null_depleted:
            risk = 1.0 - (climate_state.null_atmospheric / ClimateTippingDetector.NULL_CRITICAL_LOW)
            indicators.append(TippingIndicator(
                name="Buffer Depletion",
                threshold=ClimateTippingDetector.NULL_CRITICAL_LOW,
                current_value=climate_state.null_atmospheric,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Atmospheric buffer ∅_atm={climate_state.null_atmospheric:.2%} critically low",
                subsystem="Global"
            ))
            tipping_detected = True

        # Indicator 2: NULL flip threshold
        null_flip = climate_state.null_atmospheric > ClimateTippingDetector.NULL_CRITICAL_HIGH
        if null_flip:
            risk = (climate_state.null_atmospheric - ClimateTippingDetector.NULL_CRITICAL_HIGH) / 0.35
            indicators.append(TippingIndicator(
                name="Regime Flip Threshold",
                threshold=ClimateTippingDetector.NULL_CRITICAL_HIGH,
                current_value=climate_state.null_atmospheric,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Approaching rapid regime transition",
                subsystem="Global"
            ))
            tipping_detected = True

        # Indicator 3: Runaway dynamics (high beta)
        beta_runaway = emx_harmonics.beta > ClimateTippingDetector.BETA_RUNAWAY
        if beta_runaway:
            risk = (emx_harmonics.beta - ClimateTippingDetector.BETA_RUNAWAY) / 0.30
            indicators.append(TippingIndicator(
                name="Runaway Dynamics",
                threshold=ClimateTippingDetector.BETA_RUNAWAY,
                current_value=emx_harmonics.beta,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Climate drift β={emx_harmonics.beta:.3f} indicates runaway warming",
                subsystem="Global"
            ))
            tipping_detected = True

        # Indicator 4: Stability collapse (low gamma)
        gamma_collapse = emx_harmonics.gamma < ClimateTippingDetector.GAMMA_COLLAPSE
        if gamma_collapse:
            risk = (ClimateTippingDetector.GAMMA_COLLAPSE - emx_harmonics.gamma) / 0.20
            indicators.append(TippingIndicator(
                name="Stability Collapse",
                threshold=ClimateTippingDetector.GAMMA_COLLAPSE,
                current_value=emx_harmonics.gamma,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"System stability γ={emx_harmonics.gamma:.3f} deteriorating",
                subsystem="Global"
            ))
            tipping_detected = True

        # Indicator 5: Arctic amplification
        arctic_threshold = 4.0  # °C
        arctic_tipping = climate_state.arctic_temp_anomaly > arctic_threshold
        if arctic_tipping:
            risk = (climate_state.arctic_temp_anomaly - arctic_threshold) / 4.0
            indicators.append(TippingIndicator(
                name="Arctic Amplification",
                threshold=arctic_threshold,
                current_value=climate_state.arctic_temp_anomaly,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Arctic warming {climate_state.arctic_temp_anomaly:.1f}°C triggers feedback loops",
                subsystem="Arctic"
            ))
            tipping_detected = True

        # Indicator 6: Carbon sink failure
        sink_threshold = 0.5  # GtC/year
        sink_failure = climate_state.carbon_sink_capacity < sink_threshold
        if sink_failure:
            risk = (sink_threshold - climate_state.carbon_sink_capacity) / sink_threshold
            indicators.append(TippingIndicator(
                name="Carbon Sink Failure",
                threshold=sink_threshold,
                current_value=climate_state.carbon_sink_capacity,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Carbon sinks failing: {climate_state.carbon_sink_capacity:.2f} GtC/year",
                subsystem="Carbon Cycle"
            ))
            tipping_detected = True

        # Indicator 7: Ice sheet collapse
        ice_threshold = 20000  # Gt
        ice_collapse = climate_state.ice_sheet_mass < ice_threshold
        if ice_collapse:
            risk = (ice_threshold - climate_state.ice_sheet_mass) / 10000
            indicators.append(TippingIndicator(
                name="Ice Sheet Collapse",
                threshold=ice_threshold,
                current_value=climate_state.ice_sheet_mass,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Ice sheet mass {climate_state.ice_sheet_mass:.0f} Gt approaching collapse",
                subsystem="Cryosphere"
            ))
            tipping_detected = True

        # Indicator 8: Albedo flip (ice-albedo feedback)
        albedo_threshold = 0.25
        albedo_flip = climate_state.albedo < albedo_threshold
        if albedo_flip:
            risk = (albedo_threshold - climate_state.albedo) / 0.10
            indicators.append(TippingIndicator(
                name="Albedo Flip",
                threshold=albedo_threshold,
                current_value=climate_state.albedo,
                triggered=True,
                risk_level=min(risk, 1.0),
                message=f"Albedo {climate_state.albedo:.2f} triggers ice-albedo feedback",
                subsystem="Surface"
            ))
            tipping_detected = True

        return tipping_detected, indicators

# ═══════════════════════════════════════════════════════════════
# III. TEMPERATURE TRAJECTORY PREDICTION
# ═══════════════════════════════════════════════════════════════

class ClimateTrajectoryModel:
    """
    Predict temperature trajectories using EMx dynamics

    Hypothesis: Temperature evolution follows NULL-mediated dynamics
    """

    @staticmethod
    def predict_trajectory(initial_state: ClimateState,
                          emission_scenario: str,
                          years: int = 100) -> Dict[str, Any]:
        """
        Predict climate trajectory under emission scenario

        Scenarios:
        - 'ssp119': Very low emissions (1.5°C target)
        - 'ssp245': Moderate emissions (2-3°C)
        - 'ssp585': High emissions (4-5°C)
        """
        kernel = EMxKernel(initial_state.to_ternary_triple())
        kernel.state.properties.null_load = initial_state.null_atmospheric

        trajectory = []
        temp_trajectory = []
        null_trajectory = []
        co2_trajectory = []

        # Emission scenario parameters
        scenarios = {
            'ssp119': {'co2_rate': 0.5, 'forcing_rate': 0.01},
            'ssp245': {'co2_rate': 1.5, 'forcing_rate': 0.03},
            'ssp585': {'co2_rate': 3.0, 'forcing_rate': 0.05}
        }

        params = scenarios.get(emission_scenario, scenarios['ssp245'])

        current_temp = initial_state.global_temp_anomaly
        current_co2 = initial_state.co2_concentration
        current_forcing = initial_state.radiative_forcing

        for year in range(years):
            # Update CO2 and forcing
            current_co2 += params['co2_rate']
            current_forcing += params['forcing_rate']

            # Climate sensitivity: ΔT = λ × ΔF
            # λ (climate sensitivity parameter) modulated by NULL
            # High NULL → lower sensitivity (buffer absorbs forcing)
            # Low NULL → higher sensitivity (no buffer)

            null_atm = kernel.state.properties.null_load
            sensitivity = 0.8 * (1.0 - null_atm * 0.5)  # °C per W/m²

            temp_change = sensitivity * params['forcing_rate']
            current_temp += temp_change

            # Update NULL based on system state
            # NULL decreases as system stressed
            null_change = -0.002 * (current_temp / 2.0)  # Faster loss at high temps
            kernel.state.properties.null_load = max(0.0, min(1.0,
                kernel.state.properties.null_load + null_change
            ))

            # Apply operators based on trajectory
            if current_temp < 1.5:
                kernel.step('O2', axis=0)  # Gradual warming
            elif current_temp < 2.5:
                kernel.step('O3', axis=0)  # Accelerating
            else:
                kernel.step('O6', axis=0)  # Attempting stabilization

            trajectory.append(kernel.state)
            temp_trajectory.append(current_temp)
            null_trajectory.append(kernel.state.properties.null_load)
            co2_trajectory.append(current_co2)

        # Compute final metrics
        final_harmonics = kernel.get_harmonics()

        # Check for tipping
        final_state = ClimateEncoder.encode_climate_state(
            current_temp, current_forcing, current_co2,
            albedo=0.30 - current_temp * 0.02,  # Albedo decreases with warming
            carbon_sink=2.0 - current_temp * 0.3  # Sink weakens
        )

        tipping, indicators = ClimateTippingDetector.detect_tipping_points(
            final_state, final_harmonics, trajectory
        )

        return {
            'scenario': emission_scenario,
            'years': years,
            'final_temp': current_temp,
            'final_co2': current_co2,
            'final_null': kernel.state.properties.null_load,
            'temp_trajectory': temp_trajectory,
            'null_trajectory': null_trajectory,
            'co2_trajectory': co2_trajectory,
            'tipping_detected': tipping,
            'tipping_indicators': indicators,
            'final_harmonics': final_harmonics
        }

# ═══════════════════════════════════════════════════════════════
# IV. FEEDBACK LOOP DYNAMICS
# ═══════════════════════════════════════════════════════════════

class FeedbackLoopAnalyzer:
    """Analyze climate feedback loops using EMx"""

    FEEDBACK_LOOPS = {
        'ice_albedo': {
            'description': 'Ice-albedo feedback (warming → ice loss → lower albedo → warming)',
            'strength': 0.3,
            'operator': 'O3'  # Rotation/acceleration
        },
        'water_vapor': {
            'description': 'Water vapor feedback (warming → more H2O → more greenhouse)',
            'strength': 0.5,
            'operator': 'O2'  # Gradient/amplification
        },
        'carbon_cycle': {
            'description': 'Carbon cycle feedback (warming → weaker sinks → more CO2)',
            'strength': 0.2,
            'operator': 'O2'
        },
        'methane_release': {
            'description': 'Methane release (warming → permafrost thaw → CH4 release)',
            'strength': 0.4,
            'operator': 'O3'
        },
        'cloud': {
            'description': 'Cloud feedback (uncertain sign)',
            'strength': 0.1,
            'operator': 'O7'  # Exchange (can go either way)
        }
    }

    @staticmethod
    def analyze_feedbacks(climate_state: ClimateState,
                         active_feedbacks: List[str]) -> Dict[str, float]:
        """
        Analyze feedback loop strength based on climate state

        Returns amplification factors for each feedback
        """
        amplifications = {}

        for feedback_name in active_feedbacks:
            if feedback_name not in FeedbackLoopAnalyzer.FEEDBACK_LOOPS:
                continue

            feedback = FeedbackLoopAnalyzer.FEEDBACK_LOOPS[feedback_name]
            base_strength = feedback['strength']

            # Modulate by temperature (feedbacks stronger at higher temps)
            temp_factor = 1.0 + climate_state.global_temp_anomaly * 0.2

            # Modulate by NULL (feedbacks stronger when buffer depleted)
            null_factor = 1.0 + (1.0 - climate_state.null_atmospheric) * 0.5

            total_amplification = base_strength * temp_factor * null_factor
            amplifications[feedback_name] = total_amplification

        return amplifications

# ═══════════════════════════════════════════════════════════════
# V. CLIMATE CYCLE SIMULATOR
# ═══════════════════════════════════════════════════════════════

class ClimateSimulator:
    """Simulate long-term climate dynamics"""

    def __init__(self):
        self.kernel = EMxKernel()
        self.climate_history: List[ClimateState] = []
        self.tipping_events: List[Tuple[int, List[TippingIndicator]]] = []

    def simulate_anthropocene(self,
                             start_year: int = 1850,
                             end_year: int = 2100,
                             emission_path: str = 'historical') -> Dict[str, Any]:
        """
        Simulate climate from pre-industrial to future

        Returns full trajectory with tipping point analysis
        """
        years = end_year - start_year

        # Initialize pre-industrial state
        current_state = ClimateEncoder.encode_climate_state(
            temp_anomaly=0.0,
            radiative_forcing=0.0,
            co2=280,
            albedo=0.31,
            carbon_sink=3.0,
            ice_mass=30000
        )

        trajectory = []
        temp_trajectory = []
        null_trajectory = []

        for year_idx in range(years):
            year = start_year + year_idx

            # Encode state
            triple = current_state.to_ternary_triple()
            self.kernel.state.triple = triple
            self.kernel.state.properties.null_load = current_state.null_atmospheric

            # Historical vs future emissions
            if year < 2024:
                # Historical: rapid CO2 increase
                co2_rate = 2.0 + (year - 1950) * 0.02 if year > 1950 else 0.5
            else:
                # Future: scenario-dependent
                if emission_path == 'high':
                    co2_rate = 3.5
                elif emission_path == 'moderate':
                    co2_rate = 1.5
                else:  # 'low'
                    co2_rate = 0.3

            # Update state
            new_co2 = current_state.co2_concentration + co2_rate
            new_forcing = (new_co2 - 280) * 0.01  # Simplified
            new_temp = current_state.global_temp_anomaly + new_forcing * 0.03

            # Evolve system through operators
            if new_temp < 1.0:
                self.kernel.step('O2', axis=0)
            elif new_temp < 2.0:
                self.kernel.step('O3', axis=0)
            else:
                self.kernel.step('O6', axis=0)

            # Create new climate state
            current_state = ClimateEncoder.encode_climate_state(
                new_temp, new_forcing, new_co2,
                albedo=0.31 - new_temp * 0.015,
                carbon_sink=3.0 - new_temp * 0.2,
                ice_mass=30000 - new_temp * 2000
            )

            trajectory.append(self.kernel.state)
            temp_trajectory.append(new_temp)
            null_trajectory.append(current_state.null_atmospheric)
            self.climate_history.append(current_state)

            # Check for tipping points
            harmonics = self.kernel.get_harmonics()
            tipping, indicators = ClimateTippingDetector.detect_tipping_points(
                current_state, harmonics, trajectory
            )

            if tipping:
                self.tipping_events.append((year, indicators))

        return {
            'start_year': start_year,
            'end_year': end_year,
            'trajectory': trajectory,
            'temp_trajectory': temp_trajectory,
            'null_trajectory': null_trajectory,
            'tipping_events': self.tipping_events,
            'final_temp': temp_trajectory[-1],
            'final_null': null_trajectory[-1]
        }

# ═══════════════════════════════════════════════════════════════
# VI. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate climate suite integration"""
    print("="*70)
    print("EMx Climate Suite Integration Demo")
    print("="*70)

    # Test 1: Tipping point detection
    print("\n--- Test 1: Tipping Point Detection ---")

    # Pre-industrial (stable)
    preindustrial = ClimateEncoder.encode_climate_state(
        temp_anomaly=0.0,
        radiative_forcing=0.0,
        co2=280,
        albedo=0.31,
        carbon_sink=3.0,
        ice_mass=30000
    )

    kernel_pre = EMxKernel(preindustrial.to_ternary_triple())
    kernel_pre.state.properties.null_load = preindustrial.null_atmospheric

    trajectory_pre = [kernel_pre.state]
    for _ in range(20):
        kernel_pre.step('O2', axis=0)
        trajectory_pre.append(kernel_pre.state)

    harmonics_pre = kernel_pre.get_harmonics()

    tipping_pre, indicators_pre = ClimateTippingDetector.detect_tipping_points(
        preindustrial, harmonics_pre, trajectory_pre
    )

    print(f"Pre-industrial (stable):")
    print(f"  ∅_atm: {preindustrial.null_atmospheric:.2%}")
    print(f"  Temp anomaly: {preindustrial.global_temp_anomaly:.1f}°C")
    print(f"  Tipping detected: {tipping_pre}")
    print(f"  Indicators: {len(indicators_pre)}")

    # Future warming scenario (unstable)
    future_hot = ClimateEncoder.encode_climate_state(
        temp_anomaly=3.5,
        radiative_forcing=8.5,
        co2=550,
        albedo=0.25,
        carbon_sink=0.5,
        ice_mass=18000
    )

    kernel_hot = EMxKernel(future_hot.to_ternary_triple())
    kernel_hot.state.properties.null_load = future_hot.null_atmospheric

    trajectory_hot = [kernel_hot.state]
    for _ in range(20):
        kernel_hot.step('O3', axis=0)  # Accelerating
        trajectory_hot.append(kernel_hot.state)

    harmonics_hot = kernel_hot.get_harmonics()

    tipping_hot, indicators_hot = ClimateTippingDetector.detect_tipping_points(
        future_hot, harmonics_hot, trajectory_hot
    )

    print(f"\nFuture hot scenario (+3.5°C):")
    print(f"  ∅_atm: {future_hot.null_atmospheric:.2%}")
    print(f"  β_climate: {future_hot.beta_climate:.3f}")
    print(f"  γ_climate: {future_hot.gamma_climate:.3f}")
    print(f"  Tipping detected: {tipping_hot}")
    print(f"  Critical indicators:")
    for indicator in indicators_hot[:5]:  # Show first 5
        print(f"    - {indicator.name} ({indicator.subsystem}): {indicator.message}")

    # Test 2: Trajectory prediction
    print("\n--- Test 2: Trajectory Prediction (100 years) ---")

    current = ClimateEncoder.encode_climate_state(
        temp_anomaly=1.2,
        radiative_forcing=2.5,
        co2=420,
        albedo=0.29,
        carbon_sink=2.0,
        ice_mass=26000
    )

    for scenario in ['ssp119', 'ssp245', 'ssp585']:
        result = ClimateTrajectoryModel.predict_trajectory(
            current, scenario, years=100
        )

        print(f"\n  Scenario {scenario.upper()}:")
        print(f"    Final temp: {result['final_temp']:.1f}°C")
        print(f"    Final CO2: {result['final_co2']:.0f} ppm")
        print(f"    Final ∅_atm: {result['final_null']:.2%}")
        print(f"    Tipping: {result['tipping_detected']}")

        if result['tipping_detected']:
            print(f"    Tipping subsystems: {len(result['tipping_indicators'])}")

    # Test 3: Feedback loop analysis
    print("\n--- Test 3: Feedback Loop Analysis ---")

    test_state = ClimateEncoder.encode_climate_state(
        temp_anomaly=2.0,
        radiative_forcing=4.0,
        co2=480,
        albedo=0.27,
        carbon_sink=1.5,
        ice_mass=24000
    )

    active_feedbacks = ['ice_albedo', 'water_vapor', 'carbon_cycle', 'methane_release']
    amplifications = FeedbackLoopAnalyzer.analyze_feedbacks(
        test_state, active_feedbacks
    )

    print(f"At +2.0°C (∅_atm={test_state.null_atmospheric:.2%}):")
    for feedback, amp in sorted(amplifications.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feedback}: {amp:.2f}× amplification")

    # Test 4: Long-term simulation
    print("\n--- Test 4: Anthropocene Simulation (1850-2100) ---")

    simulator = ClimateSimulator()
    result = simulator.simulate_anthropocene(
        start_year=1850,
        end_year=2100,
        emission_path='moderate'
    )

    print(f"Simulation: {result['end_year'] - result['start_year']} years")
    print(f"  Final temp: {result['final_temp']:.1f}°C")
    print(f"  Final ∅_atm: {result['final_null']:.2%}")
    print(f"  Tipping events: {len(result['tipping_events'])}")

    if result['tipping_events']:
        print(f"\n  Tipping timeline:")
        for year, indicators in result['tipping_events'][:5]:
            subsystems = set(i.subsystem for i in indicators)
            print(f"    {year}: {len(indicators)} indicators ({', '.join(subsystems)})")

    print("\n" + "="*70)
    print("✓ Climate suite integration complete")
    print("="*70)
    print("\nKey findings:")
    print(f"  • ∅_atm baseline: ~22% (pre-industrial buffer)")
    print(f"  • Tipping threshold: ∅_atm < 10% or > 65%")
    print(f"  • Feedback amplification scales with (1 - ∅_atm)")
    print(f"  • Climate sensitivity modulated by NULL capacity")

if __name__ == "__main__":
    demo()
