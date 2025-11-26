"""
EMx Tokenizer
Bidirectional encoding between EMx states/operators/harmonics and discrete token IDs.
Integrates directly with existing EMx kernel primitives.
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from emx_kernel import (
    EMxKernel, EMxState, TernaryTriple, Polarity,
    Harmonics, k_class, classify_state, NullClass
)

# ═══════════════════════════════════════════════════════════════
# I. TOKEN VOCABULARY
# ═══════════════════════════════════════════════════════════════

class TokenType(Enum):
    """Token type classification"""
    SPECIAL = 0      # Special tokens (PAD, BOS, EOS, etc.)
    STATE = 1        # Ternary state (27 tokens)
    OPERATOR = 2     # Operators O1-O10 (10 tokens)
    HARMONIC = 3     # Discretized harmonics (5 metrics × bins)
    META = 4         # Metadata (domain, phase, etc.)

@dataclass
class Token:
    """Single token with metadata"""
    id: int
    type: TokenType
    value: Any
    symbol: str

    def __repr__(self):
        return f"Token({self.id}, {self.symbol})"

class EMxVocabulary:
    """Complete EMx vocabulary"""

    # Special tokens (0-9)
    SPECIAL_TOKENS = {
        '<PAD>': 0,
        '<BOS>': 1,    # Begin of sequence
        '<EOS>': 2,    # End of sequence
        '<SEP>': 3,    # Separator
        '<MASK>': 4,   # Masked token (for MLM training)
        '<UNK>': 5,    # Unknown
        '<GATE_FAIL>': 6,  # Gate failure marker
        '<CYCLE_START>': 7,  # Cycle boundary
        '<CYCLE_END>': 8,
        '<DOMAIN>': 9,  # Domain marker
    }

    # State tokens (10-36): 27 T₀ states
    STATE_OFFSET = 10

    # Operator tokens (37-46): O1-O10
    OPERATOR_OFFSET = 37
    OPERATOR_TOKENS = {
        'O1': 37, 'O2': 38, 'O3': 39, 'O4': 40, 'O5': 41,
        'O6': 42, 'O7': 43, 'O8': 44, 'O9': 45, 'O10': 46
    }

    # Harmonic tokens (47-96): 5 metrics × 10 bins each
    HARMONIC_OFFSET = 47
    HARMONIC_BINS = 10  # Discretize [0,1] into 10 bins

    # Meta tokens (97-106): Domains, phases
    META_OFFSET = 97
    META_TOKENS = {
        'LOGIC': 97,
        'ARITHMETIC': 98,
        'OPTIMIZATION': 99,
        'FINANCIAL': 100,
        'CLIMATE': 101,
        'KERNEL': 102,
        'P1': 103, 'P2': 104, 'P3': 105, 'P4': 106,
        'P5': 107, 'P6': 108, 'P7': 109
    }

    # Total vocabulary size
    VOCAB_SIZE = 110

    @staticmethod
    def get_state_id(triple: TernaryTriple) -> int:
        """
        Map ternary triple to unique state ID

        Encoding: Each axis ∈ {−0, 0, +0} → {0, 1, 2}
        State ID = x*9 + y*3 + z
        """
        def polarity_to_int(p: Polarity) -> int:
            if p == Polarity.MINUS_ZERO:
                return 0
            elif p == Polarity.ZERO:
                return 1
            elif p == Polarity.PLUS_ZERO:
                return 2

        x = polarity_to_int(triple[0])
        y = polarity_to_int(triple[1])
        z = polarity_to_int(triple[2])

        state_index = x * 9 + y * 3 + z
        return EMxVocabulary.STATE_OFFSET + state_index

    @staticmethod
    def get_triple_from_id(token_id: int) -> TernaryTriple:
        """
        Inverse: state ID → ternary triple
        """
        if token_id < EMxVocabulary.STATE_OFFSET or token_id >= EMxVocabulary.STATE_OFFSET + 27:
            raise ValueError(f"Token {token_id} is not a valid state token")

        state_index = token_id - EMxVocabulary.STATE_OFFSET

        x = state_index // 9
        y = (state_index % 9) // 3
        z = state_index % 3

        def int_to_polarity(i: int) -> Polarity:
            if i == 0:
                return Polarity.MINUS_ZERO
            elif i == 1:
                return Polarity.ZERO
            elif i == 2:
                return Polarity.PLUS_ZERO

        return (int_to_polarity(x), int_to_polarity(y), int_to_polarity(z))

    @staticmethod
    def get_operator_id(operator: str) -> int:
        """Map operator string to token ID"""
        op_upper = operator.upper()
        if op_upper in EMxVocabulary.OPERATOR_TOKENS:
            return EMxVocabulary.OPERATOR_TOKENS[op_upper]
        return EMxVocabulary.SPECIAL_TOKENS['<UNK>']

    @staticmethod
    def get_operator_from_id(token_id: int) -> str:
        """Inverse: token ID → operator string"""
        for op, tid in EMxVocabulary.OPERATOR_TOKENS.items():
            if tid == token_id:
                return op
        return '<UNK>'

    @staticmethod
    def discretize_harmonic(value: float, metric_name: str) -> int:
        """
        Discretize harmonic metric into bins

        Returns token ID for binned value
        Bins: [0.0-0.1), [0.1-0.2), ..., [0.9-1.0]
        """
        # Clamp to [0, 1]
        value = max(0.0, min(1.0, value))

        # Which bin? (0-9)
        bin_idx = min(int(value * EMxVocabulary.HARMONIC_BINS), EMxVocabulary.HARMONIC_BINS - 1)

        # Which metric? (0-4 for α, β, γ, Ω, ∅)
        metric_offsets = {
            'alpha': 0,
            'beta': 1,
            'gamma': 2,
            'omega': 3,
            'null': 4
        }

        metric_offset = metric_offsets.get(metric_name, 0)

        token_id = (EMxVocabulary.HARMONIC_OFFSET +
                   metric_offset * EMxVocabulary.HARMONIC_BINS +
                   bin_idx)

        return token_id

    @staticmethod
    def undiscretize_harmonic(token_id: int) -> Tuple[str, float]:
        """
        Inverse: token ID → (metric_name, approximate_value)

        Returns bin center value
        """
        if token_id < EMxVocabulary.HARMONIC_OFFSET or token_id >= EMxVocabulary.HARMONIC_OFFSET + 50:
            raise ValueError(f"Token {token_id} is not a valid harmonic token")

        offset = token_id - EMxVocabulary.HARMONIC_OFFSET

        metric_idx = offset // EMxVocabulary.HARMONIC_BINS
        bin_idx = offset % EMxVocabulary.HARMONIC_BINS

        metric_names = ['alpha', 'beta', 'gamma', 'omega', 'null']
        metric_name = metric_names[metric_idx]

        # Return bin center
        value = (bin_idx + 0.5) / EMxVocabulary.HARMONIC_BINS

        return metric_name, value

# ═══════════════════════════════════════════════════════════════
# II. TOKENIZER
# ═══════════════════════════════════════════════════════════════

class EMxTokenizer:
    """
    Bidirectional tokenizer for EMx framework

    Converts between:
    - EMx primitives (states, operators, harmonics) ↔ token IDs
    - Trajectories ↔ token sequences
    """

    def __init__(self):
        self.vocab = EMxVocabulary()
        self.vocab_size = EMxVocabulary.VOCAB_SIZE

    # ─────────────────────────────────────────────────────────
    # Encoding (EMx → Tokens)
    # ─────────────────────────────────────────────────────────

    def encode_state(self, triple: TernaryTriple) -> int:
        """Encode ternary triple as single token"""
        return self.vocab.get_state_id(triple)

    def encode_operator(self, operator: str) -> int:
        """Encode operator as single token"""
        return self.vocab.get_operator_id(operator)

    def encode_harmonics(self, harmonics: Harmonics) -> List[int]:
        """
        Encode harmonics as 5 tokens (one per metric)

        Returns: [α_token, β_token, γ_token, Ω_token, ∅_token]
        """
        return [
            self.vocab.discretize_harmonic(harmonics.alpha, 'alpha'),
            self.vocab.discretize_harmonic(harmonics.beta, 'beta'),
            self.vocab.discretize_harmonic(harmonics.gamma, 'gamma'),
            self.vocab.discretize_harmonic(1.0 if harmonics.omega else 0.0, 'omega'),
            self.vocab.discretize_harmonic(harmonics.null_share, 'null')
        ]

    def encode_step(self,
                    state: TernaryTriple,
                    operator: str,
                    next_state: TernaryTriple,
                    harmonics: Harmonics) -> List[int]:
        """
        Encode single step as token sequence

        Format: [state, operator, next_state, α, β, γ, Ω, ∅]
        Total: 8 tokens per step
        """
        tokens = []

        # Current state
        tokens.append(self.encode_state(state))

        # Operator
        tokens.append(self.encode_operator(operator))

        # Next state
        tokens.append(self.encode_state(next_state))

        # Harmonics
        tokens.extend(self.encode_harmonics(harmonics))

        return tokens

    def encode_trajectory(self,
                         trajectory: List[EMxState],
                         operators: List[str],
                         add_special_tokens: bool = True) -> List[int]:
        """
        Encode full trajectory as token sequence

        Args:
            trajectory: List of EMx states
            operators: List of operators applied
            add_special_tokens: Add BOS/EOS tokens

        Returns:
            List of token IDs
        """
        tokens = []

        if add_special_tokens:
            tokens.append(self.vocab.SPECIAL_TOKENS['<BOS>'])

        for i in range(len(trajectory) - 1):
            state = trajectory[i].triple
            operator = operators[i] if i < len(operators) else 'O6'
            next_state = trajectory[i + 1].triple
            harmonics = trajectory[i + 1].harmonics

            step_tokens = self.encode_step(state, operator, next_state, harmonics)
            tokens.extend(step_tokens)

            # Add separator every 96 ticks (cycle boundary)
            if (i + 1) % 96 == 0:
                tokens.append(self.vocab.SPECIAL_TOKENS['<CYCLE_END>'])

        if add_special_tokens:
            tokens.append(self.vocab.SPECIAL_TOKENS['<EOS>'])

        return tokens

    def encode_kernel_history(self, kernel: EMxKernel) -> List[int]:
        """
        Encode kernel's full history as tokens

        Convenience method for current kernel state
        """
        trajectory = [kernel.state]  # Current state

        # Reconstruct trajectory from history
        # (Note: operators not stored in history, using O6 as placeholder)
        operators = ['O6'] * len(kernel.state.history)

        return self.encode_trajectory(trajectory, operators)

    # ─────────────────────────────────────────────────────────
    # Decoding (Tokens → EMx)
    # ─────────────────────────────────────────────────────────

    def decode_state(self, token_id: int) -> TernaryTriple:
        """Decode state token to ternary triple"""
        return self.vocab.get_triple_from_id(token_id)

    def decode_operator(self, token_id: int) -> str:
        """Decode operator token to string"""
        return self.vocab.get_operator_from_id(token_id)

    def decode_harmonics(self, tokens: List[int]) -> Dict[str, float]:
        """
        Decode 5 harmonic tokens to metric values

        Args:
            tokens: [α_token, β_token, γ_token, Ω_token, ∅_token]

        Returns:
            Dict with metric names and approximate values
        """
        if len(tokens) != 5:
            raise ValueError(f"Expected 5 harmonic tokens, got {len(tokens)}")

        harmonics = {}

        for token_id in tokens:
            metric_name, value = self.vocab.undiscretize_harmonic(token_id)
            harmonics[metric_name] = value

        return harmonics

    def decode_step(self, tokens: List[int]) -> Tuple[TernaryTriple, str, TernaryTriple, Dict[str, float]]:
        """
        Decode 8-token step sequence

        Returns: (state, operator, next_state, harmonics_dict)
        """
        if len(tokens) < 8:
            raise ValueError(f"Expected at least 8 tokens for step, got {len(tokens)}")

        state = self.decode_state(tokens[0])
        operator = self.decode_operator(tokens[1])
        next_state = self.decode_state(tokens[2])
        harmonics = self.decode_harmonics(tokens[3:8])

        return state, operator, next_state, harmonics

    def decode_trajectory(self, tokens: List[int], skip_special: bool = True) -> List[Tuple]:
        """
        Decode token sequence to trajectory

        Returns:
            List of (state, operator, next_state, harmonics) tuples
        """
        trajectory = []

        i = 0
        while i < len(tokens):
            token_id = tokens[i]

            # Skip special tokens
            if skip_special and token_id < self.vocab.STATE_OFFSET:
                i += 1
                continue

            # Try to decode step (8 tokens)
            if i + 7 < len(tokens):
                try:
                    step = self.decode_step(tokens[i:i+8])
                    trajectory.append(step)
                    i += 8
                except:
                    i += 1  # Skip invalid token
            else:
                break

        return trajectory

    # ─────────────────────────────────────────────────────────
    # Utility Methods
    # ─────────────────────────────────────────────────────────

    def token_to_string(self, token_id: int) -> str:
        """Convert token ID to human-readable string"""
        # Special tokens
        for symbol, tid in self.vocab.SPECIAL_TOKENS.items():
            if tid == token_id:
                return symbol

        # State tokens
        if self.vocab.STATE_OFFSET <= token_id < self.vocab.STATE_OFFSET + 27:
            triple = self.decode_state(token_id)
            return f"S{token_id-self.vocab.STATE_OFFSET}:{triple}"

        # Operator tokens
        if self.vocab.OPERATOR_OFFSET <= token_id < self.vocab.OPERATOR_OFFSET + 10:
            return self.decode_operator(token_id)

        # Harmonic tokens
        if self.vocab.HARMONIC_OFFSET <= token_id < self.vocab.HARMONIC_OFFSET + 50:
            metric_name, value = self.vocab.undiscretize_harmonic(token_id)
            return f"{metric_name[:1]}={value:.1f}"

        # Meta tokens
        for symbol, tid in self.vocab.META_TOKENS.items():
            if tid == token_id:
                return symbol

        return f"T{token_id}"

    def tokens_to_string(self, tokens: List[int]) -> str:
        """Convert token sequence to readable string"""
        return ' '.join(self.token_to_string(t) for t in tokens)

    def get_vocab_info(self) -> Dict[str, Any]:
        """Get vocabulary information"""
        return {
            'vocab_size': self.vocab_size,
            'special_tokens': len(self.vocab.SPECIAL_TOKENS),
            'state_tokens': 27,
            'operator_tokens': 10,
            'harmonic_tokens': 50,
            'meta_tokens': len(self.vocab.META_TOKENS),
            'token_ranges': {
                'special': (0, 9),
                'states': (10, 36),
                'operators': (37, 46),
                'harmonics': (47, 96),
                'meta': (97, 109)
            }
        }

# ═══════════════════════════════════════════════════════════════
# III. DATASET GENERATOR
# ═══════════════════════════════════════════════════════════════

class EMxDatasetGenerator:
    """Generate tokenized training datasets from EMx trajectories"""

    def __init__(self, tokenizer: EMxTokenizer):
        self.tokenizer = tokenizer

    def generate_training_example(self,
                                  kernel: EMxKernel,
                                  operator_sequence: List[str],
                                  domain: str = 'KERNEL') -> Dict[str, Any]:
        """
        Generate single training example

        Returns:
            {
                'tokens': List[int],
                'states': List[TernaryTriple],
                'operators': List[str],
                'harmonics': List[Dict],
                'domain': str,
                'length': int
            }
        """
        trajectory = []
        operators_applied = []
        harmonics_list = []

        # Execute sequence
        for op in operator_sequence:
            success, reason = kernel.step(op, axis=0)

            trajectory.append(kernel.state)
            operators_applied.append(op)
            harmonics_list.append({
                'alpha': kernel.state.harmonics.alpha,
                'beta': kernel.state.harmonics.beta,
                'gamma': kernel.state.harmonics.gamma,
                'omega': kernel.state.harmonics.omega,
                'null': kernel.state.harmonics.null_share
            })

            if not success:
                # Add gate failure token
                break

        # Tokenize
        tokens = self.tokenizer.encode_trajectory(trajectory, operators_applied)

        return {
            'tokens': tokens,
            'states': [s.triple for s in trajectory],
            'operators': operators_applied,
            'harmonics': harmonics_list,
            'domain': domain,
            'length': len(tokens)
        }

    def generate_dataset(self,
                        num_examples: int = 1000,
                        ticks_per_example: int = 96) -> List[Dict[str, Any]]:
        """
        Generate full dataset

        Args:
            num_examples: Number of trajectories to generate
            ticks_per_example: Length of each trajectory

        Returns:
            List of training examples
        """
        dataset = []

        # Standard operator sequences
        sequences = [
            ['O2', 'O3', 'O6'] * (ticks_per_example // 3),  # Canonical cycle
            ['O2'] * ticks_per_example,  # Expansion
            ['O6'] * ticks_per_example,  # Normalization
            ['O7', 'O2', 'O6'] * (ticks_per_example // 3),  # Exchange-expand-normalize
            ['O2', 'O3', 'O3', 'O6'] * (ticks_per_example // 4),  # Double rotation
        ]

        for i in range(num_examples):
            kernel = EMxKernel()

            # Select sequence
            sequence = sequences[i % len(sequences)]

            example = self.generate_training_example(kernel, sequence)
            dataset.append(example)

            if (i + 1) % 100 == 0:
                print(f"Generated {i+1}/{num_examples} examples...")

        return dataset

# ═══════════════════════════════════════════════════════════════
# IV. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate EMx tokenizer"""
    print("="*70)
    print("EMx Tokenizer Demo")
    print("="*70)

    tokenizer = EMxTokenizer()

    # Test 1: Encode/decode state
    print("\n--- Test 1: State Encoding ---")
    state = (Polarity.PLUS_ZERO, Polarity.MINUS_ZERO, Polarity.ZERO)
    token_id = tokenizer.encode_state(state)
    decoded = tokenizer.decode_state(token_id)

    print(f"Original state: {state}")
    print(f"Token ID: {token_id}")
    print(f"Decoded state: {decoded}")
    print(f"Match: {state == decoded}")

    # Test 2: Encode/decode operator
    print("\n--- Test 2: Operator Encoding ---")
    operator = 'O2'
    token_id = tokenizer.encode_operator(operator)
    decoded = tokenizer.decode_operator(token_id)

    print(f"Original operator: {operator}")
    print(f"Token ID: {token_id}")
    print(f"Decoded operator: {decoded}")

    # Test 3: Encode/decode harmonics
    print("\n--- Test 3: Harmonics Encoding ---")
    from emx_kernel import Harmonics

    harmonics = Harmonics(
        alpha=0.667,
        beta=0.180,
        gamma=0.996,
        omega=True,
        null_share=0.220
    )

    tokens = tokenizer.encode_harmonics(harmonics)
    decoded = tokenizer.decode_harmonics(tokens)

    print(f"Original harmonics:")
    print(f"  α: {harmonics.alpha:.3f}")
    print(f"  β: {harmonics.beta:.3f}")
    print(f"  γ: {harmonics.gamma:.3f}")
    print(f"  Ω: {harmonics.omega}")
    print(f"  ∅: {harmonics.null_share:.3f}")

    print(f"\nTokens: {tokens}")
    print(f"Decoded harmonics:")
    for key, value in decoded.items():
        print(f"  {key}: {value:.3f}")

    # Test 4: Encode trajectory
    print("\n--- Test 4: Trajectory Encoding ---")
    kernel = EMxKernel()
    operators = ['O2', 'O3', 'O6', 'O2']

    trajectory = [kernel.state]
    for op in operators:
        kernel.step(op, axis=0)
        trajectory.append(kernel.state)

    tokens = tokenizer.encode_trajectory(trajectory, operators)

    print(f"Trajectory length: {len(trajectory)} states")
    print(f"Operators: {operators}")
    print(f"Token sequence length: {len(tokens)}")
    print(f"Tokens (first 20): {tokens[:20]}")
    print(f"\nReadable: {tokenizer.tokens_to_string(tokens[:20])}")

    # Test 5: Decode trajectory
    print("\n--- Test 5: Trajectory Decoding ---")
    decoded_trajectory = tokenizer.decode_trajectory(tokens)

    print(f"Decoded {len(decoded_trajectory)} steps")
    for i, (state, op, next_state, harms) in enumerate(decoded_trajectory[:3]):
        print(f"\nStep {i}:")
        print(f"  State: {state}")
        print(f"  Operator: {op}")
        print(f"  Next: {next_state}")
        print(f"  γ: {harms['gamma']:.2f}")

    # Test 6: Vocabulary info
    print("\n--- Test 6: Vocabulary Information ---")
    vocab_info = tokenizer.get_vocab_info()

    print(f"Vocabulary size: {vocab_info['vocab_size']}")
    print(f"Token categories:")
    for category, count in vocab_info.items():
        if category not in ['vocab_size', 'token_ranges']:
            print(f"  {category}: {count}")

    # Test 7: Dataset generation
    print("\n--- Test 7: Dataset Generation ---")
    generator = EMxDatasetGenerator(tokenizer)

    print("Generating 5 training examples...")
    dataset = generator.generate_dataset(num_examples=5, ticks_per_example=12)

    print(f"Generated {len(dataset)} examples")
    print(f"\nExample 0:")
    print(f"  Domain: {dataset[0]['domain']}")
    print(f"  Length: {dataset[0]['length']} tokens")
    print(f"  Operators: {dataset[0]['operators'][:5]}...")
    print(f"  Final ∅: {dataset[0]['harmonics'][-1]['null']:.3f}")

    print("\n" + "="*70)
    print("✓ Tokenizer demonstration complete")
    print("="*70)
    print(f"\nKey Statistics:")
    print(f"  • Vocabulary size: {tokenizer.vocab_size} tokens")
    print(f"  • State encoding: Lossless (27 states)")
    print(f"  • Operator encoding: Lossless (10 ops)")
    print(f"  • Harmonic encoding: ~10% quantization loss")
    print(f"  • Sequence format: 8 tokens per step")
    print(f"  • 96-tick cycle: 768 tokens + special tokens")

if __name__ == "__main__":
    demo()
