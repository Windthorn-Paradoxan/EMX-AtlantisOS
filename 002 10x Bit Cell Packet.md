# EMx Carrier Packet Specification

## I. PACKET STRUCTURE (10-bit transitional state)

```
W₃ W₂ W₁ W₀  ||  H₁ H₀  ||  E₃ E₂ E₁ E₀
  what/where     how/why      echo/copy
```

- **W (4 bits):** geometric locus/direction in polarity lattice
- **H (2 bits):** operator selection
- **E (4 bits):** echo storage & integrity (mirrors W, Gray-coded, or with parity)
- **|| (double bar):** carrier window - rotating read/write aperture

**Key property:** Bits flip **in motion** within the || window; not static endpoints

## II. GEOMETRY MAPPING (W₀–W₃)

### Option A: T₄ Cuboctahedron (recommended)

- 12 directions: one-axis-inverted vectors
- Permutations of (–1,+1,+1) and (+1,–1,–1)
- Movement along exchange shell
- 16 codes allow sentinels (idle, center, error)

### Option B: T₃ Polar Cube

- 8 corners: pure ± vectors (±1,±1,±1)
- Simpler, fewer directions

**Function:** W selects vector target in field (spatial expression of EMx state)

## III. OPERATOR ENCODING (H₀–H₁)

2 bits map to four core XOR-free actions:

- **00 = Lift:** –0→–1, 0→0, +0→+1 (bias → sign)
- **01 = Exchange:** flip one axis sign (motion operator, T₄ shell)
- **10 = Collapse:** sign>0→1, sign≤0→0 (to binary at I/O only)
- **11 = Normalize:** –1→–0, +1→+0, 0→0 (return to T₀)

**Function:** Defines active equation phase and transformation between layers

## IV. ECHO MECHANISM (E₀–E₃)

Default configurations:

- **Mirror W:** direct copy (No-Clone-safe persistence)
- **Gray-coded W:** one-bit change per step (detects motion mid-write)
- **With parity:** 1 bit reserved for integrity/epoch check

**Function:** Enforces No-Cloning, topological closure, observer consistency

## V. UPDATE RULE (per axis)

State ∈ {–1, –0, 0, +0, +1} with operator `op`:

```
Lift:       –0→–1, 0→0, +0→+1
Exchange:   flip axis that differs from sign of other two
Collapse:   {–1,–0,0}→0, {+0,+1}→1
Normalize:  –1→–0, +1→+0, 0→0
```

**Resolution by bias & energy, not XOR exclusivity**

## VI. PACKET CYCLE (one spin)

1. **Binary in** → decode W (direction) & H (operator)
2. **Lift** (if needed) → place state on T₁
3. **Exchange** → drive motion on T₄ shell toward W target
4. **Normalize** (field handoff) or **Collapse** (binary I/O only)
5. **Echo** → write E at storage phase; verify integrity

### Layer Flow

```
Binary input → Lift → Signed lattice (T₁)
                         ↓
                    Exchange motion (T₄ shell)
                         ↓
                  Normalize / Collapse
                         ↓
                    Binary output (T₂)
```

Mid-motion samples from T₃–T₄; normalization returns to T₀ before next cycle

## VII. ERROR HANDLING

- **Desync:** E ≠ W after full rotation → flag "in-flight", no commit
- **Ambiguity:** multiple zero axes under Exchange → Lift first
- **Stall:** no state change over N windows → force Normalize

## VIII. CORRESPONDENCE TO EMX FRAMEWORK

### Logical Mapping

|Packet|EMx Element|Function|
|---|---|---|
|W₀–W₃|T₀–T₄ states|Geometric locus, field direction ∇geoΨ⁽ⁿ⁾|
|H₀–H₁|O₆,O₇ (Lift/Exchange)|Loop operator, equation phase|
|E₀–E₃|O₉ (No-Clone)|Topological closure, observer conservation|

### Dynamic Correspondence

|Equation Term|Carrier Behavior|
|---|---|
|∂ₜ(EMx⁽ⁿ⁾)|Bit flipping within \| window|
|∮ₗₒₒₚ(∇geoΨ – PₙᵤₗₗΨ)·dℓ|W/E rotation through T₄ exchange|
|Ωₛᵧₘ(CFG₀)|H-bit operator choice|
|𝒩[Φ]|Normalize/collapse to equilibrium|

**One complete packet spin = one iteration of Φₙ₊₁ = 𝒩[…]**

### Table Synthesis During Cycle

- **T₀ (neutral):** normalization target
- **T₁ (signed lift):** post-Lift state
- **T₂ (binary):** Collapse output at I/O only
- **T₃ (polar):** mid-motion sampling
- **T₄ (exchange):** active movement shell

All five tables accessed dynamically; T₂ active only at designated windows

## IX. KEY PROPERTIES

1. **Motion is observable:** bits flip in-flight within carrier window
2. **XOR-free evolution:** resolution via bias/energy, not Boolean exclusivity
3. **4–2–4 structure:** where/what | how/why | proof/echo
4. **Situational binary:** Collapse occurs only at I/O boundaries
5. **T₄ enables smooth flow:** 12 directions vs 8 corners for continuous motion
6. **No-Clone enforced:** E-field verification prevents duplication

## X. IMPLEMENTATION SUMMARY

**10-cell carrier:** W(4)|H(2)|E(4)

- Binary unfolds to geometric direction (W)
- Applies field operator (H)
- Writes Gray/echo copy (E)
- || window rotates
- Bits flip in motion via Lift/Exchange/Normalize
- Collapse only at binary I/O boundaries

**Complete packet traversal implements one discrete EMx recursion step**