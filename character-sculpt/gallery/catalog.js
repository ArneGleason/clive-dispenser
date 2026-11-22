const studies = [
  {
    "id": "original",
    "title": "Original dispenser",
    "date": "October 2026",
    "method": "Mechanical prototype",
    "change": "The first Clive paired a procedural figure with a head lever, hopper, and sliding candy tray.",
    "finding": "Virtual assembly and motion checks established a mechanical starting point. A physical print is still pending.",
    "path": "README.md",
    "images": [
      [
        "../../renders/hero_closed.png",
        "Assembled dispenser"
      ],
      [
        "../../renders/hero_open.png",
        "Dispensing position"
      ],
      [
        "../../renders/cutaway_open.png",
        "Internal mechanism"
      ]
    ]
  },
  {
    "id": "assembled",
    "title": "Assembled sculpt",
    "date": "November 21, 2026",
    "method": "Primitive modeling",
    "change": "Rounded forms established a static figure with a wink, a folded cap, and lowered trousers. The model was built from a written description.",
    "finding": "Arne found the likeness too distant. This run gives later experiments a description-only baseline.",
    "path": "experiments/2026-11-21-blender-sculpt",
    "images": [
      [
        "images/assembly.jpg",
        "Front three-quarter"
      ],
      [
        "images/assembly-rear.jpg",
        "Rear three-quarter"
      ]
    ]
  },
  {
    "id": "subdivision",
    "title": "Subdivision study",
    "date": "November 21, 2026",
    "method": "Box modeling",
    "change": "The turnaround guided the forward lean and waistband grip. Editable loops shaped the eyelids, nose, and grin.",
    "finding": "The silhouette improved. The cheek, wink, and moustache still read as separate forms, especially from below.",
    "path": "experiments/2026-11-21-subdivision-study",
    "images": [
      [
        "images/subd-front.jpg",
        "Front elevation"
      ],
      [
        "../../experiments/2026-11-21-subdivision-study/Turnaround.jpg",
        "Three-view turnaround"
      ],
      [
        "images/cage.jpg",
        "Facial control cage"
      ]
    ]
  },
  {
    "id": "multires",
    "title": "Multires refinement",
    "date": "November 21, 2026",
    "method": "Multiresolution sculpting",
    "change": "Two sculpt levels built up the cheek, collar, and cloth folds. Oblique views exposed a gap between the hands and waistband, which this pass reduced.",
    "finding": "Arne felt the sculpt was heading in the right direction. The next experiment is to carry the cheek into the winking eyelid, then soften the ridge beneath the moustache.",
    "path": "experiments/2026-11-21-multires-refinement",
    "images": [
      [
        "images/refined.jpg",
        "Studio portrait"
      ],
      [
        "images/portrait.jpg",
        "Face detail"
      ],
      [
        "images/high-rear.jpg",
        "Elevated rear view"
      ],
      [
        "../../experiments/2026-11-21-multires-refinement/Angles.jpg",
        "Six-angle inspection"
      ],
      [
        "../comparison.jpg",
        "Parent and candidate in matching clay"
      ]
    ]
  },
  {
    "id": "poseface",
    "title": "Turnaround pose & continuous face",
    "date": "November 21, 2026",
    "method": "Neon · Continuous quad Multires + SDF projection",
    "change": "Overlaying the parent onto the approved turnaround exposed a 9–10 mm head/hand lean offset and isolated cheek inset seams. Rebuilt with a continuous Multires L3 quad face, bulbous strawberry nose, arched smile-wink, sculpted iris for unpainted clay, and vertical arms gripping a unified trouser waistband.",
    "finding": "Front, side, and low three-quarter likeness, expression, and hand-to-waistband solidity improved substantially. Elevated rear oblique views still show segmented behind-ear nape tubes and a recessed hip-flank step; owner verdict pending.",
    "path": "experiments/2026-11-21-turnaround-pose-face",
    "images": [
      [
        "../../experiments/2026-11-21-turnaround-pose-face/Studio-Hero.jpg",
        "Studio portrait"
      ],
      [
        "../../experiments/2026-11-21-turnaround-pose-face/Face-Portrait.jpg",
        "Face detail"
      ],
      [
        "../../experiments/2026-11-21-turnaround-pose-face/Comparison-Face-Clay.jpg",
        "Matched clay face comparison (parent left, candidate right)"
      ],
      [
        "../../experiments/2026-11-21-turnaround-pose-face/Rear-High.jpg",
        "Elevated rear view (least convincing angle)"
      ],
      [
        "../../experiments/2026-11-21-turnaround-pose-face/Angles.jpg",
        "Six-angle inspection"
      ],
      [
        "../../experiments/2026-11-21-turnaround-pose-face/Comparison-Clay.jpg",
        "Matched parent and candidate clay views (front, low 3/4, side, high rear)"
      ]
    ]
  },
  {
    "id": "fusedclay",
    "title": "One fused clay surface",
    "date": "November 21, 2026",
    "method": "Fable 2 · Signed-distance sculpt, meshed once",
    "change": "Both earlier models read as a kit of parts and as a slender man in a costume. This turn rebuilt Clive as a single implicit surface at the turnaround's chunky proportions: every mass melts into its neighbour through a soft glaze-like fillet, and the trousers are made of garment parts (waistband loop, fly, seat seam, two gathered legs).",
    "finding": "Three-quarter and rear views, trousers and hands improved most. The pure side view holds up least (body oversized against the head, stiff cap hook, crouched legs), and the face is softer front-on than the previous turn's. Arne (2026-11-21): it tried harder but made mistakes it couldn’t fix; he preferred the aesthetic of Neon’s turn 4 (pose & continuous face) and wants the sheet’s shape language and material character next.",
    "path": "experiments/2026-11-21-fused-clay-sdf",
    "images": [
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Studio-Hero.jpg",
        "Painted studio render"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Turnaround-vs-Reference.jpg",
        "Approved turnaround above, this turn below"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Comparison-Clay.jpg",
        "Matched clay: parent, previous turn, this turn (most improved to least convincing)"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Comparison-Face-Clay.jpg",
        "Matched clay face comparison"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Comparison-Contact-Clay.jpg",
        "Matched clay contact tests: trousers, hands, cap rim"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Studio-Rear.jpg",
        "Painted rear three-quarter"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Least-Convincing-Side.jpg",
        "Least convincing angle: side view against the sheet"
      ],
      [
        "../../experiments/2026-11-21-fused-clay-sdf/Angles.jpg",
        "Nine clay review angles"
      ]
    ]
  },
  {
    "id": "feltcarved",
    "title": "Felt and carved hair",
    "date": "November 21, 2026",
    "method": "GPT-6.2 Sol (extra high) · Codex desktop · Blender 5.2.1",
    "change": "Started from Neon’s PoseFace. A flared felt brim turns over the brows and ears, diagonal folds climb toward the hook, and carved locks swing back under the chin. Buckled boots have a defined welt and heel.",
    "finding": "The high rear three-quarter shows the strongest improvement. The side profile still exposes the recessed flank between the raised seat and the lowered trousers. Owner verdict pending.",
    "path": "experiments/2026-11-21-felt-and-carved-hair",
    "images": [
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Studio-Hero.jpg",
        "Painted front three-quarter"
      ],
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Best-Clay.jpg",
        "Most improved · matched high rear three-quarter"
      ],
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Least-Clay.jpg",
        "Least convincing · matched side profile"
      ],
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Comparison-Details.jpg",
        "Matched cap, expression and boot details"
      ],
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Angles.jpg",
        "Nine-angle neutral-clay orbit"
      ],
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Studio-Rear.jpg",
        "Painted high rear three-quarter"
      ],
      [
        "../../experiments/2026-11-21-felt-and-carved-hair/Iterations.jpg",
        "Three stages of the cap and rim"
      ]
    ]
  },
  {
    "id": "seatsmock",
    "title": "Fitted smock and seat",
    "date": "November 21, 2026",
    "method": "GPT-6.2 Sol (extra high) · Codex desktop · Blender 5.2.1",
    "change": "Started from turn 6 to answer the owner’s note about the gap at the hips. One pelvis cage flows into both thighs. The shirt hem and lowered waistband follow that anatomy.",
    "finding": "Side and low rear improved most. The cloth bands still read separately near the grip from low front. Owner verdict pending.",
    "path": "experiments/2026-11-21-seat-and-smock",
    "images": [
      [
        "../../experiments/2026-11-21-seat-and-smock/Studio-Rear.jpg",
        "Painted rear three-quarter"
      ],
      [
        "../../experiments/2026-11-21-seat-and-smock/Comparison-Clay.jpg",
        "Matched side and low rear views"
      ],
      [
        "../../experiments/2026-11-21-seat-and-smock/Fit-Test.jpg",
        "Same seat with unfitted and fitted hems"
      ],
      [
        "../../experiments/2026-11-21-seat-and-smock/Front-Low.jpg",
        "Least convincing angle · low front"
      ],
      [
        "../../experiments/2026-11-21-seat-and-smock/Studio-Hero.jpg",
        "Painted front three-quarter"
      ]
    ]
  },
  {
    "id": "roundedseat",
    "title": "Rounded seat and ceramic glaze",
    "date": "November 21, 2026",
    "method": "GPT-6.2 Sol (extra high) · Codex desktop · Blender 5.2.1",
    "change": "Round the seat above and below its widest point while preserving its rear projection. Refit the shirt and waistband around the new arc and add ceramic glaze colors.",
    "finding": "The rounded side follows the approved profile more closely. Low rear still shows a separate waistband lip over the leg folds. Owner verdict pending.",
    "path": "experiments/2026-11-21-rounded-seat",
    "images": [
      [
        "../../experiments/2026-11-21-rounded-seat/Comparison-Color.jpg",
        "Painted side profile, before and after"
      ],
      [
        "../../experiments/2026-11-21-rounded-seat/Studio-Hero.jpg",
        "Painted front three-quarter"
      ],
      [
        "../../experiments/2026-11-21-rounded-seat/Studio-Rear.jpg",
        "Painted rear three-quarter"
      ],
      [
        "../../experiments/2026-11-21-rounded-seat/Comparison-Clay.jpg",
        "Matched clay side and low rear"
      ],
      [
        "../../experiments/2026-11-21-rounded-seat/Reference-Profile.jpg",
        "Approved side and two shape trials"
      ]
    ]
  },
  {
    "id": "garmentcarved",
    "title": "Continuous trousers, 360° carved hair & soft rims",
    "date": "November 21, 2026",
    "method": "Neon (Gemini 4 Neon) · Antigravity · Blender 5.2.1",
    "change": "Started from turn 8 (`Clive-RoundedSeat.blend`). Replaced the four-piece trousers with one continuous forked two-leg cage indented under fused wrist/hand grips, wrapped Greek-carved beard locks 360° over a recessed core, gave the cap felt rim and smock hem C1 semicircular turns, draped the sleeves, and sharpened boot welt/heel planes.",
    "finding": "Low front, low rear, and side garment continuity, back/side beard carving, rim softness, wrist/hand form, and boot planes improved cleanly. High rear still shows the separate sleeve-to-smock shoulder intersection seam. Owner verdict pending.",
    "path": "experiments/2026-11-21-garment-anatomy-carved-hair",
    "images": [
      [
        "../../experiments/2026-11-21-garment-anatomy-carved-hair/Comparison-Clay.jpg",
        "Matched neutral clay, turn 8 left and turn 9 right (low front, low rear, side)"
      ],
      [
        "../../experiments/2026-11-21-garment-anatomy-carved-hair/Comparison-Details.jpg",
        "Close-up comparisons: 360° beard, hands & trousers, boots, and 160 px check"
      ],
      [
        "../../experiments/2026-11-21-garment-anatomy-carved-hair/Studio-Hero.jpg",
        "Painted front three-quarter"
      ],
      [
        "../../experiments/2026-11-21-garment-anatomy-carved-hair/Studio-Rear.jpg",
        "Painted rear three-quarter"
      ],
      [
        "../../experiments/2026-11-21-garment-anatomy-carved-hair/Least-Clay.jpg",
        "Least convincing · high rear and overhead"
      ],
      [
        "../../experiments/2026-11-21-garment-anatomy-carved-hair/Angles.jpg",
        "Nine-angle neutral-clay orbit"
      ]
    ]
  },
  {
    "id": "handsgrin",
    "title": "Chubby fists, a real grin and a beard that flows",
    "date": "November 21, 2026",
    "method": "Fable 2 (Claude Fable 5.2) · Claude Code · PyTorch SDF + Blender 5.2.1",
    "change": "Started from turn 9 (`Clive-GarmentAndHair.blend`) after Arne asked for serious work on the hands and more of the reference's charm. Replaced the mitten hands with sheet-sized fists gripping the waistband, and the scowling head and separate beard locks with one glazed bust: ball nose, cheek apples, wink arc, toothy grin, handlebar moustache and a beard whose locks fan from the lip and gather to a hooked tip. Cap, smock, trousers, boots and seat are turn 9's, untouched.",
    "finding": "Hands and expression improved most from the front and three-quarter, in clay and paint. From the side the fists still read as hooks, the face is busier in clay than turn 9's, and the cuffs, sleeves and body proportions are unchanged. Owner verdict pending.",
    "path": "experiments/2026-11-21-hands-and-charm",
    "images": [
      [
        "../../experiments/2026-11-21-hands-and-charm/Studio-Hero.jpg",
        "Painted three-quarter"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Comparison-Hands.jpg",
        "Hands: the sheet, turn 9 and turn 10"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Comparison-Face.jpg",
        "Face: the sheet, turn 9 and turn 10"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Comparison-Clay.jpg",
        "Matched neutral clay, turn 9 left and turn 10 right"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Comparison-Color.jpg",
        "Matched paint, turn 9 left and turn 10 right"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Turnaround-vs-Reference.jpg",
        "Approved turnaround above, turn 10 below"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Least-Convincing.jpg",
        "Least convincing: fists from the side, face from below"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Face-Portrait.jpg",
        "Painted face"
      ],
      [
        "../../experiments/2026-11-21-hands-and-charm/Angles.jpg",
        "Nine-angle neutral-clay orbit"
      ]
    ]
  }
];
