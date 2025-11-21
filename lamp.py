import time
import math
import random
from dataclasses import dataclass
from typing import List

@dataclass
class ToggleState:
    count: int
    null_load: float
    lamp_on: bool

class EMxLampParadox:
    def __init__(self):
        self.BASELINE_NULL = 0.22
        self.CAPACITY = 1 - self.BASELINE_NULL
        self.NULL_INJECTION_RATE = 0.015
        self.NULL_DECAY_RATE = 0.92

        self.toggle_count = 0
        self.null_load = self.BASELINE_NULL
        self.lamp_state = False
        self.collapsed = False
        self.history: List[ToggleState] = []

    def toggle(self):
        """Perform one toggle operation"""
        if self.collapsed:
            return False

        self.toggle_count += 1
        self.lamp_state = (self.toggle_count % 2 == 1)

        # EMx NULL accumulation
        injected = self.NULL_INJECTION_RATE * (1 + math.log(self.toggle_count + 1) / 10)
        decayed = self.null_load * self.NULL_DECAY_RATE
        noise = (random.random() - 0.5) * 0.01
        self.null_load = min(decayed + injected + noise, 1.0)

        # Check capacity
        if self.null_load > self.CAPACITY:
            self.collapsed = True
            return False

        # Record history
        self.history.append(ToggleState(
            count=self.toggle_count,
            null_load=self.null_load,
            lamp_on=self.lamp_state
        ))

        return True

    def get_status(self):
        """Return current system status"""
        if self.collapsed:
            status = "COLLAPSED"
        elif self.null_load < self.BASELINE_NULL:
            status = "Stable"
        elif self.null_load < 0.5:
            status = "Accumulating"
        elif self.null_load < self.CAPACITY:
            status = "Warning"
        else:
            status = "Critical"

        return {
            'toggles': self.toggle_count,
            'null_load': self.null_load,
            'null_percent': self.null_load * 100,
            'lamp_state': 'ON' if self.lamp_state else 'OFF',
            'status': status,
            'collapsed': self.collapsed,
            'capacity_remaining': (self.CAPACITY - self.null_load) * 100
        }

    def reset(self):
        """Reset to initial state"""
        self.toggle_count = 0
        self.null_load = self.BASELINE_NULL
        self.lamp_state = False
        self.collapsed = False
        self.history.clear()

    def run_simulation(self, max_toggles=1000, delay=0.1, verbose=True):
        """Run automatic simulation"""
        print(f"\n{'='*60}")
        print("EMx Lamp Paradox Simulator")
        print(f"{'='*60}")
        print(f"Baseline NULL: {self.BASELINE_NULL*100:.0f}%")
        print(f"Capacity Limit: {self.CAPACITY*100:.0f}%")
        print(f"{'='*60}\n")

        for _ in range(max_toggles):
            if not self.toggle():
                break

            if verbose and self.toggle_count % 10 == 0:
                status = self.get_status()
                bar_length = 40
                filled = int(bar_length * status['null_load'])
                bar = '█' * filled + '░' * (bar_length - filled)

                print(f"Toggle {status['toggles']:4d} | "
                      f"Lamp: {status['lamp_state']:3s} | "
                      f"∅: [{bar}] {status['null_percent']:5.1f}% | "
                      f"Status: {status['status']}")

            time.sleep(delay)

        # Final report
        print(f"\n{'='*60}")
        if self.collapsed:
            print("❌ SYSTEM COLLAPSED")
            print(f"   NULL exceeded capacity at toggle {self.toggle_count}")
            print(f"   Final ∅: {self.null_load*100:.1f}%")
        else:
            print("✓ Simulation completed")
            print(f"   Total toggles: {self.toggle_count}")
            print(f"   Final ∅: {self.null_load*100:.1f}%")
        print(f"{'='*60}\n")

        return self.history

    def print_explanation(self):
        """Print EMx interpretation"""
        print("\n" + "="*60)
        print("EMx Resolution of the Lamp Paradox")
        print("="*60)
        print("\nCLASSICAL PARADOX:")
        print("  • Infinite toggles → undefined final state")
        print("  • No way to answer: 'Is the lamp on or off?'")
        print("\nEMx RESOLUTION:")
        print("  • Each toggle consumes event budget")
        print("  • Accumulation tracked in ∅ (NULL reservoir)")
        print("  • System collapses when ∅ exceeds capacity (~78%)")
        print("  • The 'limit' is crossing through NULL, not a binary state")
        print("\nKEY INSIGHT:")
        print(f"  • ∅ ≈ {self.BASELINE_NULL*100:.0f}% baseline is irreducible uncertainty")
        print("  • Required for finite resolution of infinite process")
        print("  • Paradox isn't 'unsolved'—it's a routing through NULL")
        print("="*60 + "\n")


def main():
    """Main execution"""
    simulator = EMxLampParadox()
    simulator.print_explanation()

    # Run simulation
    history = simulator.run_simulation(
        max_toggles=1000,
        delay=0.05,
        verbose=True
    )

    # Optional: Export history for analysis
    if history:
        print(f"Captured {len(history)} state transitions")
        print(f"Peak NULL load: {max(h.null_load for h in history)*100:.1f}%")

if __name__ == "__main__":
    main()
