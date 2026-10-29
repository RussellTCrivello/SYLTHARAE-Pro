# Domain model

What the application stores, in the words an analyst or an integrator needs to
read it. This document describes the model as the code implements it; the
paragraphs that state a contract are checked against the code, so a change to
the model without a change here fails the suite.

## The record

| concept | what it is |
|---|---|
| file | one object in the collection, identified by its path and hash |
| logical file | one work, however many copies of it exist (`content identity`) |
| occurrence | one place a logical file was seen |
| archive | a container read as a tree, with lineage from container to member |
| source / side | where an item came from, and which party it belongs to |
| term, keyword, category | the vocabulary the collection is described with |

## Extraction provenance

Every stored item carries `extraction_provenance`: how its text was obtained,
from which reader, and what the reader could not do. A field that is absent
means "not measured", never "measured as zero".

### OCR

Optical character recognition is optional and is recorded honestly: an attempt
that failed is stored as a failed attempt, with its error, rather than as an
absence of text.

For OCR, `extraction_provenance.ocr` holds `attempted`, `successful`, `derived`
(whether the text came from OCR rather than an embedded layer), `engine`,
`engine_version`, `engines` (per-page engines when they differ), `confidence`,
`confidence_error` (why a confidence could not be read), `language`,
`missing_languages` (requested and not installed), `input_variant`
(`original` or `preprocessed`), `rotation`, `ocr_pages`, `rotated_pages` and
`total_pages`. A single image read reports the flat fields; a PDF read reports
the page counts as well, because the reader may have used a text layer on one
page and OCR on another.

## Media

A media read that cannot transcribe speech still stores what the container
says: duration, geometry, codec, stream counts and tags. The record states that
speech was **not** extracted rather than storing an empty transcript, so an
empty text is never mistaken for silence in the recording.
