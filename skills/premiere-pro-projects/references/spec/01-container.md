# 1. Container

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

1. A `.prproj` file is a **gzip** stream wrapping one **UTF-8 XML** document [O: steps 00–23 #container.gzip-xml]. The gzip header is not significant: files gzipped by Python (mtime set, OS byte `0xff`) load [V: step 12-gen #container.any-gzip-header].
2. The first line MUST be exactly `<?xml version="1.0" encoding="UTF-8" ?>`, with a space before `?>`. The root is `<PremiereData Version="3">`; the file ends `</PremiereData>` and two newlines [O: steps 00–23 #container.declaration].
3. Indentation is **tabs only**, one per nesting level [O: steps 00–23 #container.tab-indent].
4. **Self-closing tags** appear only on references (`<Tag ObjectRef="12"/>`, no space before `/>`). An empty container is an opening and a closing tag on separate lines, never `<X/>` or `<X></X>` [O: steps 00–23 #container.self-closing].
5. Escaping in text (`&lt;`, `&gt;`, `&amp;`, `&#10;`): no step contains an entity reference, so it is not covered; see [§18](18-not-observed.md).
6. A writer SHOULD edit the text in place rather than re-serialise the tree: ElementTree rewrites the declaration with single quotes, writes `" />`, drops the trailing newlines and expands `&#10;`.
7. **`.prin` sidecar.** A `<name>.prin` beside a project is Premiere's media-search index; the .prproj doesn't refer to it. Ignore it; don't edit or commit it. Its format is not covered; see [§18](18-not-observed.md).
