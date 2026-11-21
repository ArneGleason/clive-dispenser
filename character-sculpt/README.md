# Character Sculpt Lab

Develop a repeatable way to turn one or more character images into a figurine the owner wants to print. Clive, the mooning garden gnome, is the first subject. The owner judges likeness and appeal. The result of a run can be a useful rejection.

[Browse Clive’s sculpt history and copy the current prompt](gallery/README.md).

**Start a run** by reading [Clive’s brief](subjects/clive.md), the [experiment log](LOG.md), and the [refinement workflow](WORKFLOW.md). Copy the [run template](RUN.md) into a new experiment directory. A new model, tool, or representation is welcome.

## Handoff prompt

Use [the current handoff](HANDOFF.txt). The gallery reads this same file. To catalog a new run, add its notes and image paths to [catalog.js](gallery/catalog.js). From a checkout, serve the repository root with `python -m http.server 8000` and open `http://localhost:8000/character-sculpt/gallery/`.

## What counts as progress

A pass should answer a specific visual question. “Can I see the raised cheek pushing the wink shut from both the front and the low three-quarter view?” gives the next operator more to work with than “increase detail.” Save a parent whenever a change fixes one angle at the expense of another. An approved exterior and a successful physical print are separate milestones. The existing dispenser is a later engineering resource.

The workflow, template, and review renderer can be reused for another character. Give that character its own brief, image inventory, and comparison baseline.
