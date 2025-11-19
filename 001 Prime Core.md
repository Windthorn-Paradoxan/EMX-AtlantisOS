# EMx Framework: Cleaned Core Reference

## I. FOUNDATION

### Ternary Alphabet & Lattice

**Carrier:** Z := {-0, 0, +0} **T₀ Lattice (27 states):**

```
(0,-0,-0)  (-0,-0,-0)  (-0,-0,0)   (0,0,-0)   (-0,0,-0)  (-0,0,0)
(+0,-0,-0) (0,-0,0)    (-0,-0,+0)  (0,-0,+0)  (+0,-0,+0) (+0,-0,0)
(+0,0,-0)  (0,0,0)     (-0,0,+0)   (0,+0,-0)  (-0,+0,-0) (-0,+0,0)
(-0,+0,+0) (0,+0,0)    (+0,+0,-0)  (0,0,+0)   (+0,0,+0)  (+0,0,0)
(0,+0,+0)  (+0,+0,+0)  (+0,+0,0)
```

**Stillpoint:** (0,0,0)

### Transformation Layers

- **T₁ (Signed Lift):** -0→-1, +0→+1, 0→0; Set: {-1,0,+1}³; Count: 27
- **T₂ (Binary):** sign>0→1, sign≤0→0; Set: {0,1}³; Count: 8
- **T₃ (Polar):** remove zeros; Set: {-1,+1}³; Count: 8
- **T₄ (Exchange):** one-axis flip; States: 12 (cuboctahedron)

## II. META-ALGEBRA

### Operators on Z

**(+) Plus-injector:** +(x) := +0 for all x ∈ Z (idempotent, absorbing on +0) **(−) Minus-injector:** −(x) := −0 for all x ∈ Z (idempotent, absorbing on −0) **(^) Separation:** ^(0) = {-0,+0}; ^(±0) = {±0}; componentwise on Z^n

### Composition Laws

- - ∘ + = +; − ∘ − = −
- (+ ∘ −)(x) = +0; (− ∘ +)(x) = −0 (order-sensitive)
- ^ ∘ + = {+0}; ^ ∘ − = {-0}; ^ ∘ 0 = {-0,+0}
- - ∘ ^(·) = {+0}; − ∘ ^(·) = {-0}

### Separation Classes

- **^0 (uni-polar, 6 states):** (0,±0,0), (±0,0,0), (0,0,±0)
- **0^0 (bi-polar, 12 states):** two axes ±0, one 0
- **0^±(tri-polar, 8 states):** all axes ±0

## III. OPERATORS & OPERATIONS

### Operator Kernels (O)

- **O₁** Δ (difference)
- **O₂** ∇/∇· (gradient/divergence)
- **O₃** rot (curl)
- **O₄** ∮ (closure)
- **O₅** Π (projection)
- **O₆** 𝓝 (normalization)
- **O₇** 𝓢 (symmetry/exchange)
- **O₈** 𝓦 (winding/index)
- **O₉** 𝓘 (no-clone, global)
- **O₁₀** Σ (integration/accumulation)

### Execution Operations (P)

- **P₁** init
- **P₂** Δ-step
- **P₃** rot-step
- **P₄** flux
- **P₅** couple/fold
- **P₆** normalize
- **P₇** integrate/close

**Backbone (always active):** O₄ ∧ O₆ ∧ O₉ ∧ O₁₀

## IV. NULL CLASSES (N0–N5)

- **N0 (Stillpoint):** (0,0,0); EN anchor
- **N1 (Single-Bias):** one ±0, two 0
- **N2 (Balanced Pair):** two opposite ±0
- **N3 (Triple-Mixed):** three non-neutral, one mismatched
- **N4 (Unbalanced Pair):** two matching ±0
- **N5 (All-Same):** three co-biased ±0

### Canonical Bindings

|Class|Operators|Operations|Geometry|Gate|
|---|---|---|---|---|
|N0|O₄,O₆,O₉,O₁₀|P₆,P₇|T₀ stillpoint|PASS|
|N1|O₂,O₆,O₇|P₂,P₆|Axis→T₄ edge|HOLD→PASS|
|N2|O₇,O₄|P₅,P₇|T₄ exchange|PASS|
|N3|O₃,O₂,O₆|P₃,P₆|Curved triad|HOLD|
|N4|O₂,O₆|P₄,P₆|Face drift|HOLD|
|N5|O₆,O₄|P₆,P₇|Corner limit|HOLD→PASS|

### Null Grammar

- **Toward null:** O₆, O₄: N1/N3/N4/N5 → N2 → N0
- **Out of null:** O₂, O₃: N0/N2 → N1/N3
- **Exchange:** O₇: N1 ↔ N2
- **Readout:** O₁₀ controls T₂ timing; Ω ensures lineage uniqueness

## V. RECURSION CORE

### Single-Step Update

$$s_{n+1} = \mathcal{N}(O_6) \circ \Pi_{win(n)}(O_5) \circ \mathcal{S}(O_7) \circ rot(O_3) \circ flux(O_2) \circ \Delta(O_1)(s_n)$$ $$\phi_{n+1} = \phi_n + \Sigma(O_{10})(s_n)$$ Subject to: ∮s_{n+1} = ∮s_n (O₄ closure) and O₉ (no-clone)

