"""
EMx LLM Trainer
Complete training loop with checkpointing, metrics tracking, and resume capability.
File 4 of 4 in the LLM training pipeline.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import time
from pathlib import Path
import numpy as np
from tqdm import tqdm

from emx_model import EMxTransformer, EMxModelConfig
from emx_persistence import EMxPersistence, TrainingState, Checkpoint
from emx_dataset_builder import EMxDatasetBuilder, DatasetConfig
from emx_tokenizer import EMxTokenizer

# ═══════════════════════════════════════════════════════════════
# I. DATASET WRAPPER
# ═══════════════════════════════════════════════════════════════

class EMxTokenDataset(Dataset):
    """PyTorch dataset wrapper for EMx tokens"""

    def __init__(self, persistence: EMxPersistence, max_batches: Optional[int] = None):
        self.persistence = persistence
        self.batches = []

        # Load batch indices
        for i, batch in enumerate(persistence.datasets.iter_batches()):
            if max_batches is not None and i >= max_batches:
                break
            self.batches.append(batch.batch_id)

    def __len__(self) -> int:
        return len(self.batches)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Get single batch

        Returns dict with:
            - input_ids: (batch_size, seq_length)
            - labels: (batch_size, seq_length)
            - attention_mask: (batch_size, seq_length)
        """
        batch = self.persistence.datasets.load_batch(self.batches[idx])

        # Convert to tensors
        input_ids = torch.from_numpy(batch.tokens).long()

        # Create labels (shifted by 1 for next-token prediction)
        labels = input_ids.clone()

        # Create attention mask (1 for real tokens, 0 for padding)
        attention_mask = (input_ids != 0).long()

        return {
            'input_ids': input_ids,
            'labels': labels,
            'attention_mask': attention_mask
        }

# ═══════════════════════════════════════════════════════════════
# II. TRAINING CONFIGURATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class TrainerConfig:
    """Training hyperparameters"""

    # Training
    num_epochs: int = 10
    batch_size: int = 32
    gradient_accumulation_steps: int = 1

    # Optimization
    learning_rate: float = 3e-4
    weight_decay: float = 0.01
    max_grad_norm: float = 1.0
    warmup_steps: int = 1000

    # Checkpointing
    save_every_n_steps: int = 1000
    eval_every_n_steps: int = 500
    log_every_n_steps: int = 100

    # Device
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu'

    # Mixed precision
    use_amp: bool = torch.cuda.is_available()  # Automatic mixed precision

    # Early stopping
    patience: int = 5  # Stop if no improvement for N evaluations
    min_delta: float = 0.001  # Minimum improvement to count

# ═══════════════════════════════════════════════════════════════
# III. LEARNING RATE SCHEDULER
# ═══════════════════════════════════════════════════════════════

class WarmupCosineScheduler:
    """Learning rate scheduler with warmup and cosine decay"""

    def __init__(self,
                 optimizer: optim.Optimizer,
                 warmup_steps: int,
                 total_steps: int,
                 min_lr: float = 1e-6):
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.total_steps = total_steps
        self.min_lr = min_lr
        self.base_lr = optimizer.param_groups[0]['lr']
        self.step_count = 0

    def step(self):
        """Update learning rate"""
        self.step_count += 1

        if self.step_count < self.warmup_steps:
            # Linear warmup
            lr = self.base_lr * (self.step_count / self.warmup_steps)
        else:
            # Cosine decay
            progress = (self.step_count - self.warmup_steps) / (self.total_steps - self.warmup_steps)
            lr = self.min_lr + (self.base_lr - self.min_lr) * 0.5 * (1 + np.cos(np.pi * progress))

        for param_group in self.optimizer.param_groups:
            param_group['lr'] = lr

        return lr

# ═══════════════════════════════════════════════════════════════
# IV. METRICS TRACKER
# ═══════════════════════════════════════════════════════════════

