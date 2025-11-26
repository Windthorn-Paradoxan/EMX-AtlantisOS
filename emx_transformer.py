"""
EMx Transformer Model
Lightweight transformer architecture optimized for EMx token sequences.
File 3 of 4 in the LLM training pipeline.
"""

import math
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════
# I. MODEL CONFIGURATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class EMxModelConfig:
    """Configuration for EMx transformer model"""

    # Vocabulary
    vocab_size: int = 110  # EMx tokenizer vocabulary

    # Architecture
    d_model: int = 256  # Embedding dimension (small for laptop)
    n_heads: int = 4    # Attention heads
    n_layers: int = 6   # Transformer layers
    d_ff: int = 1024    # Feedforward dimension

    # Sequence
    max_seq_length: int = 1024  # Max sequence length (longer than 768 for flexibility)

    # Regularization
    dropout: float = 0.1
    attention_dropout: float = 0.1

    # Training
    learning_rate: float = 3e-4
    weight_decay: float = 0.01
    warmup_steps: int = 1000
    max_grad_norm: float = 1.0

    # Special tokens
    pad_token_id: int = 0
    bos_token_id: int = 1
    eos_token_id: int = 2

    def __post_init__(self):
        """Validate configuration"""
        assert self.d_model % self.n_heads == 0, "d_model must be divisible by n_heads"

# ═══════════════════════════════════════════════════════════════
# II. POSITIONAL ENCODING
# ═══════════════════════════════════════════════════════════════

class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding"""

    def __init__(self, d_model: int, max_seq_length: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        # Create positional encoding matrix
        position = torch.arange(max_seq_length).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))

        pe = torch.zeros(max_seq_length, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)

        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape (batch_size, seq_length, d_model)

        Returns:
            Tensor with positional encoding added
        """
        x = x + self.pe[:x.size(1)]
        return self.dropout(x)

# ═══════════════════════════════════════════════════════════════
# III. MULTI-HEAD ATTENTION
# ═══════════════════════════════════════════════════════════════

class MultiHeadAttention(nn.Module):
    """Multi-head self-attention with causal masking"""

    def __init__(self, d_model: int, n_heads: int, dropout: float = 0.1):
        super().__init__()
        assert d_model % n_heads == 0

        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads

        # Linear projections
        self.q_linear = nn.Linear(d_model, d_model)
        self.k_linear = nn.Linear(d_model, d_model)
        self.v_linear = nn.Linear(d_model, d_model)
        self.out_linear = nn.Linear(d_model, d_model)

        self.dropout = nn.Dropout(dropout)

        # Causal mask (register as buffer so it moves with model)
        self.register_buffer('causal_mask', None)

    def _get_causal_mask(self, seq_length: int, device: torch.device) -> torch.Tensor:
        """Create causal mask for autoregressive generation"""
        if self.causal_mask is None or self.causal_mask.size(0) < seq_length:
            mask = torch.triu(torch.ones(seq_length, seq_length, device=device), diagonal=1)
            mask = mask.bool()
            self.causal_mask = mask

        return self.causal_mask[:seq_length, :seq_length]

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_length, d_model)
            mask: Optional padding mask (batch_size, seq_length)

        Returns:
            (batch_size, seq_length, d_model)
        """
        batch_size, seq_length, _ = x.size()

        # Linear projections and reshape for multi-head
        q = self.q_linear(x).view(batch_size, seq_length, self.n_heads, self.d_k).transpose(1, 2)
        k = self.k_linear(x).view(batch_size, seq_length, self.n_heads, self.d_k).transpose(1, 2)
        v = self.v_linear(x).view(batch_size, seq_length, self.n_heads, self.d_k).transpose(1, 2)

        # Scaled dot-product attention
        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)

        # Apply causal mask
        causal_mask = self._get_causal_mask(seq_length, x.device)
        scores = scores.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float('-inf'))

        # Apply padding mask if provided
        if mask is not None:
            scores = scores.masked_fill(mask.unsqueeze(1).unsqueeze(2), float('-inf'))

        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)

        # Apply attention to values
        out = torch.matmul(attn, v)

        # Concatenate heads and project
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_length, self.d_model)
        out = self.out_linear(out)

        return out

# ═══════════════════════════════════════════════════════════════
# IV. FEEDFORWARD NETWORK
# ═══════════════════════════════════════════════════════════════

class FeedForward(nn.Module):
    """Position-wise feedforward network"""

    def __init__(self, d_model: int, d_ff: int, dropout: float = 0.1):
        super().__init__()
        self.linear1 = nn.Linear(d_model, d_ff)
        self.linear2 = nn.Linear(d_ff, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_length, d_model)

        Returns:
            (batch_size, seq_length, d_model)
        """
        x = self.linear1(x)
        x = F.gelu(x)  # GELU activation (modern choice)
        x = self.dropout(x)
        x = self.linear2(x)
        return x

