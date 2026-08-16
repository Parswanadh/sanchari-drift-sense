# Drift-Sense — Demo Video Script (Team Sanchari)
Target length: ~2:30–3:00. Speakers: **Sriya** and **Padmaja**.
`[bracketed lines]` = on-screen action / what to show.

---

### 0:00–0:20 — Hook (headline number up front)

**Sriya:** "A wafer inspection tool has to land on the *exact same spot* on a chip, thousands of times a day — and when it drifts off target, every die around it looks almost identical, so it can't tell by looking. That's Applied Materials' Navigation-Error Recovery problem — a needle in a nanoscale haystack. Our classical computer-vision pipeline finds it with 100% accuracy within 3 pixels on findable sites, in about a second, on a plain CPU. Here's how."

`[Show: PDF background slide — the drift/missed-site diagram, 2 sec]`

### 0:20–0:55 — Problem + why it's hard *(Sriya continues — problem section)*

**Sriya:** "We're given two images: a small, sharp Reference — a 100x zoom of the site the tool already knows — and a bigger, noisier Search image, a 10x zoom of the same area. The reference pattern sits somewhere inside the search image, shrunk exactly 10x. Our job: find its center, (x, y). The catch is periodicity — DRAM and FinFET layouts repeat the same pattern hundreds of times in one frame, so a naive template match can lock onto the *wrong* repeat with just as much confidence as the right one."

`[Show: side-by-side reference + search image, e.g. results/success_example.png]`

### 0:55–1:40 — Our approach *(Padmaja — architecture + demo section)*

**Padmaja:** "First, our dataset generator. Since Applied Materials gives no real data, we built our own — synthetic DRAM word-line/bit-line/via arrays and FinFET fin/gate structures, with independent Poisson-and-Gaussian sensor noise on each image, SEM-style edge brightening, blur, and rotation — every choice cited against real SEM and VLSI literature in our repo. For localization, we went classical computer vision, not deep learning — because we *know* the zoom ratio is exactly 10x. Instead of a blind multi-scale search, we sweep a narrow band around that known ratio plus a small rotation range, run normalized cross-correlation, and — this is the key part — when the layout is genuinely periodic and multiple spots tie for the best match, we resolve it the same way Applied Materials defines the correct answer: pick whichever is closest to the center of the search image."

`[Show: pipeline diagram from the PPT, Slide 4]`

### 1:40–2:15 — Live demo *(Padmaja continues)*

**Padmaja:** "Let's run it live."

`[Terminal — run on screen:]`
```bash
python dataset_generator.py --architecture dram --num-pairs 1 --out-dir data/demo --seed 7
python localize.py --reference data/demo/images/pair_0000_reference.png \
                    --search    data/demo/images/pair_0000_search.png
```
`[Let the JSON output print: {"x": ..., "y": ..., "score": ..., "time_sec": ...}]`

**Padmaja:** "One command, one JSON line with the predicted center — about a second and a quarter on a CPU. No GPU, no training required."

### 2:15–2:50 — Results, honestly *(Sriya — results + close section)*

**Sriya:** "Across 30 randomized test pairs: 86.7% land within 3 pixels of ground truth overall. On sites with any locally-distinguishing feature, we hit 100% within 3 pixels, mean error under half a pixel. And we're honest about where it fails — on purely periodic, feature-less regions, the algorithm correctly *detects* the ambiguity but can't beat what's fundamentally a coin flip between identical repeats. We show that failure case explicitly, with the root cause documented, plus a bonus extension to RGB optical-microscope images."

`[Show: results/failure_example.png with the green/red markers]`

### 2:50–3:00 — Close

**Sriya:** "Everything — generator, inference script, citations, results — is in our public repo. Thanks for watching — we're Team Sanchari, thinking in a systems way."

`[Show: GitHub URL — github.com/Parswanadh/sanchari-drift-sense]`

---

## Notes for filming
- Record the terminal demo *for real* — don't fake the output, it genuinely runs in ~1.2s.
- Swap speaker lines freely to match who's more comfortable reading which part.
- If time-constrained, cut the RGB bonus line (2:45) first — everything else is core-rubric content.
