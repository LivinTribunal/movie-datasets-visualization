---
name: unslop
description: >
  Cut AI tells from prose a human will read: PR titles and descriptions, review
  findings, issue bodies, docs, the report text, chart captions and app copy,
  fresh docstrings and comments. Load it before drafting. Triggers: "/unslop",
  "unslop this", "make this sound human", "does this read as AI", drafting a PR
  body or a review finding, writing a section of the report, "explain this in
  two sentences".
---

# Unslop

Adapted from the upstream `pstack/unslop` skill
(https://github.com/cursor/plugins/blob/main/pstack/skills/unslop/SKILL.md).
Rules 1 to 31 are upstream's, with 13 and 26 adjusted. Rule 32 is ours.

## Chat

Most invocations land on chat text, not on a document. There the job is length
first and tells second. Answer in two sentences unless the user asked for more,
and apply five rules: 32 (mannered prose), 27 (say what it does, not how it
feels), 20 (chatbot phrases), 22 (sycophancy), 23 (filler). Skip the other 27.
They are for text that carries a `file:line`.

## What this applies to

New prose, at the moment you write it:

- PR titles, PR descriptions and PR review comments
- `review-proof` and `pr-ready` reports
- The project report (motivation, data, design choices, observations, lessons
  learned), `docs/decisions.md` entries, `DATASETS.md` notes
- Text shown in the app: titles, axis labels, tooltips, captions, the notes
  that tell users data was transformed
- Docstrings and comments you are writing in this change

Three things stay exactly as they are:

- Existing text in `docs/**`, `AGENTS.md` and `CLAUDE.md`. Do not sweep them
  for em dashes. Rewriting old text is churn with no reader on the other end.
- Quoted material. Lecture quotes, error output, dataset column names, log
  lines and user quotes stay verbatim. Never unslop evidence.
- Machine-read text. Commit messages, file and column names, CLI flags and
  anything a script parses keep their required shape.

Evidence beats voice. A review finding carries its mechanism, its `file:line`
and what proves it. If a rewrite would cost a sentence its path, its command or
its number, keep the fact and rephrase around it.

## Process

1. Scan for the patterns below.
2. Rewrite. Keep the meaning and the intended tone.
3. Add soul (next section).
4. Self-audit: "What makes this obviously AI generated?" Fix what is left.

## Adding soul

Removing patterns is half the job. Sterile, voiceless writing is just as obvious.

- **Have opinions.** React to facts instead of listing pros and cons neutrally.
- **Vary rhythm.** Short sentences. Then longer ones that take their time.
- **Acknowledge complexity.** "Useful but also misleading for small genres"
  beats "useful".
- **Use "we" or "I" when it fits.** The report is written by three people.
- **Be specific.** Not "coverage is limited" but "TMDB has a budget for 28 % of
  the working subset".

First person is a tone allowance, not a licence to narrate. PR bodies describe
the change, never the process, so "I've implemented..." and "Let me..." stay
out of them.

## Patterns to detect and fix

### Content

1. **Puffery.** "pivotal moment", "testament to", "evolving landscape",
   "setting the stage for", "deeply rooted". State what happened.
2. **Name-dropping.** Listing sources without context. Pick one, say what it
   said.
3. **Superficial -ing phrases.** "highlighting...", "ensuring...",
   "showcasing...". Delete, or say what the thing does.
4. **Promotional language.** "vibrant", "breathtaking", "groundbreaking",
   "stunning". Use neutral words.
5. **Vague attributions.** "Experts believe", "Studies suggest". Name the
   source or delete.
6. **Formulaic challenges.** "Despite challenges... continues to thrive."
   Replace with specific facts.

### Language

7. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance,
   fostering, garner, interplay, intricate, landscape (abstract), pivotal,
   showcase, tapestry, testament, underscore, vibrant, robust, seamless. Use
   plain words.
8. **Fancy ways to say "is".** "serves as", "stands as", "boasts", "features".
   Say "is" or "has".
9. **"Not just X, but Y."** State the point directly.
10. **Rule of three.** Forcing ideas into groups of three. Use the natural
    number.
11. **Synonym cycling.** Film, movie, title, picture for the same thing in one
    paragraph. Pick one and repeat it.
12. **False ranges.** "from X to Y" where X and Y are not on a scale. List the
    topics.

### Style

13. **Em dashes.** Do not use them in prose you write from now on. Use periods
    or commas. Parentheses, en dashes and hyphens used as dashes are the same
    tell in other clothes. If a thought needs separation, end the sentence.
14. **Colon overuse.** Colons are fine before a list or an example, not as a
    connector in the middle of a sentence.
15. **Boldface overuse.** Do not bold every proper noun.
16. **Inline-header lists.** A bold label and colon that restates the line
    ("**Performance:** Performance improved...") becomes prose. A bold lead-in
    that ends in a period and is followed by new detail is fine.
17. **Title case headings.** Use sentence case.
18. **Decorative emojis.** Remove them from headings and bullets.
19. **Curly quotes.** Use straight quotes.

### Communication

20. **Chatbot phrases.** "I hope this helps!", "Let me know if...",
    "Certainly!". Remove.
21. **Cutoff disclaimers.** "While specific details are limited...". Find the
    source or remove.
22. **Sycophancy.** "Great question! You're absolutely right!" Answer directly.

### Filler

23. **Filler phrases.** "In order to" becomes "To". "Due to the fact that"
    becomes "Because". "It is important to note that" goes.
24. **Hedging.** "could potentially possibly be argued that it might" becomes
    "may".
25. **Generic conclusions.** "The future looks bright." State a plan or a fact.

### Jargon

26. **Abstract metaphor nouns.** Substrate, wedge, vector, locus, vantage,
    nexus, bedrock, scaffolding, modality, paradigm, gold-plating, ratchet,
    endgame, north star, flywheel. Pick the concrete word: "substrate" becomes
    "base", "vector" becomes "way". Words that name real things here are
    exempt when used that way: a **scale** (D3 scale), a **view** (one linked
    chart in the app), a **brush**, a **stage** (a pipeline stage), a
    **subset** (working or notable).

### Plain speech

27. **Say what it does, not how it feels.** "insights at your fingertips"
    names a feeling. Name the mechanism or a number instead: "brushing years
    in the timeline filters the scatter to films released in them". If the
    sentence could appear unchanged in another project's docs, it says nothing
    about this one. Cut it.
28. **Split dense sentences.** If the reader has to backtrack, break it in two.
    One idea per sentence.
29. **Active voice.** "the data is cleaned" becomes "the clean stage drops
    TMDB's zero budgets". Passive is fine only when the actor does not matter.
30. **Cut adverbs.** "significantly improves" becomes the measured change.
31. **Plain words.** "utilize" and "leverage" become "use", "facilitate"
    becomes "help", "numerous" becomes "many".
32. **Mannered prose.** Metaphor standing in for a direct statement: "a dial
    worth turning", "moves the needle", "the long pole", "punches above its
    weight". It makes the reader work so the writer can perform, and it drags
    in connotations you did not choose. When a literal phrase exists, use it.

## Executive summary

Every PR body opens with one. Exactly two sentences in plain language, written
**last**, after the rest of the body:

1. What changed.
2. Why it matters.

No file paths, column names or issue numbers. Test: would a teammate who has
not read the code understand what this PR is about from these two sentences?
If not, rewrite.
