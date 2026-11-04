# Example project layout (opt-in)

A layout that keeps edits to a `.prproj` predictable: the recipes in this skill are easiest to apply to a project organised this way. Offer it when the user asks how to structure a project or asks you to set one up; never impose it on an existing project without asking.

- **Root bins:** `src` (media, including rendered graphics), `seq` (sequences) and `sfx` (sound effects, created when the first one is added).
- **Sequence chain:** `Src` (synced camera + separate audio) → `Cut` (Src nested as one clip, then split into the kept pieces: the rough cut) → `Edit` (Cut nested as one clip; graphics, music and finishing on the tracks above). Because each stage nests the one before, the cut can be redone without touching the graphics layer's structure (but see cutting-and-editing.md §4: a nested clip doesn't follow its child's length).
- **Audio tracks in Edit:** dialogue (the nested Cut) and music on the top tracks; sound effects on 1-3 dedicated tracks below them, never mixed onto dialogue or music tracks.
- **Backups:** before changing a sequence, duplicate it as `NAME (backup YYYY-MM-DD HHMM)` in `seq` (object-surgery.md). Prune old backups only when the user asks, keeping the newest.
- **Review flags:** label clips Mango (`set-label … --label Mango`) to mark spots for the user to review.
