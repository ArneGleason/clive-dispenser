# A refinement cycle

1. **Establish the evidence.** Inventory the supplied images, view directions, expression, pose, and any disagreement between them. Mark each image as owner-supplied, model render, or generated hypothesis. With a single image, write down what is hidden. If a generator supplies rotations, hold pose, proportions, expression, and camera projection consistent. Check near-side/far-side swaps and invented features against the supplied view. Retain the prompt, model/version if available, and selected outputs. An inferred back stays labeled even when it looks convincing.
2. **Choose a method for the question.** For an editable silhouette or a continuous eyelid-to-cheek transition, try a sparse subdivision cage. For local volume and crease work, try multiresolution sculpting or digital clay. For a fresh base, try image-to-3D using the same references and compare the raw mesh before cleanup. A hybrid run might reconstruct the base, retopologize the face, then sculpt. Record manual work and externally generated inputs. Isolate the change being tested when comparing models or settings.
3. **Orbit the parent.** Align front, side, and rear for proportions. Slowly rotate from high to low on both sides, pausing where the character stops reading. Inspect silhouette, cross-sections, overlaps, negative spaces, contact, and expression. Use flat clay first. Use color later for paint and material judgments. Choose one region and one or two observable outcomes.
4. **Add volume.** Identify which mass is missing and where it should connect. Push the coarse cage or sculpt a broad form first. For Clive, a cheek lift should continue into the lower eyelid as the head rotates. Save a temporary state and recheck the opposite side. Record the effect and at least one view that could disprove it.
5. **Subtract volume.** Orbit again looking for excess, buried edges, or crowded gaps. Carve a plane, ease an exaggerated bulge, thin a fold, or remove a repeated detail. A subtraction should describe the form around it. A narrow groove all the way around a cheek can make it look pasted on. Undo edits that weaken the gesture. Either pass may have no justified change. Record that judgment.
6. **Refine at the appropriate scale.** Inspect at intended print size. If the profile is wrong, return to the broad form before adding detail. Use finer levels for eyelid thickness, lip turns, cloth compression, and changing lock widths. Rotate while shaping. A fixed contact sheet is a record of the inspection, not its full extent.
7. **Compare and record.** Match the parent’s camera, scale, lighting, and pose. Show both the most improved angle and the least convincing angle. Record improved, unchanged, regressed, or uncertain for likeness, off-axis volume, expression, and small-scale legibility. Keep print checks and user judgments separate. Save the editable source and tool versions. Update the catalog even for a discarded experiment.

## Matched review views

The bundled Blender script renders nine neutral-clay views and a reusable camera frame. Tested with Blender 5.2.1. The figure should be upright along Z, facing negative Y, with only the subject and its plinth visible as meshes. For another tool or differently oriented model, export a review copy into Blender or match the same views in the native tool. If the figure is moved, align the review copies before comparing them.

From the repo root, run these commands with fresh output directory names:

```sh
blender -b experiments/2026-11-21-subdivision-study/Clive-SubD.blend --python-exit-code 1 -P character-sculpt/tools/review_views.py -- review/parent
blender -b experiments/2026-11-21-multires-refinement/Clive-Refined.blend --python-exit-code 1 -P character-sculpt/tools/review_views.py -- review/candidate --frame-from review/parent/frame.json
```

The second run reuses the parent’s framing so proportion changes stay visible. For unfamiliar assets, inspect a render for clipping, extra scene geometry, or an incorrect front axis.

## When only one image exists

Start with silhouette, eye line, chin, shoulder width, hands, ground contact, and any overlap that tells you which surface is in front. Build a rough depth hypothesis and render it from the original camera. If the camera is perspective, use that perspective for this overlay; reserve orthographic views for cross-run comparisons.

For generated views, first request a modest camera turn with pose and expression held fixed. Compare identifiable landmarks and which features become newly visible. Then try a profile or back. A plausible generated back is one candidate. When two plausible backs would lead to materially different meshes, keep both hypotheses or ask the owner which to pursue. For image-to-3D trials, record exactly which generated views went into reconstruction and retain an original-view-only run when testing whether the extra views helped.