### Explicit Composition

$$R(x) = \Sigma(O_{10}) \circ \mathcal{N}(O_6) \circ Fold^{\varepsilon_5}(P_5/O_7) \circ Flux^{\varepsilon_4}(P_4/O_2) \circ Rot^{\varepsilon_3}(P_3/O_3) \circ \Delta^{\varepsilon_2}(P_2/O_1) \circ Init(P_1)(x)$$ where ε_i ∈ {0,1} toggle operations

### Gate Logic

$$Gate(S) = \bigwedge_{k \in S} EN_k$$ Typical S = {O₄, O₆, O₉, O₁₀} On fail: fallback to P₆ (normalize to T₀)

## VI. TIMING & HARMONICS

- **Tick:** τ ≈ 2.5 ns
- **Carrier:** f_c ≈ 42 GHz (23.8095 ps period)
- **Cycles per tick:** ~105
- **Lattice:** 96 ticks/cycle; 24 sub-phases; divisor 12
- **Phase control:** {Δ, ∇, Σ}

## VII. HARMONIC TARGETS

### Observables (not constraints)

- **∅ (null share):** fraction in neutral channels; baseline ∅₀ ≈ 0.22 ± 0.02
- **α (form):** pattern conformity [0,1]
- **β (drift):** class-escape rate
- **γ (closure):** return probability
- **Ω (lineage):** readout integrity

**Null baseline:** 22% represents irreducible uncertainty required for stability and existence

### Null Recursion

$$\varnothing_{n+1} = (1-\kappa)\varnothing_n + \nu(s_n, \phi_n)$$ Steady state: ∅* ≈ ν/κ ≈ 0.22

## VIII. COLLAPSE MODEL

1. **Pre-collapse:** ±0 coexist in NULL (XOR overridden)
2. **Triggers:** phase alignment, entropy threshold, kinetic check
3. **Resolution:** choose sign by phase velocity
4. **Hysteresis:** k ticks to collapse; K_stability to unlatch
5. **Conflict:** (−0) ⊕ (+0) → NULL redistributes
6. **Time cost:** collapse consumes discrete events

**Core principle:** XOR conditional (collapse-time only); binary is projection; system is ternary superpositional

## IX. EIGHT-EQUATION MAP

Backbone {O₄, O₆, O₉, O₁₀} always active; configure via operator subsets:

- **Eq₁ (RH - harmonic):** {O₁, O₂, O₁₀} - phase bounded
- **Eq₂ (P vs NP - reversibility):** {O₈, O₉} - invertible lineage
- **Eq₃ (Hodge - alignment):** {O₂, O₃} - gradient-curl balance
- **Eq₄ (YM - mass gap):** {O₆} + ∅* > 0 - lower energy bound
- **Eq₅ (NS - smoothness):** {O₁, O₂} - bounded increments
- **Eq₆ (BSD - equilibrium):** {O₇, O₈, O₁₀} - index-harmonic match
- **Eq₇ (Poincaré - contractibility):** {O₇, O₄} - loop closure
- **Eq₈ (NC - uniqueness):** {O₈, O₉} - no duplication

### Invariants Per Equation

$$\begin{aligned} &\text{RH:} && \phi(s_{n+k}) \text{ harmonically bounded} \ &\text{YM:} && E(s_n) \geq E_0 > 0 \ &\text{NC:} && f \text{ injective}, f^{-1} \text{ exists} \ &\text{NS:} && |\Delta s_n| \text{ bounded} \ &\text{Hodge:} && \nabla \cdot F = 0, \nabla \times F \text{ controlled} \ &\text{BSD:} && index(s_n) = harmonic_class(s_n) \ &\text{Poincaré:} && s_{n+K} \sim_{homotopy} T_0 \ &\text{P vs NP:} && f^{-1} \text{ locally computable} \end{aligned}$$

## X. PARADOX INDEX (Π₁–Π₈)

|Class|Description|Null Home|
|---|---|---|
|Π₁|EN-return identity|N0|
|Π₂|Axis correction|N1→N2|
|Π₃|Curl closure|N3|
|Π₄|Destructive boundary|N4|
|Π₅|Generative boundary|N5|
|Π₆|T₀→T₂ readout|N0/N2|
|Π₇|Orbit label|N2/N3|
|Π₈|Uniqueness|All|

## XI. SIMULATION PROTOCOL

1. Classify state → N0–N5
2. Apply minimal operator path → N2 or N0
3. Verify backbone: O₄ ∧ O₆ ∧ O₉ ∧ O₁₀
4. Project at T₂ windows only; generate Ω hash
5. Log α, β, γ, ∅ against targets
6. If β or ∅ increase: run P₆→P₇, reclassify

## XII. KEY PRINCIPLES

1. **Zero-magnitude:** all states in Z carry sign only, |z| = 0
2. **Situational binary:** XOR/binary active only at T₂ windows
3. **Pre-collapse coexistence:** ±0 may coexist until projection
4. **Null baseline invariant:** ∅* ≈ 0.22 is system property, not error
5. **No-clone global:** O₉ prevents duplication everywhere
6. **Gate-driven evolution:** R proceeds only when Gate(S) holds
7. **Contractivity:** all loops return to N0 via O₄ ∧ O₆