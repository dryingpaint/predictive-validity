---
name: report-doc
description: Update the Predictive Validity Report, the Claude Doc that is the canonical report. Ports prose edits and Claude-addressed comments from the doc into the templates, rebuilds with `python -m report`, writes the changed sections and figures into the doc, and opens a PR. Use when asked to update, refresh, rebuild or publish the report or the doc, or when a doc comment asks for a change to it.
---

# Update the report doc

The doc named in `report/doc.json` is the report people read and edit. Its prose comes from
`report/REPORT.template.md`, `report/APPENDIX.template.md` and `report/narrative/*.md`; its numbers,
tables and figures come from the pipeline. Its two tabs are rendered as `REPORT.md` and
`REPORT_APPENDIX.md`. The pinned comment on the doc tells readers to edit prose freely and to comment
on a number, table or figure instead.

Work in a worktree off `origin/main` (AGENTS.md). The build only reads the shared database, but
announce it to the other sessions if one is writing, and wait for theirs to finish if it writes
tables the report reads.

## 1. Pull the doc's edits into the templates

1. For each tab in `report/doc.json`, read its body node with `payload {"kind":"view","sinceRev":<rev>}`.
   The changed blocks are edits made since the last publish.
2. For each changed prose block, find the template that renders it (grep a distinctive phrase) and port
   the edit, keeping `{{…}}` placeholders where the doc shows a pipeline number. Do not port an edit to a
   number, table or figure: reply in a doc comment on it that it comes from the pipeline, and fix the
   pipeline or template if the comment shows it is wrong.
3. `query` the tab's comments (`afterSeq` = the last seq you handled) for threads addressed to Claude and
   not yet answered. Make the change they ask for in the templates, and reply in the thread once it is
   published.

## 2. Build

Run `.venv/bin/python -m report`. It reads one database snapshot and writes `report/output/`,
`REPORT.md` and `REPORT_APPENDIX.md`. It exits non-zero:

- when Section 3 picked cases its audit lacks. Run `.venv/bin/python -m report.cases pending`, check
  each case with agents following `report/audits/case_protocol.md` (evidence and outcome agents for every
  case; a second coder for each failure; an adjudicator where the codes differ), save their JSON answers
  in one directory, run `.venv/bin/python -m report.cases merge <dir>`, and build again;
- when the link dropped and the build read two snapshots: build again;
- when a placeholder is left unfilled: fix the template.

Then read the prose of every section the plan (step 3) will rewrite against the new numbers: rankings,
"most"/"least", comparisons with BIO, named cases, counts written as words. The templates hold static
sentences; fix any the numbers no longer support.

## 3. Plan

Run `.venv/bin/python -m report.doc plan`. It writes `report/output/doc_plan.json`:

- `figures`: figure files that changed. For each, upload it to the doc's artifact
  (`Artifact(action="publish", url=<doc url>, file_path=<path>, asset=true)` → an opaque id), create a
  blob (`create(object="blob", engine="blob", container=C, payload={"asset":"<id>"})` → `blob/<id>`), then
  `.venv/bin/python -m report.doc blob <path>=blob/<id>` and run `plan` again. While figures are listed,
  the plan holds no sections.
- `sections`: in tab order, each `replace`, `insert` (after the section keyed `after`) or `delete`, with the
  section's `heading`, `level` and `markdown` (figures already written as their blobs).

## 4. Write the doc

`C` = `{"kind":"project","id":"<doc>"}`. For each tab with steps, read its outline
(`payload {"projection":"outline"}`) for block ids and the tab's `rev`, then apply the steps one
`update` per section, in order, anchoring each on the previous ack:

- A section is its heading block and every block after it up to the next heading block of any level.
  Find the heading by its text and level; if the text repeats, take the one in the right parent
  section.
- `replace`: one `replace` op on all of the section's block ids, `"ifRev":<rev of the read>`,
  `"with":{"as":"markdown","from":{"kind":"inline","content":<markdown>}}`.
- `insert`: `insert` after the last block of the `after` section, `"source":{"as":"markdown",…}`.
- `delete`: `delete` the section's block ids with `"ifRev"`.
- The title section keeps the byline under the title (as-of date chip, author): leave it out of the
  replaced ids and set its date chip to today.
- `guard_mismatch` or `find_none`: someone edited the section meanwhile. Read it, port their edit (step 1),
  rebuild, and plan again. `anchors_affected`: a comment hangs on words the rewrite drops. Resend with
  `"allowDetach":true` only for a thread already answered or resolved; otherwise skip that section and
  ask in the thread.

## 5. Record and open the PR

1. Run `.venv/bin/python -m report.doc published REPORT.md=<last rev> REPORT_APPENDIX.md=<last rev>`
   with each tab's revision from your last ack on it.
2. Reply in the comment threads you acted on.
3. Commit the templates, `REPORT.md`, `REPORT_APPENDIX.md`, `report/doc.json`, the figures and any
   audit files, and open the PR. Its body says what ran, which sections changed and why.
