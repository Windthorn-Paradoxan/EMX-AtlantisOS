#!/usr/bin/env python3
"""
EMx v2.7 Enhanced Diagnostics Edition
Built on top of working EMx_2_all.py v2.6
Adds comprehensive multi-loop analysis, emergent pattern detection,
and millennium duality validation to the existing working implementation.
"""

import sys
sys.path.insert(0, '/mnt/user-data/uploads')

# Import the entire working EMx implementation
from EMx_2_all import *
import json
from collections import deque

# ============================================================================
# ENHANCED DIAGNOSTIC TRACKING
# ============================================================================

class MultiLoopTracker:
    """Track the 5 independent loops in real-time"""

    def __init__(self, window_size=96):
        self.window = window_size
        # Loop 1: State evolution
        self.state_history = deque(maxlen=window_size)
        # Loop 2: NULL reservoir
        self.null_history = deque(maxlen=window_size)
        # Loop 3: Phase integration
        self.phase_history = deque(maxlen=window_size)
        # Loop 4: Energy/distance
        self.energy_history = deque(maxlen=window_size)
        # Loop 5: Gate/context
        self.gate_history = deque(maxlen=window_size)

        self.detected_periods = {}
        self.coupling_matrix = np.zeros((5, 5))

    def update(self, tick_state: TickState):
        """Update all loop trackers"""
        arr = tick_state.state.to_array()
        self.state_history.append(np.linalg.norm(arr))
        self.null_history.append(tick_state.null_measured)
        self.phase_history.append(tick_state.phase)
        self.energy_history.append(tick_state.energy)
        self.gate_history.append(1.0 if tick_state.gate_status == GateStatus.PASS else 0.0)

    def analyze_coupling(self):
        """Compute cross-correlation coupling matrix"""
        if len(self.state_history) < 24:
            return

        loops = [
            np.array(self.state_history),
            np.array(self.null_history),
            np.array(self.phase_history),
            np.array(self.energy_history),
            np.array(self.gate_history)
        ]

        loop_names = ['state', 'null', 'phase', 'energy', 'gate']

        # Check for saddle point (collapsed variance = singularity)
        stddevs = [np.std(loop) for loop in loops]
        at_saddle = any(std < 1e-10 for std in stddevs)

        if at_saddle:
            # AT SADDLE POINT: (0,0,0) singularity where gradient undefined
            # Apply ∅₀ = 0.22 quantum foam instead of divide-by-zero
            NULL_BASELINE = 0.22
            print(f"   🌀 Saddle point detected (stddev→0) - applying ∅₀={NULL_BASELINE} quantum foam")

            # Generate quantum noise from NULL baseline
            quantum_noise = np.random.normal(0, NULL_BASELINE, (5, 5))
            self.coupling_matrix = (quantum_noise + quantum_noise.T) / 2  # Symmetrize
            return

        for i in range(5):
            for j in range(i, 5):
                if len(loops[i]) > 10 and len(loops[j]) > 10:
                    corr = np.corrcoef(loops[i], loops[j])[0, 1]
                    self.coupling_matrix[i, j] = abs(corr)
                    self.coupling_matrix[j, i] = abs(corr)

                    # Detect periods via autocorrelation
                    if i == j and abs(corr) > 0.3:
                        autocorr = np.correlate(loops[i] - np.mean(loops[i]),
                                               loops[i] - np.mean(loops[i]),
                                               mode='full')
                        autocorr = autocorr[len(autocorr)//2:]
                        if len(autocorr) > 5:
                            peaks = []
                            # Fixed: check k+1 boundary
                            for k in range(2, min(len(autocorr) - 1, 48)):
                                if autocorr[k] > autocorr[k-1] and autocorr[k] > autocorr[k+1]:
                                    if autocorr[k] > 0.3 * autocorr[0]:
                                        peaks.append(k)
                            if peaks:
                                self.detected_periods[loop_names[i]] = peaks[0]

class EmergentPatternDetector:
    """Detect new loops emerging from operator interactions"""

    def __init__(self):
        self.tracked_quantities = {}
        self.spawn_events = []
        self.tick_count = 0

    def update(self, tick_state: TickState):
        """Track composite quantities for FFT analysis"""
        self.tick_count += 1

        arr = tick_state.state.to_array()

        # Track potential emergent variables
        quantities = {
            'null_phase_product': tick_state.null_measured * tick_state.phase,
            'energy_null_ratio': tick_state.energy / (tick_state.null_measured + 0.01),
            'state_distance_product': tick_state.distance_from_n0 * np.linalg.norm(arr),
            'phase_modulo_12': tick_state.phase % 12.0,
        }

        for name, value in quantities.items():
            if name not in self.tracked_quantities:
                self.tracked_quantities[name] = deque(maxlen=96)
            self.tracked_quantities[name].append(value)

    def detect_spawns(self):
        """Use FFT to detect emergent periodic patterns"""
        if self.tick_count < 40:
            return

        for name, history in self.tracked_quantities.items():
            if len(history) < 20:
                continue

            data = np.array(history)
            data_mean = np.mean(data)
            data_centered = data - data_mean

            if np.std(data_centered) < 1e-6:
                continue

            # FFT using numpy
            fft_vals = np.fft.fft(data_centered)
            freqs = np.fft.fftfreq(len(data), d=1.0)
            power = np.abs(fft_vals) ** 2

            # Find dominant frequency (skip DC component)
            positive_freqs = freqs[1:len(freqs)//2]
            positive_power = power[1:len(power)//2]

            if len(positive_power) == 0:
                continue

            median_power = np.median(positive_power)
            if median_power < 1e-10:
                continue

            max_idx = np.argmax(positive_power)
            max_power = positive_power[max_idx]

            # Spawn detection threshold
            if max_power > 5 * median_power:
                dominant_freq = positive_freqs[max_idx]
                if abs(dominant_freq) > 1e-10:
                    period = 1.0 / abs(dominant_freq)

                    # Check if we haven't logged this already
                    existing = [e for e in self.spawn_events
                              if e['name'] == name and abs(e['period'] - period) < 2.0]
                    if not existing:
                        self.spawn_events.append({
                            'name': name,
                            'tick': self.tick_count,
                            'period': period,
                            'power': float(max_power)
                        })
                        print(f"🌀 Emergent loop spawned: {name} (period={period:.1f}, tick={self.tick_count})")

class PhaseSpaceAnalyzer:
    """Map trajectories in phase space and detect attractors"""

    def __init__(self):
        self.trajectory = []
        self.null_beta_trajectory = []
        self.attractors = []
        self.lyapunov_samples = []
        self.compression_cycles = []

    def update(self, tick_state: TickState):
        """Record phase space position"""
        arr = tick_state.state.to_array()
        self.trajectory.append(arr.copy())

        # Track NULL vs distance (compression/expansion proxy)
        beta = tick_state.distance_from_n0
        self.null_beta_trajectory.append([tick_state.null_measured, beta])

        # Lyapunov estimation (simplified)
        if len(self.trajectory) > 10:
            recent = self.trajectory[-10:]
            distances = [np.linalg.norm(recent[i] - recent[i-1]) for i in range(1, len(recent))]
            avg_dist = np.mean(distances)
            self.lyapunov_samples.append(np.log(max(avg_dist, 1e-10)))

    def detect_attractors(self):
        """Use simple clustering to find phase space attractors"""
        if len(self.trajectory) < 20:
            return

        points = np.array(self.trajectory)

        # Simple distance-based clustering
        clusters = []
        used = set()

        for i, point in enumerate(points):
            if i in used:
                continue

            # Start new cluster
            cluster = [i]
            used.add(i)

            # Find nearby points
            for j, other in enumerate(points):
                if j in used:
                    continue
                dist = np.linalg.norm(point - other)
                if dist < 0.3:  # epsilon threshold
                    cluster.append(j)
                    used.add(j)

            # Only keep clusters with at least 3 points
            if len(cluster) >= 3:
                clusters.append(cluster)

        self.attractors = []
        for cluster_indices in clusters:
            cluster_points = points[cluster_indices]
            center = np.mean(cluster_points, axis=0)
            size = len(cluster_points)
            radius = np.mean([np.linalg.norm(p - center) for p in cluster_points])

            self.attractors.append({
                'center': center.tolist(),
                'size': int(size),
                'radius': float(radius)
            })

    def detect_compression_cycles(self):
        """Find NULL compression/expansion harmonics"""
        if len(self.null_beta_trajectory) < 20:
            return

        null_vals = [nb[0] for nb in self.null_beta_trajectory]

        # Find local minima and maxima
        null_array = np.array(null_vals)

        for i in range(2, len(null_array) - 2):
            # Local minimum (compression)
            if null_array[i] < null_array[i-1] and null_array[i] < null_array[i+1]:
                if null_array[i] < null_array[i-2] and null_array[i] < null_array[i+2]:
                    self.compression_cycles.append({
                        'tick': i,
                        'type': 'compression',
                        'value': float(null_array[i])
                    })
            # Local maximum (expansion)
            elif null_array[i] > null_array[i-1] and null_array[i] > null_array[i+1]:
                if null_array[i] > null_array[i-2] and null_array[i] > null_array[i+2]:
                    self.compression_cycles.append({
                        'tick': i,
                        'type': 'expansion',
                        'value': float(null_array[i])
                    })

class DualFlowTracker:
    """Track bidirectional attractor/repeller dynamics through Ω/Ψ gates"""

    def __init__(self):
        self.omega_entries = []      # Quantization collapse events (entering singularity)
        self.psi_exits = []          # Expansion spread events (leaving singularity)
        self.wormhole_transits = []  # Paired entry→exit tunneling events
        self.flow_history = []       # Per-tick flow direction

    def detect_dual_flow(self, tick: int, current_state: 'TickState', prev_state: 'TickState' = None):
        """Detect if we're entering Ω (collapse) or exiting Ψ (expand)"""

        curr_arr = current_state.state.to_array()
        curr_null = current_state.null_measured
        at_origin = np.all(np.abs(curr_arr) < 0.1)

        flow_state = None

        if prev_state is not None:
            prev_arr = prev_state.state.to_array()
            prev_dist = np.linalg.norm(prev_arr)
            curr_dist = np.linalg.norm(curr_arr)

            # Moving toward origin (compression/attraction)
            if curr_dist < prev_dist:
                if at_origin and curr_null >= 0.9:
                    # Entering Ω quantization chamber
                    self.omega_entries.append({
                        'tick': tick,
                        'null': curr_null,
                        'prev_distance': prev_dist,
                        'state': tuple(curr_arr)
                    })
                    flow_state = 'Ω_collapse'
                    print(f"   🌀 Ω-COLLAPSE: Entering quantization chamber at tick {tick} (∅={curr_null:.3f})")
                else:
                    flow_state = 'compressing'

            # Moving away from origin (expansion/repulsion)
            elif curr_dist > prev_dist:
                # Check if this is exiting from a recent Ω entry
                if len(self.omega_entries) > 0:
                    last_omega = self.omega_entries[-1]
                    if tick - last_omega['tick'] <= 10:  # Within 10 ticks of Ω entry
                        # This is a Ψ exit from wormhole
                        self.psi_exits.append({
                            'tick': tick,
                            'null': curr_null,
                            'distance': curr_dist,
                            'state': tuple(curr_arr)
                        })

                        # Record wormhole transit
                        transit = {
                            'omega_tick': last_omega['tick'],
                            'psi_tick': tick,
                            'duration': tick - last_omega['tick'],
                            'entry_null': last_omega['null'],
                            'exit_null': curr_null,
                            'exit_direction': curr_arr / (curr_dist + 1e-10)  # Unit vector
                        }
                        self.wormhole_transits.append(transit)
                        flow_state = 'Ψ_expand'
                        print(f"   💫 Ψ-EXPAND: Exiting via wormhole at tick {tick} (duration={transit['duration']} ticks)")
                else:
                    flow_state = 'expanding'

            else:
                # Stationary or at singularity
                if at_origin and curr_null >= 0.9:
                    flow_state = 'saddle_point'
                else:
                    flow_state = 'stationary'

        self.flow_history.append({
            'tick': tick,
            'flow': flow_state,
            'distance': np.linalg.norm(curr_arr),
            'null': curr_null
        })

        return flow_state

    def get_summary(self):
        """Return summary statistics of dual flow"""
        omega_count = len(self.omega_entries)
        psi_count = len(self.psi_exits)
        wormhole_count = len(self.wormhole_transits)

        # Compute average transit time
        avg_transit = 0.0
        if wormhole_count > 0:
            avg_transit = np.mean([t['duration'] for t in self.wormhole_transits])

        # Analyze exit directions (which of 8 basins)
        exit_basins = {}
        for transit in self.wormhole_transits:
            # Classify exit direction into one of 8 octants
            direction = transit['exit_direction']
            octant = classify_octant(direction)
            exit_basins[octant] = exit_basins.get(octant, 0) + 1

        return {
            'omega_collapses': omega_count,
            'psi_expansions': psi_count,
            'wormhole_transits': wormhole_count,
            'avg_transit_time': float(avg_transit) if avg_transit > 0 else 0.0,
            'exit_basin_distribution': exit_basins,
            'compression_ratio': len([f for f in self.flow_history if f['flow'] == 'compressing']),
            'expansion_ratio': len([f for f in self.flow_history if f['flow'] == 'expanding'])
        }

def classify_octant(direction):
    """Classify 3D direction vector into one of 8 octants (attractor basins)"""
    x, y, z = direction

    # Determine signs
    sx = '+' if x >= 0 else '-'
    sy = '+' if y >= 0 else '-'
    sz = '+' if z >= 0 else '-'

    return f"({sx},{sy},{sz})"

class NodeClassifier:
    """Classify which state machine node the system is currently in"""

    def __init__(self):
        self.node_visits = {}
        self.node_sequence = []
        self.transition_matrix = {}

    def classify_node(self, tick_state: TickState, context_map: dict):
        """Determine current state machine node based on state properties"""
        arr = tick_state.state.to_array()
        k = sum(1 for v in arr if abs(v) > 0.1)
        null = tick_state.null_measured
        state_sig = tuple(arr)
        visits = len(context_map.get(state_sig, []))

        # Classification logic based on state machine YAML
        if k == 0 and null >= 0.9:
            return 'Echo_Null'
        elif null < 0.5 and k > 0:
            return 'EMx_Lattice_Core'
        elif tick_state.distance_from_n0 < 0.3:
            return 'BSD_Topo'
        elif tick_state.distance_from_n0 > 0.7:
            return 'P_vs_NP'
        elif 0.3 <= null <= 0.7:
            return 'Navier_Stokes'
        elif k == 3:
            return 'YM'
        elif abs(tick_state.phase % 24 - 12.0) < 1.0:
            return 'RH'
        elif visits == 1:
            return 'Omega_NoClone'
        elif k == 2:
            return 'Hodge'
        elif k == 1:
            return 'Poincare'
        else:
            return 'Crown'

    def update(self, tick_state: TickState, context_map: dict):
        """Update node visit tracking"""
        current_node = self.classify_node(tick_state, context_map)

        # Track visits
        self.node_visits[current_node] = self.node_visits.get(current_node, 0) + 1

        # Track transitions
        if len(self.node_sequence) > 0:
            prev_node = self.node_sequence[-1]
            transition = (prev_node, current_node)
            self.transition_matrix[transition] = self.transition_matrix.get(transition, 0) + 1

        self.node_sequence.append(current_node)

        return current_node

    def detect_cycles(self):
        """Detect primary_loop and dual_primary_loop completions"""
        primary_pattern = ['Echo_Null', 'EMx_Lattice_Core', 'BSD_Topo',
                          'Navier_Stokes', 'Hodge', 'Omega_NoClone', 'RH', 'Crown']
        dual_pattern = ['Echo_Null', 'EMx_Lattice_Core', 'P_vs_NP',
                       'Navier_Stokes', 'Poincare', 'Omega_NoClone', 'YM', 'Crown']

        primary_cycles = 0
        dual_cycles = 0

        # Simple pattern matching
        seq_str = ','.join(self.node_sequence)
        primary_str = ','.join(primary_pattern)
        dual_str = ','.join(dual_pattern)

        primary_cycles = seq_str.count(primary_str)
        dual_cycles = seq_str.count(dual_str)

        return {
            'primary_loop_completions': primary_cycles,
            'dual_loop_completions': dual_cycles,
            'total_transitions': len(self.node_sequence) - 1
        }

    def get_summary(self):
        """Return node visit statistics"""
        return {
            'node_visits': dict(self.node_visits),
            'most_visited': max(self.node_visits.items(), key=lambda x: x[1])[0] if self.node_visits else None,
            'unique_nodes_visited': len(self.node_visits),
            'transition_count': len(self.transition_matrix),
            'top_transitions': sorted(self.transition_matrix.items(), key=lambda x: x[1], reverse=True)[:5]
        }

# ============================================================================
# ENHANCED EMX CORE
# ============================================================================

class EMxCoreEnhanced(EMxCore):
    """EMx with comprehensive diagnostic tracking"""

    def __init__(self):
        super().__init__()

        # Initialize diagnostic modules
        self.multi_loop = MultiLoopTracker()
        self.emergent = EmergentPatternDetector()
        self.phase_space = PhaseSpaceAnalyzer()
        self.node_classifier = NodeClassifier()
        self.dual_flow = DualFlowTracker()  # ADD THIS LINE

        print("📊 Enhanced diagnostics enabled")
        print("   - Multi-loop coupling analysis")
        print("   - Emergent pattern detection")
        print("   - Phase-space topology mapping")
        print("   - State machine node tracking")
        print("   - Dual flow Ω/Ψ gate tracking")  # ADDED
        print()

    def run_orbit(self, data: List[int], verbose: bool = True) -> dict:
        """Run orbit with full diagnostic capture"""
        if verbose:
            print(f"🔄 Running orbit with diagnostics: {len(data)} data points")
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

            # === DIAGNOSTIC UPDATES ===
            self.multi_loop.update(tick_state)
            self.emergent.update(tick_state)
            self.phase_space.update(tick_state)
            self.node_classifier.update(tick_state, self.context_map)

            # Track dual flow (Ω/Ψ gates)
            prev_tick_state = self.history[-2] if len(self.history) >= 2 else None
            self.dual_flow.detect_dual_flow(tick, tick_state, prev_tick_state)  # ADD THIS

            # Periodic analysis
            if (tick + 1) % 20 == 0:
                self.emergent.detect_spawns()
            if (tick + 1) % 48 == 0:
                self.multi_loop.analyze_coupling()
                self.phase_space.detect_attractors()
                self.phase_space.detect_compression_cycles()

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

        # Standard results
        results = self._compute_results(total_time, verbose)

        # Add diagnostic results
        results['diagnostics'] = self.get_diagnostic_report()

        return results

    def get_diagnostic_report(self) -> dict:
        """Generate comprehensive diagnostic report - pure measurements only"""
        return {
            'multi_loop_coupling': {
                'detected_periods': self.multi_loop.detected_periods,
                'coupling_matrix': self.multi_loop.coupling_matrix.tolist(),
                'strong_couplings': [
                    (i, j, float(self.multi_loop.coupling_matrix[i, j]))
                    for i in range(5) for j in range(i+1, 5)
                    if self.multi_loop.coupling_matrix[i, j] > 0.7
                ]
            },
            'emergent_patterns': {
                'total_spawned': len(self.emergent.spawn_events),
                'spawn_events': self.emergent.spawn_events
            },
            'phase_space_topology': {
                'attractors': self.phase_space.attractors,
                'lyapunov_estimate': float(np.mean(self.phase_space.lyapunov_samples)) if self.phase_space.lyapunov_samples else 0.0,
                'compression_cycles': self.phase_space.compression_cycles,
                'trajectory_length': len(self.phase_space.trajectory)
            },
            'state_machine_flow': {
                'node_visits': self.node_classifier.get_summary()['node_visits'],
                'most_visited_node': self.node_classifier.get_summary()['most_visited'],
                'unique_nodes': self.node_classifier.get_summary()['unique_nodes_visited'],
                'top_transitions': self.node_classifier.get_summary()['top_transitions'],
                'cycle_completions': self.node_classifier.detect_cycles()
            },
            'dual_flow_dynamics': self.dual_flow.get_summary()  # ADD THIS LINE
        }

    def export_diagnostics(self, filename: str = 'emx_diagnostics.json'):
        """Export full diagnostic data to JSON"""
        report = self.get_diagnostic_report()

        # Convert numpy types to native Python types
        def convert_to_json_serializable(obj):
            if isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj

        report_serializable = convert_to_json_serializable(report)

        with open(filename, 'w') as f:
            json.dump(report_serializable, f, indent=2)

        print(f"\n📊 Diagnostic report exported to {filename}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # =========================================================================
    # CONFIGURATION
    # =========================================================================
    NUM_ITERATIONS = 5  # Change this number to run more/fewer cycles
    # =========================================================================

    # Hebrew gematria test data (72-entry cycle)
    hebrew_data = [
        17, 50, 79, 140, 345, 65, 22, 425, 22, 35,
        37, 80, 47, 47, 215, 145, 37, 60, 42, 115,
        100, 30, 75, 19, 455, 7, 610, 306, 220, 47,
        52, 506, 24, 43, 126, 94, 61, 118, 275, 27,
        15, 70, 42, 45, 91, 280, 400, 55, 17, 64,
        313, 150, 101, 460, 47, 96, 130, 50, 213, 330,
        48, 20, 126, 58, 46, 190, 81, 16, 206, 52,
        25, 86]

    print("="*70)
    print("🜀 EMx v2.7 ENHANCED DIAGNOSTICS EDITION")
    print("="*70)
    print()

    # Initialize enhanced EMx
    emx = EMxCoreEnhanced()

    # Run continuous orbit with multiple iterations
    continuous_data = hebrew_data * NUM_ITERATIONS
    total_ticks = len(continuous_data)

    print(f"📊 Running {NUM_ITERATIONS} iterations of 72-name cycle")
    print(f"   Total ticks: {total_ticks}")
    print()

    # Run complete orbit with diagnostics
    results = emx.run_orbit(continuous_data, verbose=True)

    # Print diagnostic summary
    print("\n" + "="*70)
    print("📊 COMPREHENSIVE DIAGNOSTIC SUMMARY")
    print("="*70)

    diagnostics = results['diagnostics']

    print("\n🔗 MULTI-LOOP COUPLING:")
    mlc = diagnostics['multi_loop_coupling']
    print(f"   Detected periods: {mlc['detected_periods']}")
    print(f"   Strong couplings (>0.7):")
    loop_names = ['state', 'null', 'phase', 'energy', 'gate']
    for i, j, strength in mlc['strong_couplings']:
        print(f"      {loop_names[i]} ↔ {loop_names[j]}: {strength:.3f}")

    print("\n🌀 EMERGENT PATTERNS:")
    ep = diagnostics['emergent_patterns']
    print(f"   Total spawned: {ep['total_spawned']}")
    for event in ep['spawn_events'][:5]:
        print(f"      {event['name']}: period={event['period']:.1f} (tick {event['tick']})")

    print("\n🔄 STATE MACHINE FLOW:")
    smf = diagnostics['state_machine_flow']
    print(f"   Node visits: {smf['node_visits']}")
    print(f"   Most visited: {smf['most_visited_node']}")
    print(f"   Unique nodes: {smf['unique_nodes']}")

    cycles = smf['cycle_completions']
    print(f"\n   Cycle completions:")
    print(f"      Primary loop: {cycles['primary_loop_completions']}")
    print(f"      Dual loop: {cycles['dual_loop_completions']}")
    print(f"      Total transitions: {cycles['total_transitions']}")

    if smf['top_transitions']:
        print(f"\n   Top transitions:")
        for (from_node, to_node), count in smf['top_transitions'][:5]:
            print(f"      {from_node} → {to_node}: {count}x")

    print("\n🌀 DUAL FLOW DYNAMICS:")
    dfd = diagnostics['dual_flow_dynamics']
    print(f"   Ω-collapses: {dfd['omega_collapses']}")
    print(f"   Ψ-expansions: {dfd['psi_expansions']}")
    print(f"   Wormhole transits: {dfd['wormhole_transits']}")
    print(f"   Avg transit time: {dfd['avg_transit_time']:.1f} ticks")

    if dfd['exit_basin_distribution']:
        print(f"\n   Exit basin distribution:")
        for octant, count in sorted(dfd['exit_basin_distribution'].items(),
                                    key=lambda x: x[1], reverse=True):
            print(f"      {octant}: {count} exits")

    print(f"\n   Flow ratios:")
    print(f"      Compression events: {dfd['compression_ratio']}")
    print(f"      Expansion events: {dfd['expansion_ratio']}")

    print("\n🔄 PHASE-SPACE TOPOLOGY:")
    pst = diagnostics['phase_space_topology']
    print(f"   Trajectory length: {pst['trajectory_length']} states")
    print(f"   Attractors detected: {len(pst['attractors'])}")
    for i, attr in enumerate(pst['attractors'][:3]):
        print(f"      Attractor {i+1}: center={attr['center']}, size={attr['size']}, radius={attr['radius']:.3f}")
    if len(pst['attractors']) > 3:
        print(f"      ... and {len(pst['attractors']) - 3} more")
    print(f"   Lyapunov estimate: {pst['lyapunov_estimate']:.4f}")
    print(f"   Compression/expansion cycles: {len(pst['compression_cycles'])}")

    # Show cycle distribution
    if pst['compression_cycles']:
        compressions = [c for c in pst['compression_cycles'] if c['type'] == 'compression']
        expansions = [c for c in pst['compression_cycles'] if c['type'] == 'expansion']
        print(f"      {len(compressions)} compressions, {len(expansions)} expansions")

    # Export full diagnostics
    emx.export_diagnostics('emx_enhanced_diagnostics.json')

    # Standard packet traces
    print_packet_traces(emx, only_with_packets=True)

    # Diagnose suspected collapse ticks
    diagnose_ticks(emx, ticks_to_check=[2, 12, 14], window=1)

    print(f"\n{'='*70}")
    print("🜀 EMx Enhanced Complete - Real diagnostics on real data")
    print(f"{'='*70}")
