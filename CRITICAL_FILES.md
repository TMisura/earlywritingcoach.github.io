# Where to save critical files

Cue yourself every time a coaching note appears. The writing sample is discarded on purpose.

## Parents and tutors — after each submission

Save **now**, before you leave the report page.

| What | Where to save it | What is not saved |
| --- | --- | --- |
| Coaching note (1–2 skills, home practice, teacher talking points) | **Your computer:** click **Save this note** (Downloads folder, filename like `early-writing-coach-note-grade-3-CA-conventions.html`). **Paper:** Print this note into the homework folder. **Account:** signed-in notes live in Saved notes — skills only. | The child’s writing. It is not stored on the server and is not in the downloaded file. |
| Monthly drawing & writing booklet | Print from **Printable booklets**. Keep the paper copy at home. | Uploaded booklet pages are not part of this tool yet. |

If you close the report without saving, that week’s “what we practiced” may be gone unless you were signed in (account keeps the skill note, still not the writing).

## Site owner (this repository)

| File | Why it is critical | When to save / commit |
| --- | --- | --- |
| `data/standards/by_state.json` | K–8 writing standards for 50 states + DC | After any rebuild (`python3 tools/build_standards.py`) |
| `data/standards/states.json` | Jurisdiction names and frameworks | Same as above |
| `data/source/ccss_ela.csv` | Source list used to build CCSS-based packs | If you replace the source compilation |
| `backend/assess.py` | How 1–2 difficulties and home practice are chosen | After you edit coaching language |
| `backend/coach.db` | Local account notes (skills only, no writing) | Machine-local only — do not commit. Back it up off-repo if you need history. |
| Downloaded HTML notes | The copy a parent can take to a teacher | On the parent’s computer, not in git |

Domains for this product: **earlywritingcoach.ai** and **earlywritingcoach.com**. Summer Writing Squad (`summer_writing_squad.html`) is a separate campaign page, not this tool.
