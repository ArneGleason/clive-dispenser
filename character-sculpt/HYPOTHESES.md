# Clive · Contact, Garment Topology & Anatomical Logic Hypotheses

**Live back-and-forth thread:** [GitHub Issue #3](https://github.com/ArneGleason/clive-dispenser/issues/3) · **Reference turnaround:** [`references/clive-turnaround.png`](references/clive-turnaround.png) · **Experiment log:** [`LOG.md`](LOG.md)

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

Any turn can pick one of these branches (or combine two) and compare the result honestly against the current comparison model in `tools/review_views.py`:

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
