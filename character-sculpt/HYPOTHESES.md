# Clive · Contact, Garment Topology & Anatomical Logic Hypotheses

**Live back-and-forth thread:** [GitHub Issue #3](https://github.com/ArneGleason/clive-dispenser/issues/3) · **Reference turnaround:** [`references/clive-turnaround.png`](references/clive-turnaround.png) · **Experiment log:** [`LOG.md`](LOG.md)

See the [field guide](FIELD-GUIDE.md) for findings that held up in comparisons and the conditions where they apply.

## 1. Owner critique after the 2026-11-21 pose & face pass

Reviewing [`2026-11-21-turnaround-pose-face`](../experiments/2026-11-21-turnaround-pose-face/README.md) ([PR #2](https://github.com/ArneGleason/clive-dispenser/pull/2)), Arne noted clear directional improvement ("much improvement… getting much better") while calling out two structural problems that affect both that candidate and earlier Blender runs:

1. **Unrecognizable trouser topology.** Clive's lowered pants do not follow real trouser topology — they were built as two separate stacked-ring leg tubes plus an independent waistband torus and an inner fill ellipsoid, rather than a single continuous bifurcated garment pulled down around the knees/ankles and stretched horizontally across the front by his hands.
2. **Blind 3D object interpenetration (missing physical response).** Neighboring volumes push straight through each other instead of sitting on, wrapping around, or compressing one another:
   - **Cap ↔ Hair (and brows/ears):** Hair curls push through the cap's lower rim without being compressed beneath it, and the cap rim ignores the hair volume beneath it rather than conforming softly over the brow/nape mass.
   - **Trousers ↔ Thighs / Seat / Hands / Boots:** Separate overlapping primitives clip into one another instead of a continuous cloth band resting against the bare hips, indenting under gripping knuckles, and pooling with gravity over the boot collars.
   - **Smock ↔ Sleeves / Seat:** Sleeves plug into the torso side as separate tubes and the rear hem clips/floats over the seat rather than stretching continuously across a hunched back and rolling smoothly up over the upper buttocks.
   - **Hands ↔ Fingers & Facial Hair ↔ Skin:** Separate finger tubes meet a rounded forearm cap, and eyebrows/moustache/beard locks sit on the head surface rather than emerging seamlessly from the underlying anatomy.

## 2. Arne's framing: "Goals from two directions"

Every procedural and box-modeled attempt so far worked primarily **outside-in** — assembling independent primitives to match the 2D silhouette. Arne proposed constraining the sculpt **from two directions simultaneously**:

- **Outside-in (likeness & appeal):** Fit the approved front, side, and back turnaround ([`references/clive-turnaround.png`](references/clive-turnaround.png)) — proportions, mischievous expression, ceramic charm.
- **Inside-out (anatomical & garment logic):** Start from **known-good humanoid anatomical meshes and real garment topology** (so shoulders, spine, pelvis, thighs, articulated hands, bifurcated trousers, continuous smock, and fitted cap all obey coherent structural logic) and deform/stylize them to meet the turnaround silhouette.

---

## 3. Competing hypotheses to test (handoff notes for Fable 2 & future agents)

Any turn can pick one of these branches (or combine two) and compare the result honestly against its chosen starting model in `tools/review_views.py`:

### Hypothesis A · Humanoid reference base mesh + pose-first, dress-second
- **Method:** Start from an open-source stylized humanoid base mesh (for example, Blender Studio's CC0 Human Base Meshes bundle — stylized male body, head, hands — or an articulated all-quad mannequin with proper craniofacial loops, shoulders, pelvis, thighs, knees, and 5-finger hands). Stylize its proportions to Clive (large head ~1:2.2 total height, stocky torso/arms, plump cheeks/nose/hands), rig/pose it into the exact bent-over mooning pose first, and only then build clothing and hair *onto* the posed body.
- **Why it may win:** Solves continuous body anatomy (neck, hunched shoulders, bare seat flowing smoothly into thighs, palms flowing into gripping fingers) by construction before any garment touches it.
- **Watch-out / failure mode:** Humanoid base meshes can look stiff or overly realistic ("old man in a costume") if facial and hand caricaturing isn't pushed boldly enough early on.

### Hypothesis B · Real garment topology + Blender Cloth / Shrinkwrap contact
- **Method:** Build clothing from real sewing/garment patterns rather than stacked tubes, and let Blender modifiers/physics resolve contact:
  - **Trousers:** Model one continuous **bifurcated trouser mesh** (single waist loop, fly, crotch gusset, two leg tubes) positioned up on the posed mannequin's legs. Pin the front waistband vertices to Clive's gripping fingers, set the posed legs, seat, and boots as **Collision** objects, and run a short **Blender Cloth simulation** (e.g., 30–50 frames) to drop and bunch the pants naturally onto the boot collars. Freeze the best frame, add `Solidify` for ceramic wall thickness, and finish folds in Multires.
  - **Smock:** Model one continuous tunic-with-sleeves mesh (sleeves extruded from the torso armscyes, not separate plugged cylinders), drape it over the hunched torso/arms with the rear hem pinned upward to the turnaround arch so diagonal back folds form physically from tension.
  - **Cap ↔ Hair (bidirectional contact):** Either drape/shrinkwrap the cap's inner shell *over* the hair mass (then solidify outward) so the cap visibly rides over the hair, **or** use the cap's inner brim as a physical collision/compression boundary (`Shrinkwrap` / `BVHTree` clamp) that flattens hair inward under the brim so curls swell and bloom only once clear of the rim.
- **Why it may win:** Directly answers Arne's two biggest critiques — recognizable pants topology and real physical contact/compression — without requiring manual sculpting of every cloth fold.
- **Watch-out / failure mode:** Default cloth sims can produce thin, paper-like crinkles rather than chunky glazed-ceramic folds; use high bending stiffness, coarse quad density (~2–3 mm), pressure/solidify thickness, and a light ceramic smoothing pass.

### Hypothesis C · Unified ceramic clay fusion (voxel-remesh connected assemblies + contact creases)
- **Method:** Follow a traditional collectible-figurine sculpting pipeline: block out connected regions cleanly, **fuse** each logical ceramic mass (e.g., entire temple + nape hair collar; forearm + palm + fingers; head + ears + brow ridges) via voxel remesh or boolean union, smooth out hard interpenetration edges, and carve intentional ceramic contact creases where cloth meets skin or hair meets hat brim.
- **Why it may win:** Real slip-cast glazed ceramic (like `clive-turnaround.png`) has soft fillets and pooled-glaze valleys at every contact seam rather than sharp knife-edge intersections between independent solids.
- **Watch-out / failure mode:** Destructive remeshing loses coarse cage editability unless the pre-remesh editable cage objects are preserved in a hidden backup collection or rebuilt cleanly by script.

### Hypothesis D · Multiview Image-to-3D reconstruction + anatomical/garment cleanup hybrid
- **Method:** Run the three clean views from `references/clive-turnaround.png` through a multiview image-to-3D model (e.g., Hunyuan3D 2.x MV, Tripo, Meshy, Trellis, Rodin), inspect and log the **raw mesh** in `review_views.py` first (per `WORKFLOW.md`), then retopologize/sculpt the face, wink, hands, and crisp garment boundaries in Blender — or use the raw mesh as a 3D spatial shrinkwrap guide while keeping clean anatomical/garment cages from Hypotheses A/B.
- **Why it may win:** Captures holistic ceramic charm, silhouette harmony, and coherent bunched trouser drapery that procedural geometry struggles to invent from scratch.
- **Watch-out / failure mode:** Image-to-3D raw outputs often bake paint into blobby geometry around eyelids, teeth, fingers, and tucked undercuts; requires disciplined raw-vs-cleaned comparison.

---

## 4. Specific experiments I wanted to try next (untested ideas from the `poseface` turn)

1. **Automated `BVHTree` contact-compression pass for Blender scripts:** Even inside a lightweight reproducible script (`build_clive.py`), Blender's `mathutils.bvhtree.BVHTree.FromObject()` can resolve contact between neighboring meshes cleanly:
   - Clamp/compress `Hair` vertices smoothly inward wherever they come within `0.5 mm` of the `Cap` inner surface, adding a subtle outward bloom just below the brim line (`z = brim_z - 1..3 mm`).
   - Indent `Trousers` / `Waistband` vertices directly along the `Finger` & `Thumb` contact normals while raising a gentle pinched fabric ridge beside the knuckles.
   - Project the inner hem loop of `Smock` strictly `0.25 mm` *outside* the `Seat` surface so the rolled hem hugs the bare buttocks tautly with zero gap and zero clipping.
2. **40-frame headless Cloth trouser drop test:** Test whether dropping a single coarse bifurcated pants pattern over posed collider legs in headless Blender (`blender -b`) yields genuinely recognizable bunched trousers in under a minute.
3. **Single continuous sculpted hair collar:** Replace the 12 individual swept behind-ear/nape curl tubes in `Clive-PoseFace.blend` with one voxel-fused, smoothed, and groove-carved ceramic hair collar tucked cleanly beneath the compressed cap rim.
4. **Blended facial-hair roots + subtle head attitude:** Seat eyebrow and moustache roots smoothly into the brow ridge and cheek plane (instead of sharp tube intersections) and test a slight `~3°` playful head tilt toward the open eye to remove residual CAD symmetry.

---

## 5. Verification checklist (how to tell whether a new turn solved this)

Compare against the baseline in `character-sculpt/tools/review_views.py` (matched neutral clay, same `frame.json`) plus close-up crops on four disproof tests:

1. **Trouser readability test (`front`, `front_low`, `rear_low`, `rear_high`):** Can you trace one continuous pair of pulled-down pants — waistband rim → front fly/crotch → two gathered legs → boot tops — without seeing stacked donuts, detached thigh cylinders, or skin bleeding between the legs?
2. **Hat-over-hair contact test (`side`, `rear_high`, `front_high`, close-up ear/brim):** Does hair clearly tuck *under* the cap brim (compressed at the rim, blooming below it) or does the cap visibly conform over the hair, with zero curls poking through the hat wall?
3. **Hand-and-cloth compression test (`front_low`, close-up hands):** Do palm and fingers read as one continuous articulated hand pressing into and pulling on a continuous waistband lip?
4. **Unpainted clay charm test (`front`, `wink_side`, `face_front` clay):** Does Clive still read immediately as this specific mischievous winking ceramic gnome in flat matte clay at ~108 mm print scale?

---

## 6. Results so far

| Hypothesis | Turn | What happened |
|---|---|---|
| C · unified ceramic fusion | [2026-11-21 fused clay](../experiments/2026-11-21-fused-clay-sdf/README.md) | Taken to its limit: the whole figure is one signed-distance surface, so nothing can interpenetrate and every seam is a soft fillet. Passes checklist tests 1 (trousers) and 3 (hands) in [`Comparison-Contact-Clay.jpg`](../experiments/2026-11-21-fused-clay-sdf/Comparison-Contact-Clay.jpg); test 2 (cap over hair) passes on contact but the curls are small; test 4 (clay charm) is mixed, better as a whole figure and softer in the face. The watch-out was right: the editable cage is gone, replaced by a script. |
| B · real garment topology | same turn, partly | Challenged, not tested. Building the trousers from garment *parts* (waistband loop, fly, seat seam, two legs) was enough to make them read; no cloth simulation was run. A simulation might still give better folds and real compression. The contact here is a fillet, not physics. |
| A · humanoid base mesh | none | Untested. The fused turn's side view (crouched legs, body out of scale with the head) is the kind of error a posed anatomical base would catch. |
| D · image-to-3D | none | Untested; it needs model weights or an outside service. |

Arne's verdict on the fused-clay turn and the shape-language critique that followed are in section 7.

---

## 7. Owner critique after the fused-clay turn: shape language

**2026-11-21 (Arne).** On the fused-clay turn: it "looked like it tried harder, made some mistakes that it couldn't fix." On aesthetics he preferred Neon's turn, [turnaround pose & continuous face](../experiments/2026-11-21-turnaround-pose-face/README.md) (`Clive-PoseFace.blend`). His main point applies to every turn so far, and is written up in full in [`subjects/clive.md`](subjects/clive.md#shape-language--owner-guidance-2026-11-21):

- The reference has **shape character** that no model has captured. His example is the cap rim: it "isn't just like a … donut." It curves down and back up, conforming to Clive's head and also defining it, and the wrinkles that follow up the cap make good curve lines as pure composition. The beard does the same.
- The generated models' curves follow "pretty much a straight line on one of the axes" and do not consider all three dimensions.
- The sheet is three image-generated views, each made to look good on its own and probably not coherent with the others. Whoever sculpts has to **interpret it and overlay a consistent aesthetic of their own**: heuristics, guidance, formulas, applied over the entire shape.
- Each element should carry a **caricature of its physical material**: the cap as worn cloth or felt, the boots as stiff leather, the skin as a coherent rounded organic shape, the hair stylised and sculptural in the way ancient Greek and Roman sculptors carved hair.
- **Starting point:** the next contributor looks through all the saved models and decides for itself which is the better starter. There is no fixed comparison model any more.

### Where the fused-clay turn falls short of this, in its own code

Useful if you start from [`sculpt_clive.py`](../experiments/2026-11-21-fused-clay-sdf/sculpt_clive.py), and a caution if you do not:

- The cap rim is literally a tilted torus with a small sine wobble (`cap`, the `brim` term). It is a ring.
- The cap folds are a sine of the distance along the spine. They are bands round an axis, not lines that spiral up into the hook.
- Each beard lock is a straight interpolation from a start point to an end point with a sideways sine added in X only. Nothing bends in depth.
- The hair is two rows of near-identical ringlets. No hierarchy, no grooves, no direction.
- The boots are smooth-unioned capsules. Nothing about them says leather.

### Approaches worth testing

- **E · Draw the lines first.** Before adding any volume, author the main lines as explicit 3D curves: the rim, each cap fold, each beard and hair lock. Check each one in front, side and overhead projection against the rules in the brief. Then build volume along them with a profile that changes along the length. This works with a subdivision cage, with curve sweeps, or with distance fields.
- **F · One fold vocabulary per material.** Give felt, leather, cloth and hair each their own small set of fold or lock shapes and use nothing else on that material.
- **G · Carved hair.** Build hair as a hierarchy: a few primary masses, then ribbon-like locks with a flattened section, then two or three engraved grooves per lock, with ends rolled into volutes and crisp V-shaped valleys between locks.
- **H · Resolve the sheet's contradictions on purpose.** List where the three views disagree (rim height at the temple, cap depth against width, how far the beard projects) and write down which reading you chose and why.

### How to tell whether it worked

Add these to the checklist in section 5:

5. **Straight-line test (`front`, `side`, `overhead`):** no major edge, fold or lock projects to a straight line or a plain circle in any of the three.
6. **Line render:** a silhouette-and-crease render with no shading should already look like a pleasing drawing of Clive.
7. **Material blind test:** grey clay crops of the cap, a boot, the beard and a cheek can each be identified by material from shape alone.
8. **Rim test (`front`, `side`, `rear`, `overhead`):** the cap edge reads as one continuous curve that rises over the brow, falls over the temples and behind the ears, and settles at the nape.
