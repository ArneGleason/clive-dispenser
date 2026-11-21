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
    "method": "Continuous quad Multires + SDF projection",
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
  }
];
