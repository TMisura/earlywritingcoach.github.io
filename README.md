# earlywritingcoach.github.io

Summer Writing Squad — a K–8 writing coach that scores a child's writing against ELA written-expression standards for all 50 states and DC.

## Run locally

```bash
python3 -m pip install -r backend/requirements.txt
python3 tools/build_standards.py
chmod +x start.sh
./start.sh
```

Open http://127.0.0.1:8000

## What is in place

- Landing page and four writing destinations
- Standards packs for 51 jurisdictions, grades K–8 (writing + language conventions)
- Unique official numbering for Texas TEKS, Florida B.E.S.T., Virginia SOL, and Nebraska CCR
- CCSS-based packs for states that still use Common Core or a renamed CCSS-aligned framework
- Rubric scoring, accounts, free-plan cap (3 scores), Family/Classroom demo subscription
- Saved assessment history

## Still to build for a live subscription product

- Stripe Checkout + webhooks (demo plan activation is in place)
- Classroom roster and teacher view
- Email verification and password reset
- Human-reviewed standard text for remaining unique-similar states (IN, OK, SC, TN, KY, AK, ID, MO, MN currently crosswalk to CCSS constructs)
- Production hosting (this GitHub Pages repo now also runs as a FastAPI app)
