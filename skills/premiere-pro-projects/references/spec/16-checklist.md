# 16. Conformance checklist

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Every Premiere-saved step satisfies all of these [O: steps 00–11, 15, 19, 21, 22 #checklist.premiere-saves-conform]; a writer MUST preserve them:

1. Container per [§1](01-container.md#1-container); objects per [§2.1](02-document-structure.md#21-objects); identities unique; every reference outside `Project` resolves; a writer adds no unreferenced objects.
2. ClassID, Version and element paths per class as catalogued ([`prproj-classes.md`](../prproj-classes.md)); param ClassID matches its value type ([§12.2](12-effects-and-keyframes.md#122-components-and-params)).
3. Every indexed list contiguous from 0; track item lists sorted by `Start`; the master's `AudioTrackInlet/Sources` equal to the audio `Tracks` list ([§8](08-tracks.md#8-tracks)).
4. Track position agrees in all four places; `Track/ID` unique per group and below `NextTrackID` ([§8](08-tracks.md#8-tracks)).
5. Per track: no overlapping clip items; `End − Start = (Out − In)/speed`; `Start`/`End` on the frame grid; `Start` omitted at 0; `InPoint` present ([§9.2](09-track-items-and-links.md)).
6. Each chain, component, param, SubClip, timeline clip and SecondaryContent referenced exactly once; `ClipID`s and GUID IDs unique.
7. Links have two members; no item in two links. Linked items usually share their timing, but a split edit (J/L cut) keeps the link with different `Start`/`End` on each side ([§10](09-track-items-and-links.md#10-links)).
8. `Monitor.ProgramZoomOut` = sequence length (0 for an empty sequence) ([§7.4](07-sequences.md#74-length)).
9. Chain flags and components consistent: no `DefaultMotion` together with an explicit Motion component; component IDs unique, ≥ 3 for added effects ([§12.1](12-effects-and-keyframes.md#121-chains)).
10. Keyframe strings per [§12.4](12-effects-and-keyframes.md#124-animation). Transform key times lie within three frames of their clip's source range [O: step 15 #checklist.transform-keys-in-range].
11. Markers ([§13](13-markers.md#13-markers)): each `Marker` object is listed once in its `Markers` list, with `First` = its `mMarkerID`; `DVAMarker` is valid JSON; a Sequence with markers has a `MarkerOwner`.
12. Transitions: every `HeadTransition`/`TailTransition` points at a transition listed in the same track's `TransitionItems`, and each transition's `Start` + `Alignment` is the cut it sits on ([§11](11-transitions.md#11-transitions)).
13. Transcripts: a rewritten `TranscriptData` decodes to the same model it was built from, its `BinaryHash` length part is the decoded length + 12, and Segment start/duration still match their first/last word ([§3](03-value-encodings.md#3-value-encodings), [§14](14-transcripts-and-captions.md#14-transcripts-speech-to-text)).

`scripts/prproj.py validate` checks references, unique top-level identities and `ClipID`s, and unreferenced new objects; `scripts/selftest.py` checks the Transform layout, the timing equation, Transform key times and the keyframe grammar. The guides list the rest per operation.
