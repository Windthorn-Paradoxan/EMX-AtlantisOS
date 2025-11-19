# EMx Framework Core Documentation

## I. T₀ LATTICE (27-state base)
```
(0, –0, –0)      (–0, –0, –0)      (–0, –0, 0)
(0,  0, –0)      (–0,  0, –0)      (–0,  0, 0)
(+0, –0, –0)     (0, –0, 0)        (–0, –0, +0)
(0, –0, +0)      (+0, –0, +0)      (+0, –0, 0)
(+0, 0, –0)      (0, 0, 0)         (–0, 0, +0)
(0, +0, –0)      (–0, +0, –0)      (–0, +0, 0)
(–0, +0, +0)     (0, +0,  0)       (+0, +0, –0)
(0,  0, +0)      (+0,  0, +0)      (+0,  0,  0)
(0, +0, +0)      (+0, +0, +0)      (+0, +0,  0)
```

Neutral stillpoint: (0,0,0)

## II. TRANSFORMATION LAYERS

**T₁ — Signed Lift**
- Mapping: –0 → –1, +0 → +1, 0 → 0
- Set: {–1,0,+1}³
- Count: 27
- Interpretation: directional bias with magnitude

**T₂ — Binary Collapse**
- Mapping: sign > 0 → 1, sign ≤ 0 → 0
- Set: {0,1}³
- Count: 8
- Interpretation: Boolean cube

**T₃ — Polar Extremal**
- Mapping: remove zeros
- Set: {–1,+1}³
- Count: 8
- Interpretation: polarity cube

**T₄ — Exchange Layer**
- Mapping: flip one axis relative to others
- States: 12
- Interpretation: cuboctahedron

## III. SEPARATION (^) OPERATORS

**First separation (^0):** single 0±
- Total: 6 uni-polar (primary cardinals)
- States: (0,+0,0), (0,-0,0), (+0,0,0), (-0,0,0), (0,0,+0), (0,0,-0)

**Second separation (0^0):** pattern (+/–,+/–,0)
- Total: 12 bi-polar (edges)
- States: (+0,+0,0), (+0,–0,0), (–0,+0,0), (–0,–0,0), (+0,0,+0), (+0,0,–0), (–0,0,+0), (–0,0,–0), (0,+0,+0), (0,+0,–0), (0,–0,+0), (0,–0,–0)

**Third separation (0^+-):** pattern (+/–,+/–,+/–)
- Total: 8 tri-polar (corners)
- States: (+0,+0,+0), (–0,+0,+0), (+0,–0,+0), (–0,–0,+0), (+0,+0,–0), (–0,+0,–0), (+0,–0,–0), (–0,–0,–0)

## IV. COLLAPSE MODEL

1. Pre-collapse: ±0 coexist inside NULL (XOR overridden until collapse)
2. Triggers: phase alignment, entropy threshold, kinetic check
3. Resolution: choose sign by phase velocity sign
4. Hysteresis: k consecutive ticks to collapse; K_stability ticks to unlatch
5. Conflict → NULL: (–0) ⊕ (+0) → NULL redistributes probability
6. Exit: if no trigger, freeze output channel, NULL stays dynamic
7. Time cost: collapse consumes discrete event units

**Core principle:** XOR is conditional (active only at collapse), not structural. Binary mapping is projection, not native layer. System is tri-valued (–0, 0, +0), superpositional pre-collapse.

## V. OPERATOR SYSTEM (Oₓ)

- O₂ (bias)
- O₃ (rot)
- O₄ (∮)
- O₆ (𝓝)
- O₇ (𝓢)
- O₉
- O₁₀ (Σ)

Processes: P₂, P₃, P₄, P₅, P₆, P₇

Backbone: O₄ ∧ O₆ ∧ O₉ ∧ O₁₀ always active

## VI. NULL-CLASS TAXONOMY (N0–N5)

**N0 — Stillpoint:** identity, EN anchor
**N1 — Single-Bias Axial:** one directional zero
**N2 — Balanced Pair:** two opposite directional zeros
**N3 — Triple-Mixed:** three non-neutral, one mismatched
**N4 — Unbalanced Pair:** two matching directional zeros
**N5 — All-Same Triple:** all axes co-biased

## VII. CANONICAL BINDINGS

