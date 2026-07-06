# Vault Schema

This vault follows the LLM Wiki pattern: raw sources are preserved as notes, synthesized pages are maintained in `wiki/`, reusable prompts live in `prompts/`, and every meaningful change is recorded in `log.md`.

## Folders

- `raw/` contains source notes and research captures. These files should not be rewritten except to add source metadata or correction notes.
- `wiki/` contains synthesized project knowledge. These pages should be updated when new facts change the current understanding.
- `prompts/` contains reusable prompts for translation, article writing, and text polishing.

## Page Rules

Every wiki page should include:

- a one-paragraph summary;
- current decisions or facts;
- open questions if any;
- links to related pages;
- source links when facts came from the web.

Use Obsidian links like `[[wiki/dzen-bridge]]` when connecting pages. Keep filenames ASCII and lowercase with hyphens.

## Maintenance Workflow

When new source material arrives:

1. Create or update a note under `raw/`.
2. Update affected `wiki/` pages.
3. Update `index.md` if a new page was added.
4. Append an entry to `log.md`.

When answering project questions, read `index.md` first, then the relevant wiki pages.
