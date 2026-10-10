# Document Generator

Document Generator turns recurring church planning inputs into service documents. Its music language distinguishes the musical work from the people and notes that should be credited with it.

## Language

**Music Item**:
A piece of music assigned to a specific service position, such as Prelude, Offertory, Anthem, or Postlude.

**Personnel**:
Named guest musicians, ensembles, or performers who should be credited for a **Music Item**.
_Avoid_: Treating personnel as a generic note or legacy alias.

**Details**:
A secondary composer, arranger, harmonizer, or editor credit for a **Music Item** that should be template-addressable separately from the primary composer.
Use **Details** only when the **Music Item** already has a primary composer/source credit in the composer field.
_Avoid_: Catch-all notes, rehearsal instructions, lyric/text blocks, publisher notes, personnel, or composer-like text placed in **Details** because the composer field is blank.

**Publisher Note**:
Copyright, publisher, hymnal number, or edition information present in the source email but not passed into generated documents.

**Tune Name**:
A hymn tune identifier, often written parenthetically after a hymn or response title.
_Avoid_: Treating tune names as part of the title in current templates.

**Empty Music Item**:
A service position explicitly marked as having no music item.

**Expected Personnel**:
The personnel value for a **Music Item**, empty unless the source email clearly names performers or ensembles to credit.

## Relationships

- A **Music Item** may have zero or more **Personnel** credits.
- **Personnel** is distinct from title, composer, and **Details**.
- **Personnel** applies to both organist and choir emails.
- Canonical music extraction includes a `*_personnel` field for every organist and choir **Music Item** section.
- A **New Spirit Offertory** header credits **New Spirit** as **Personnel** for the offertory.
- A `with ...` suffix on a music section header is **Personnel**, not general details.
- Instrumentation alone is not **Personnel** unless a named person or ensemble is present.
- A named performer with role or instrument, such as `Jane Smith, soloist`, is **Personnel**.
- **Details** is reserved for secondary musical credit information, not operational instructions.
- If the composer field is blank for a **Music Item**, the details field should also remain blank unless a primary composer/source credit is identified first.
- A **Publisher Note** is discarded during music extraction.
- A **Tune Name** is ignored for now unless future templates add explicit tune-name fields.
- `None` in a music section means an **Empty Music Item**: all fields for that section are empty.
- Bracketed choir instructions are not extracted into fields, but may indicate nearby evidence for **Personnel** in the email.

## Example dialogue

> **Dev:** "The email says the offertory includes a guest cellist. Is that just a detail?"
> **Domain expert:** "No. That is **Personnel** because the musician should be credited in the service document."
>
> **Dev:** "For a choir line with `Welsh Hymn Melody` followed by `Harm. by David Evans`, which field gets the harmonizer?"
> **Domain expert:** "`Welsh Hymn Melody` is the primary composer/source credit, and `Harm. by David Evans` is **Details**."

## Flagged ambiguities

- If a source line names multiple composer-like credits and it is unclear which is primary, prefer the first named source/creator as composer and use **Details** only for clearly secondary arranger, harmonizer, editor, or additional-composer credit.
