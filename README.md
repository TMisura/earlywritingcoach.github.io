# Early Writing Coach

Home of **earlywritingcoach.ai** / **earlywritingcoach.com**.

Parents and tutors submit any K–8 writing assignment. The tool names **one or two** writing difficulties, how to reinforce them at home, and a sentence to tell the teacher. It does **not** score the child. It does **not** keep the writing sample. It does keep the coaching recommendations if you have an account.

Summer Writing Squad is a separate campaign page (`summer_writing_squad.html`), not this product.

## Save these files

Read **[CRITICAL_FILES.md](CRITICAL_FILES.md)** whenever a coaching note appears.

- Parents: **Save this note** on the report page → your computer’s Downloads folder.
- This repo: standards live in `data/standards/`. Do not commit `backend/coach.db`.

## Run locally

```bash
python3 -m pip install -r backend/requirements.txt
python3 tools/build_standards.py
./start.sh
```

Open http://127.0.0.1:8000