class MetricsTracker:
    """Track and compute training metrics"""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all metrics"""
        self.losses = []
        self.accuracies = []
        self.learning_rates = []

    def update(self, loss: float, accuracy: float, lr: float):
        """Update metrics"""
        self.losses.append(loss)
        self.accuracies.append(accuracy)
        self.learning_rates.append(lr)

    def get_averages(self) -> Dict[str, float]:
        """Get average metrics"""
        if not self.losses:
            return {'loss': 0.0, 'accuracy': 0.0, 'lr': 0.0}

        return {
            'loss': np.mean(self.losses),
            'accuracy': np.mean(self.accuracies),
            'lr': np.mean(self.learning_rates)
        }

# ═══════════════════════════════════════════════════════════════
# V. TRAINER
# ═══════════════════════════════════════════════════════════════

class EMxTrainer:
    """Complete training system for EMx transformer"""

    def __init__(self,
                 model: EMxTransformer,
                 persistence: EMxPersistence,
                 config: Optional[TrainerConfig] = None):
        self.model = model
        self.persistence = persistence
        self.config = config or TrainerConfig()

        # Move model to device
        self.device = torch.device(self.config.device)
        self.model.to(self.device)

        # Optimizer
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )

        # Loss function
        self.criterion = nn.CrossEntropyLoss(ignore_index=0)  # Ignore padding

        # Mixed precision scaler
        self.scaler = torch.cuda.amp.GradScaler() if self.config.use_amp else None

        # Scheduler (will be initialized in train())
        self.scheduler = None

        # Metrics
        self.metrics = MetricsTracker()

        # Training state
        self.global_step = 0
        self.current_epoch = 0
        self.best_loss = float('inf')
        self.best_accuracy = 0.0
        self.patience_counter = 0

    def compute_accuracy(self,
                        logits: torch.Tensor,
                        labels: torch.Tensor,
                        mask: torch.Tensor) -> float:
        """
        Compute token-level accuracy

        Args:
            logits: (batch_size, seq_length, vocab_size)
            labels: (batch_size, seq_length)
            mask: (batch_size, seq_length)
        """
        predictions = logits.argmax(dim=-1)

        # Only count non-padded positions
        correct = (predictions == labels) & (mask == 1)
        accuracy = correct.sum().item() / mask.sum().item()

        return accuracy

    def train_step(self, batch: Dict[str, torch.Tensor]) -> Tuple[float, float]:
        """
        Single training step

        Returns: (loss, accuracy)
        """
        input_ids = batch['input_ids'].to(self.device)
        labels = batch['labels'].to(self.device)
        attention_mask = batch['attention_mask'].to(self.device)

        # Forward pass
        if self.config.use_amp:
            with torch.cuda.amp.autocast():
                logits = self.model(input_ids, attention_mask)

                # Compute loss (shift for next-token prediction)
                shift_logits = logits[..., :-1, :].contiguous()
                shift_labels = labels[..., 1:].contiguous()
                shift_mask = attention_mask[..., 1:].contiguous()

                loss = self.criterion(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1)
                )
        else:
            logits = self.model(input_ids, attention_mask)

            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            shift_mask = attention_mask[..., 1:].contiguous()

            loss = self.criterion(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1)
            )

        # Compute accuracy
        with torch.no_grad():
            accuracy = self.compute_accuracy(shift_logits, shift_labels, shift_mask)

        # Backward pass
        if self.config.use_amp:
            self.scaler.scale(loss).backward()
        else:
            loss.backward()

        return loss.item(), accuracy

    def optimizer_step(self):
        """Perform optimizer step with gradient clipping"""
        if self.config.use_amp:
            self.scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
            self.scaler.step(self.optimizer)
            self.scaler.update()
        else:
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
            self.optimizer.step()

        self.optimizer.zero_grad()

    @torch.no_grad()
    def evaluate(self, dataloader: DataLoader) -> Dict[str, float]:
        """
        Evaluate model on validation set

        Returns: Dict with metrics
        """
        self.model.eval()

        total_loss = 0.0
        total_accuracy = 0.0
        num_batches = 0

        for batch in dataloader:
            input_ids = batch['input_ids'].to(self.device)
            labels = batch['labels'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)

            # Forward pass
            logits = self.model(input_ids, attention_mask)

            # Shift for next-token prediction
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = labels[..., 1:].contiguous()
            shift_mask = attention_mask[..., 1:].contiguous()

            # Loss
            loss = self.criterion(
                shift_logits.view(-1, shift_logits.size(-1)),
                shift_labels.view(-1)
            )

            # Accuracy
            accuracy = self.compute_accuracy(shift_logits, shift_labels, shift_mask)

            total_loss += loss.item()
            total_accuracy += accuracy
            num_batches += 1

        self.model.train()

        return {
            'eval_loss': total_loss / num_batches,
            'eval_accuracy': total_accuracy / num_batches
        }

    def save_checkpoint(self, is_best: bool = False):
        """Save training checkpoint"""
        training_state = TrainingState(
            epoch=self.current_epoch,
            step=self.global_step,
            best_loss=self.best_loss,
            best_gamma=self.best_accuracy,  # Using accuracy as proxy for gamma
            learning_rate=self.optimizer.param_groups[0]['lr'],
            examples_seen=self.global_step * self.config.batch_size,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            hyperparameters={
                'batch_size': self.config.batch_size,
                'learning_rate': self.config.learning_rate,
                'weight_decay': self.config.weight_decay
            }
        )

        metrics = {
            'loss': self.best_loss,
            'accuracy': self.best_accuracy
        }

        self.persistence.save_training_snapshot(
            model_state=self.model.state_dict(),
            optimizer_state=self.optimizer.state_dict(),
            training_state=training_state,
            metrics=metrics,
            is_best=is_best
        )

    def load_checkpoint(self, checkpoint: Checkpoint):
        """Load training checkpoint"""
        self.model.load_state_dict(checkpoint.model_state)

        if checkpoint.optimizer_state is not None:
            self.optimizer.load_state_dict(checkpoint.optimizer_state)

        self.global_step = checkpoint.training_state.step
        self.current_epoch = checkpoint.training_state.epoch
        self.best_loss = checkpoint.training_state.best_loss
        self.best_accuracy = checkpoint.training_state.best_gamma

        print(f"Resumed from epoch {self.current_epoch}, step {self.global_step}")

    def train(self,
              train_dataset: EMxTokenDataset,
              eval_dataset: Optional[EMxTokenDataset] = None,
              resume: bool = True):
        """
        Main training loop

        Args:
            train_dataset: Training dataset
            eval_dataset: Optional validation dataset
            resume: Whether to resume from checkpoint
        """
        # Try to resume
        if resume:
            result = self.persistence.resume_training()
            if result is not None:
                checkpoint, logger = result
                self.load_checkpoint(checkpoint)
                print("Resumed training from checkpoint")

        # Create dataloader
        train_loader = DataLoader(
            train_dataset,
            batch_size=1,  # Dataset already returns batches
            shuffle=True,
            num_workers=0  # Set to 0 to avoid multiprocessing issues
        )

        eval_loader = None
        if eval_dataset is not None:
            eval_loader = DataLoader(
                eval_dataset,
                batch_size=1,
                shuffle=False,
                num_workers=0
            )

        # Initialize scheduler
        total_steps = len(train_loader) * self.config.num_epochs
        self.scheduler = WarmupCosineScheduler(
            self.optimizer,
            self.config.warmup_steps,
            total_steps
        )

        # Training loop
        print(f"\n{'='*70}")
        print(f"Starting training for {self.config.num_epochs} epochs")
        print(f"Total steps: {total_steps}")
        print(f"Device: {self.device}")
        print(f"Mixed precision: {self.config.use_amp}")
        print(f"{'='*70}\n")

        self.model.train()

        for epoch in range(self.current_epoch, self.config.num_epochs):
            self.current_epoch = epoch

            epoch_start = time.time()
            self.metrics.reset()

            # Progress bar
            pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{self.config.num_epochs}")

            for batch_idx, batch in enumerate(pbar):
                # Training step
                loss, accuracy = self.train_step(batch)

                # Accumulate gradients
                if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                    self.optimizer_step()

                    if self.scheduler is not None:
                        lr = self.scheduler.step()
                    else:
                        lr = self.optimizer.param_groups[0]['lr']

                    self.global_step += 1

                # Update metrics
                self.metrics.update(loss, accuracy, self.optimizer.param_groups[0]['lr'])

                # Update progress bar
                pbar.set_postfix({
                    'loss': f'{loss:.4f}',
                    'acc': f'{accuracy:.4f}',
                    'lr': f'{self.optimizer.param_groups[0]["lr"]:.2e}'
                })

                # Logging
                if self.global_step % self.config.log_every_n_steps == 0:
                    avg_metrics = self.metrics.get_averages()
                    self.persistence.logger.log_step(self.global_step, avg_metrics['loss'])
                    self.metrics.reset()

                # Evaluation
                if eval_loader is not None and self.global_step % self.config.eval_every_n_steps == 0:
                    eval_metrics = self.evaluate(eval_loader)

                    print(f"\n[Step {self.global_step}] Eval - "
                          f"Loss: {eval_metrics['eval_loss']:.4f}, "
                          f"Acc: {eval_metrics['eval_accuracy']:.4f}")

                    # Check for improvement
                    improved = eval_metrics['eval_loss'] < (self.best_loss - self.config.min_delta)

                    if improved:
                        self.best_loss = eval_metrics['eval_loss']
                        self.best_accuracy = eval_metrics['eval_accuracy']
                        self.patience_counter = 0
                        self.save_checkpoint(is_best=True)
                        print("  ✓ New best model saved!")
                    else:
                        self.patience_counter += 1

                        if self.patience_counter >= self.config.patience:
                            print(f"\nEarly stopping: No improvement for {self.config.patience} evaluations")
                            return

                # Checkpointing
                if self.global_step % self.config.save_every_n_steps == 0:
                    self.save_checkpoint()

            # End of epoch
            epoch_time = time.time() - epoch_start
            avg_metrics = self.metrics.get_averages()

            print(f"\nEpoch {epoch+1} completed in {epoch_time:.1f}s")
            print(f"  Avg Loss: {avg_metrics['loss']:.4f}")
            print(f"  Avg Acc: {avg_metrics['accuracy']:.4f}")

            # Log epoch metrics
            self.persistence.logger.log_epoch(epoch + 1, {
                'train_loss': avg_metrics['loss'],
                'train_accuracy': avg_metrics['accuracy']
            })

        print(f"\n{'='*70}")
        print("Training completed!")
        print(f"Best loss: {self.best_loss:.4f}")
        print(f"Best accuracy: {self.best_accuracy:.4f}")
        print(f"{'='*70}\n")

# ═══════════════════════════════════════════════════════════════
# VI. CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def train_emx_from_scratch(
    workspace_dir: str = "./emx_workspace",
    num_train_examples: int = 10000,
    num_eval_examples: int = 1000,
    model_config: Optional[EMxModelConfig] = None,
    trainer_config: Optional[TrainerConfig] = None
):
    """
    Complete training pipeline from scratch

    1. Generate dataset
    2. Create model
    3. Train model
    4. Save final model
    """
    print("="*70)
    print("EMx Training Pipeline - From Scratch")
    print("="*70)

    # Initialize components
    tokenizer = EMxTokenizer()
    persistence = EMxPersistence(workspace_dir)

    # Step 1: Generate training data
    print("\n[1/4] Generating training data...")
    dataset_config = DatasetConfig(
        num_examples=num_train_examples,
        batch_size=100
    )

    builder = EMxDatasetBuilder(tokenizer, persistence, dataset_config)
    builder.build_dataset(verbose=True)

    # Generate eval data
    if num_eval_examples > 0:
        print("\n[1/4] Generating evaluation data...")
        eval_config = DatasetConfig(
            num_examples=num_eval_examples,
            batch_size=100
        )
        eval_builder = EMxDatasetBuilder(tokenizer, persistence, eval_config)
        eval_builder.build_dataset(verbose=True)

    # Step 2: Create model
    print("\n[2/4] Creating model...")
    from emx_model import create_emx_model

    if model_config is None:
        model_config = EMxModelConfig()

    model = create_emx_model(model_config)

    # Step 3: Create datasets
    print("\n[3/4] Loading datasets...")
    train_dataset = EMxTokenDataset(persistence, max_batches=num_train_examples // 100)
    eval_dataset = EMxTokenDataset(persistence, max_batches=num_eval_examples // 100) if num_eval_examples > 0 else None

    print(f"Train batches: {len(train_dataset)}")
    if eval_dataset:
        print(f"Eval batches: {len(eval_dataset)}")

    # Step 4: Train
    print("\n[4/4] Training...")
    if trainer_config is None:
        trainer_config = TrainerConfig()

    trainer = EMxTrainer(model, persistence, trainer_config)
    trainer.train(train_dataset, eval_dataset, resume=False)

    # Save final model
    final_path = persistence.paths.get_model_path("final_model")
    from emx_model import save_model
    save_model(model, str(final_path))

    print(f"\n✓ Training complete! Model saved to {final_path}")

    return model, trainer

# ═══════════════════════════════════════════════════════════════
# VII. DEMONSTRATION
# ═══════════════════════════════════════════════════════════════

def demo():
    """Quick training demo with small dataset"""
    print("="*70)
    print("EMx Trainer Demo (Small Scale)")
    print("="*70)

    # Small scale for demo
    model, trainer = train_emx_from_scratch(
        workspace_dir="./demo_training",
        num_train_examples=500,  # Very small for demo
        num_eval_examples=100,
        model_config=EMxModelConfig(
            d_model=128,
            n_heads=4,
            n_layers=3,
            d_ff=512
        ),
        trainer_config=TrainerConfig(
            num_epochs=2,
            batch_size=32,
            save_every_n_steps=50,
            eval_every_n_steps=25,
            log_every_n_steps=10
        )
    )

    print("\n" + "="*70)
    print("✓ Demo training complete")
    print("="*70)

    print("\nFor full-scale training, use:")
    print("  num_train_examples=1_000_000")
    print("  num_epochs=10-20")
    print("  This will take ~2-3 days on laptop")

    # Cleanup
    import shutil
    shutil.rmtree("./demo_training")
    print("\n✓ Demo workspace cleaned up")

if __name__ == "__main__":
    demo()