# ═══════════════════════════════════════════════════════════════
# V. TRANSFORMER LAYER
# ═══════════════════════════════════════════════════════════════

class TransformerLayer(nn.Module):
    """Single transformer layer with pre-norm architecture"""

    def __init__(self, config: EMxModelConfig):
        super().__init__()

        # Multi-head attention
        self.attention = MultiHeadAttention(
            config.d_model,
            config.n_heads,
            config.attention_dropout
        )

        # Feedforward
        self.feed_forward = FeedForward(
            config.d_model,
            config.d_ff,
            config.dropout
        )

        # Layer normalization (pre-norm)
        self.norm1 = nn.LayerNorm(config.d_model)
        self.norm2 = nn.LayerNorm(config.d_model)

        # Dropout
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_length, d_model)
            mask: Optional padding mask

        Returns:
            (batch_size, seq_length, d_model)
        """
        # Pre-norm attention with residual
        attn_out = self.attention(self.norm1(x), mask)
        x = x + self.dropout(attn_out)

        # Pre-norm feedforward with residual
        ff_out = self.feed_forward(self.norm2(x))
        x = x + self.dropout(ff_out)

        return x

# ═══════════════════════════════════════════════════════════════
# VI. EMX TRANSFORMER MODEL
# ═══════════════════════════════════════════════════════════════

class EMxTransformer(nn.Module):
    """
    Complete transformer model for EMx token sequences

    Predicts next operator given (state, harmonics) context
    """

    def __init__(self, config: EMxModelConfig):
        super().__init__()
        self.config = config

        # Token embedding
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model)

        # Positional encoding
        self.pos_encoding = PositionalEncoding(
            config.d_model,
            config.max_seq_length,
            config.dropout
        )

        # Transformer layers
        self.layers = nn.ModuleList([
            TransformerLayer(config)
            for _ in range(config.n_layers)
        ])

        # Final layer norm
        self.norm = nn.LayerNorm(config.d_model)

        # Output projection to vocabulary
        self.output = nn.Linear(config.d_model, config.vocab_size)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Initialize weights with Xavier/Kaiming initialization"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self,
                input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass

        Args:
            input_ids: (batch_size, seq_length) - Token IDs
            attention_mask: (batch_size, seq_length) - Padding mask (1 = keep, 0 = mask)

        Returns:
            logits: (batch_size, seq_length, vocab_size) - Next token predictions
        """
        # Create padding mask if needed
        if attention_mask is not None:
            # Convert to boolean (True = masked position)
            padding_mask = (attention_mask == 0)
        else:
            padding_mask = None

        # Embed tokens
        x = self.token_embedding(input_ids)

        # Add positional encoding
        x = self.pos_encoding(x)

        # Pass through transformer layers
        for layer in self.layers:
            x = layer(x, padding_mask)

        # Final normalization
        x = self.norm(x)

        # Project to vocabulary
        logits = self.output(x)

        return logits

    def generate(self,
                 input_ids: torch.Tensor,
                 max_length: int = 100,
                 temperature: float = 1.0,
                 top_k: Optional[int] = None,
                 top_p: Optional[float] = None) -> torch.Tensor:
        """
        Generate sequence autoregressively

        Args:
            input_ids: (batch_size, seq_length) - Initial context
            max_length: Maximum length to generate
            temperature: Sampling temperature
            top_k: Top-k sampling
            top_p: Nucleus sampling

        Returns:
            (batch_size, seq_length + generated_length) - Generated sequence
        """
        self.eval()

        with torch.no_grad():
            for _ in range(max_length):
                # Forward pass
                logits = self.forward(input_ids)

                # Get logits for last position
                next_token_logits = logits[:, -1, :] / temperature

                # Apply top-k filtering
                if top_k is not None:
                    indices_to_remove = next_token_logits < torch.topk(next_token_logits, top_k)[0][..., -1, None]
                    next_token_logits[indices_to_remove] = float('-inf')

                # Apply top-p (nucleus) filtering
                if top_p is not None:
                    sorted_logits, sorted_indices = torch.sort(next_token_logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)

                    # Remove tokens with cumulative probability above threshold
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = 0

                    indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
                    next_token_logits[indices_to_remove] = float('-inf')

                # Sample from distribution
                probs = F.softmax(next_token_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)

                # Append to sequence
                input_ids = torch.cat([input_ids, next_token], dim=1)

                # Stop at EOS token
                if (next_token == self.config.eos_token_id).all():
                    break

        return input_ids

    def get_num_params(self) -> int:
        """Count total trainable parameters"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

# ═══════════════════════════════════════════════════════════════
# VII. MODEL UTILITIES
# ═══════════════════════════════════════════════════════════════

def create_emx_model(config: Optional[EMxModelConfig] = None) -> EMxTransformer:
    """Create EMx transformer model with default or custom config"""
    if config is None:
        config = EMxModelConfig()

    model = EMxTransformer(config)

    num_params = model.get_num_params()
    print(f"Created EMx Transformer with {num_params:,} parameters")
    print(f"  Layers: {config.n_layers}")
    print(f"  d_model: {config.d_model}")
    print(f"  Heads: {config.n_heads}")
    print(f"  d_ff: {config.d_ff}")

    return model

def save_model(model: EMxTransformer, path: str):
    """Save model weights and config"""
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': model.config
    }, path)

def load_model(path: str) -> EMxTransformer:
    """Load model from checkpoint"""
    checkpoint = torch.load(path)
    config = checkpoint['config']

    model = EMxTransformer(config)
    model.load_state_dict(checkpoint['model_state_dict'])

    return model

# ═══════════════════════════════════════════════════════════════
# VIII. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Demonstrate EMx transformer model"""
    print("="*70)
    print("EMx Transformer Model Demo")
    print("="*70)

    # Create model
    print("\n--- Test 1: Model Creation ---")
    config = EMxModelConfig(
        d_model=128,  # Smaller for demo
        n_heads=4,
        n_layers=4,
        d_ff=512
    )

    model = create_emx_model(config)

    # Test forward pass
    print("\n--- Test 2: Forward Pass ---")
    batch_size = 2
    seq_length = 50

    # Random input tokens
    input_ids = torch.randint(0, config.vocab_size, (batch_size, seq_length))

    # Forward pass
    logits = model(input_ids)

    print(f"Input shape: {input_ids.shape}")
    print(f"Output shape: {logits.shape}")
    print(f"Expected shape: ({batch_size}, {seq_length}, {config.vocab_size})")

    # Test with attention mask
    print("\n--- Test 3: Attention Mask ---")
    attention_mask = torch.ones(batch_size, seq_length)
    attention_mask[0, 30:] = 0  # Mask second half of first sequence

    logits_masked = model(input_ids, attention_mask)
    print(f"Forward pass with masking successful")

    # Test generation
    print("\n--- Test 4: Autoregressive Generation ---")
    context = torch.randint(0, config.vocab_size, (1, 10))

    generated = model.generate(
        context,
        max_length=20,
        temperature=1.0,
        top_k=10
    )

    print(f"Context length: {context.shape[1]}")
    print(f"Generated length: {generated.shape[1]}")
    print(f"Generated tokens: {generated[0].tolist()[:15]}...")

    # Model statistics
    print("\n--- Test 5: Model Statistics ---")
    num_params = model.get_num_params()
    print(f"Total parameters: {num_params:,}")

    # Estimate memory
    param_memory = num_params * 4 / (1024**2)  # 4 bytes per float32
    print(f"Parameter memory: ~{param_memory:.1f} MB")

    # Estimate FLOPS for forward pass
    # Rough estimate: 2 * num_params * seq_length
    flops = 2 * num_params * seq_length
    print(f"FLOPs per forward pass: ~{flops/1e9:.2f} GFLOPs")

    print("\n" + "="*70)
    print("✓ Model demonstration complete")
    print("="*70)

    print(f"\nModel Summary:")
    print(f"  • Architecture: Transformer (pre-norm)")
    print(f"  • Parameters: {num_params:,}")
    print(f"  • Memory: ~{param_memory:.1f} MB")
    print(f"  • Vocabulary: {config.vocab_size} tokens")
    print(f"  • Max sequence: {config.max_seq_length}")
    print(f"  • Ready for training on laptop")

if __name__ == "__main__":
    demo()
