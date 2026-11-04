# Loose ends

**Status**: planned

## User problem
A writer often wants to offer a reader two or three choices but has time to write only one of
them today. Today the only options are to leave the other choices out, or to point them at a
passage that does not exist, which is a red broken-link error that blocks the merge. Writers on
later days also have no way to find the choices other people meant to come back to, so a branch
someone planned is quietly forgotten.

## User stories
- As a writer, I want to add a choice now and write where it leads on another day, so that my
  passage offers the choices I meant without blocking my merge.
- As a reader, I want a choice that leads nowhere yet to say so and let me go back, so that I am
  not left at a dead page.
- As a writer looking for today's starting point, I want a list of every choice still waiting to
  be written, with where it is and who wrote it, so that I can pick one up.
- As a writer, I want a mistyped name to be an error as it is today, so that a typo never hides as
  a loose end.

## Behavior
**The passage.** `src/Unwritten.twee` is a tooling-owned infrastructure file, like `Start.twee`,
created once by the developer. It holds one passage, `:: Unwritten`, which tells the reader
"This path hasn't been written yet." and offers **Go back**, a Harlowe `(link-undo:)` that returns
the reader to the passage holding the choice they clicked.

**Marking a loose end.** A writer points a choice at `Unwritten` in any link form, for example
`[[Go to the weir->Unwritten]]`. Nothing else is needed. The name must be exactly `Unwritten`,
capital U; any other missing name, including `unwritten` or `Unwriten`, is an ordinary
`broken-link` error ([structure-check](structure-check.md)) with no hint or guess.

**Picking one up.** Anyone, on any day, changes `Unwritten` in that link to their day's passage
name (`[[Go to the weir->Day 5 EV]]`) and writes that passage. This is the guide's usual "add a
choice to an earlier passage" step, done by editing a link instead of adding one.

**The structure check** reports nothing about `Unwritten`: links to it are working links, and the
passage itself is never an orphan (whether or not anything links to it) or a dead end. Its file is
exempt from the naming rule like the other infrastructure files ([web-editing](web-editing.md)).
No new finding codes.

**The site.** The **Passages** page ([output-formats](output-formats.md)) has a **Loose ends**
section above the passage table, one row per link to `Unwritten`: the choice's text as the reader
sees it, the passage it is in with `file:line`, and that file's writer initials and day. With
none, the section says "No loose ends." The Passages page is where the guide already sends a
writer in Step 1 to find the passage to link from, so the list sits where they start each day.
The pull request preview's Passages page shows the pull request's own loose ends.

**All paths, Metrics and Play** are unchanged. A route that reaches `Unwritten` is listed on All
Paths like any other, ending with `Unwritten`, so the writer sees the unfinished branch on the
route; Metrics counts the passage like `Start`.

**AI.** The Story Bible and the Continuity and Style editors do not treat the `Unwritten`
passage's text as story: it is never extracted, never reviewed, and never part of the earlier
text a reviewed passage is checked against. A passage that links to `Unwritten` is extracted and
reviewed as usual.

## Acceptance criteria
- AC-loose-ends-1: `src/Unwritten.twee` contains exactly one passage, `:: Unwritten`, whose text includes "This path hasn't been written yet." and a `(link-undo:)` link labelled "Go back", and contains no `[[...]]` link or goto macro. (verify: planned)
- AC-loose-ends-2: In `play.html`, clicking a choice that points at `Unwritten` shows "This path hasn't been written yet.", and clicking "Go back" returns to the passage that held the choice. (verify: planned)
- AC-loose-ends-3: Run over a story whose passages link to `Unwritten` in each link form (`[[Unwritten]]`, `[[Text->Unwritten]]`, `[[Unwritten<-Text]]`, `[[Text|Unwritten]]`, `(link-goto: "Text", "Unwritten")`), the structure check reports no finding for any of those links and no `orphan-passage` or `dead-end` for `Unwritten`. (verify: planned)
- AC-loose-ends-4: With no link to `Unwritten` anywhere, the structure check reports no finding for `Unwritten` or its file. (verify: planned)
- AC-loose-ends-5: A link to `unwritten`, `UNWRITTEN`, or `Unwriten` is a `broken-link` error naming that exact target, and its message contains no suggested passage name. (verify: planned)
- AC-loose-ends-6: `src/Unwritten.twee` gets no `file-naming` or `missing-day-passage` warning. (verify: planned)
- AC-loose-ends-7: The Passages page has a section headed "Loose ends" above the passage table with one row per link to `Unwritten`, sorted by file then line, each showing the link's display text, the passage it is in, its `file:line`, and the initials and day of that file; a passage with two such links has two rows, and a passage in a file that is not a writer's file shows blank initials and day. (verify: planned)
- AC-loose-ends-8: With no link to `Unwritten`, the Loose ends section reads "No loose ends." and has no rows. (verify: planned)
- AC-loose-ends-9: Choice text in the Loose ends section is HTML-escaped, so markup in it shows as text. (verify: planned)
- AC-loose-ends-10: Story Bible extraction never sends the `Unwritten` passage to the model, and no fact, entity or Freshness entry names `Unwritten`. (verify: planned)
- AC-loose-ends-11: The Continuity and Style editors never review `Unwritten`, and the earlier text given to them for any passage never contains the `Unwritten` passage's text; a changed passage that links to `Unwritten` is still reviewed. (verify: planned)
- AC-loose-ends-12: A route that reaches `Unwritten` appears on All Paths as one route whose last passage is `Unwritten`. (verify: planned)
- AC-loose-ends-13: `WRITERS-GUIDE.md` tells a writer how to point a choice at `Unwritten`, that the name is exact, and how to pick a loose end up from the Passages page, using only the web UI and the site. (verify: manual)

## Edge cases
- **Typo in the name** (`unwritten`, `Unwriten`): a red `broken-link` error on that line, as for
  any missing passage; the writer fixes the spelling (AC-loose-ends-5).
- **A writer declares their own `:: Unwritten`**: a `duplicate-passage` error naming the
  infrastructure file, as for any duplicate name.
- **`src/Unwritten.twee` deleted or renamed**: every loose end becomes a `broken-link` error, so
  the loss is visible on the next pull request; nothing is silently dropped from the list.
- **Two writers pick up the same loose end on the same day**: both edit the same link line; the
  second pull request shows a merge conflict, which GitHub's web editor resolves
  ([web-editing](web-editing.md)). The second writer links their passage from somewhere else.
- **A passage has two loose ends**: two rows; picking up one leaves the other listed.
- **A loose end in `Start` or another infrastructure passage**: listed, with blank initials and day.
- **A reader opens a saved link straight to `Unwritten`** with no earlier turn: "Go back" has
  nothing to undo, and the reader leaves with the browser. Every link into `Unwritten` comes from
  a passage, so a reader who clicks one always has a turn to go back to.
- **A reader reaches `Unwritten`**: the play page's footer behaves as at any passage with no
  links; a Path ID, if shown, identifies the unfinished route like any other.

## Soft goals
- Writers mark branches they mean to come back to instead of leaving them out.
- Loose ends get picked up before the end of November rather than shipping as dead ends.

## Out of scope
- Fuzzy matching, "did you mean" hints, or any automatic fix of a mistyped `Unwritten`.
- Bot edits of any kind: no automation adds, removes or rewrites a link to `Unwritten`.
- Claiming, assigning or reserving a loose end for a writer.
- Loose ends in the pull request comments or check runs; the list is on the site only.
- Counting loose ends in Metrics, or a separate page for them.