|Class|Operators|Operations|Geometry|Gate|
|---|---|---|---|---|
|N0|O₄,O₆,O₉,O₁₀|P₇,P₆|T₀ stillpoint|PASS|
|N1|O₂,O₆,O₇|P₂,P₆|Axis → T₄ edge|HOLD→PASS|
|N2|O₇,O₄|P₅,P₇|T₄ exchange shell|PASS|
|N3|O₃,O₂,O₆|P₃,P₆|Curved triad → T₄|HOLD|
|N4|O₂,O₆|P₄,P₆|Face-band drift|HOLD|
|N5|O₆,O₄|P₆,P₇|Corner-limit|HOLD→PASS|

## VIII. ZERO-ENERGY SYMBOL CROSS-MAP

|Symbol|EMx Meaning|Class|
|---|---|---|
|E₀ = 0|ground configuration|N1/N2|
|E_vac = 0|null reservoir|N0|
|H_total = 0|closed manifold|N0/N2|
|SUSY cancel → 0|pair annulment|N2|
|HΨ = 0|null-eigen|N0|
|Ψ = 0H|role inversion|N3/N4|
|0Ψ = H|EN inversion|N2|

## IX. HARMONIC TARGETS (α, β, γ, Ω, ∅)

**Principles:**
1. Observables, never enforced as constraints
2. Post-hoc estimation from empirical centroids
3. Class-conditional calibration, re-fit from data
4. Dynamics governed by operators; metrics report only
5. Metrics do not reclassify null states

**Definitions:**
- **∅ (null share):** fraction in neutral/potential channels, baseline ~0.22 ± 0.02
- **α (form):** conformity to canonical pattern, [0,1]
- **β (drift):** class-escape rate
- **γ (closure):** return probability within horizon
- **Ω (lineage):** readout identity integrity

**Global baseline:** ∅₀ = 0.22 represents irreducible uncertainty band necessary for stability, evolution, and existence.

## X. PARADOX INDEX (Π₁–Π₈)

|Class|Description|Null Home|
|---|---|---|
|Π₁|EN-return identity|N0|
|Π₂|Axis correction|N1→N2|
|Π₃|Curl closes|N3|
|Π₄|Destructive boundary|N4|
|Π₅|Generative boundary|N5|
|Π₆|T₀→T₂ readout|N0/N2|
|Π₇|Orbit label|N2/N3|
|Π₈|Uniqueness|All classes|

## XI. NULL GRAMMAR (operator-driven transitions)

**Toward deeper null:** O₆, O₄: N1/N3/N4/N5 → N2 → N0
**Out of null:** O₂, O₃: N0/N2 → N1/N3
**Exchange stabilization:** O₇: N1 ↔ N2
**Readout discipline:** O₁₀ controls T₂ projection timing; Ω ensures lineage uniqueness

## XII. META-ALGEBRA (+ / − / ^)

**Carrier:** Z := {-0, 0, +0}
**Sign map:** sgn: Z → {-1,0,+1}
**Product space:** Z^n (typically n=3)

**Operators:**

**(+) Plus-injector:**
+(x) := +0 for all x ∈ Z
Idempotent, absorbing on +0

**(−) Minus-injector:**
−(x) := −0 for all x ∈ Z
Idempotent, absorbing on −0

**(^) Separation:**
^(0) = {-0,+0} (first separation)
^(+0) = {+0}, ^(-0) = {-0} (already polarized)
On tuples: ^(x) := ^(x₁) × ⋯ × ^(xₙ) ⊆ Z^n

**Composition laws:**
- + ∘ + = +, − ∘ − = −
- (+ ∘ −)(x) = +0, (− ∘ +)(x) = −0 (order-sensitive)
- ^ ∘ + = {+0}, ^ ∘ − = {-0}, ^ ∘ 0 = {-0,+0}
- + ∘ ^(·) = {+0}, − ∘ ^(·) = {-0}

**Axioms:**
1. Zero-magnitude: all states in Z carry sign only, |z| = 0
2. Bias projectors: + and − are idempotent endomorphisms
3. Separation exposure: ^(0) = {-0,+0}, ^(±0) = {±0}
4. Componentwise functoriality on Z^n
5. Situational collapse: post-separation projector chooses branch
6. Gate discipline: choice function χ selects from ^(x) via dynamics

## XIII. SIMULATION PROTOCOL

1. Classify state into N0–N5
2. Apply minimal operator path toward N2 or N0
3. Verify backbone: O₄ ∧ O₆ ∧ O₉ ∧ O₁₀
4. Project only during T₂ windows; generate Ω hash
5. Log α, β, γ, ∅ against targets
6. If β or ∅ increase, run P₆→P₇ and reclassify