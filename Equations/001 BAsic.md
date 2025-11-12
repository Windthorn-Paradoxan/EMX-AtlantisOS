
# 1) Operators (O) — kernels

Let (O_k) be kernels, invoked by operations (P_k), joined at EN.

- **O₁** Δ    
- **O₂** ∇ / ∇·    
- **O₃** rot    
- **O₄** ∮    
- **O₅** Π    
- **O₆** 𝓝    
- **O₇** 𝓢    
- **O₈** 𝓦    
- **O₉** 𝓘 (global; no-clone everywhere)    
- **O₁₀** Σ
    

---

# 2) Operations (P) — execution of O in domain (d)

$$
[  
P_{k,d}(x_d)=O_k(x_d)  
]
$$
- **P₁** init    
- **P₂** Δ    
- **P₃** rot    
- **P₄** flux    
- **P₅** couple    
- **P₆** 𝓝    
- **P₇** ∮
    

--
# 3) Equivalence Nodes (EN)

Unify domains:
$$
[  
\mathrm{EN}_k:\ P_{k,t}=P_{k,g}=P_{k,p}=O_k  
]
$$
---

# 4) Transitions

- (T_0 \xrightarrow{O_1/O_6} T_1)    
- (T_1 \xrightarrow{O_5} T_3)    
- (T_1 \xrightarrow{O_5\circ H} T_2)    
- (T_3 \xleftrightarrow{O_7} T_4)    
- (* \xrightarrow{O_6} T_0)
    

---

# 5) Gates

Gate passes iff all EN in (S) hold:
$$
[  
\mathrm{Gate}(S)=\bigwedge_{k\in S}\mathrm{EN}_k  ]
$$
Common $(S = {O_4,O_6,O_9,O_{10}})$.

---
# 6) Timing / Harmonics

- Tick: (\tau\approx2.5,\mathrm{ns})    
- Carrier: (f_c\approx42,\mathrm{GHz})    
- ~105 cycles per tick    
- 96-step lattice; 24 sub-phases; divisor 12    
- Σ handles phase; {Δ,∇,Σ} harmonic control
    
---
# 7) Flow

Four-way vector flow (in/out × fwd/back), enforced by 𝓢 and gated.

---
# 8) Binary I/O (XOR-free)

Encode:
- Hard: (−1,0)→0, +1→1    
- Soft: gradient as needed    

Decode:  
0→−0 (contextual 0/−0), 1→+0; return via 𝓝 → (T_0).

---
# 9) Invariants

- (|T_0|=27) complete    
- Stillpoint + symmetry pairs    
- Closed under ( {O_k} )    
- 𝓘 global (no-clone)    
- EN coherence at gates    

---

# 10) Eight configs

Backbone always on: ({O_4,O_6,O_9,O_{10}}\Rightarrow{P_6,P_7}).

- **Eq₁:** {O₁,O₂,O₁₀}    
- **Eq₂:** {O₈,O₉}    
- **Eq₃:** {O₂,O₃}    
- **Eq₄:** {O₆}    
- **Eq₅:** {O₁,O₂}    
- **Eq₆:** {O₇,O₈,O₁₀}    
- **Eq₇:** {O₇}    
- **Eq₈:** {O₈,O₉}    

All evaluated through Gate(S).

---

# 11) Minimal Stepper

1. **P₁** init from (T_0)    
2. **P₂/P₄/P₃** as configured    
3. Gate(S): if fail → **P₆**, else continue    
4. **P₅** (optional exchange)    
5. **P₇** close; log Σ    
6. **P₆** return to (T_0); repeat (96/24 cycle)    

---
# 12) NULL

Neutral fixed point; all (O_k) commute with projection via 𝓝; never cloned (𝓘); crossed only under Gate(S).

---
