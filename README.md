# Vet Case Assistant

A Streamlit decision-support app for veterinary case triage at Jadoon Vet Clinic. The app collects animal description, history, clinical signs, vitals, and exam notes, then suggests:

- urgency level and red flags
- top 2 likely diagnosis candidates
- recommended confirmatory diagnostics
- treatment plan principles for veterinarian review
- a copyable case summary
- open-source pretrained semantic matching with `sentence-transformers/all-MiniLM-L6-v2`
- local no-key Hugging Face LLM assessment with `google/flan-t5-small` by default

## Important clinical note

This tool is not a replacement for a licensed veterinarian. It should not be used to bypass a physical examination, local law, prescription rules, drug withdrawal periods, or professional judgment. It is a decision-support and documentation assistant.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Model approach

No OpenAI key, no DeepSeek API key, no Groq key, no paid API token is required. The app can download public Hugging Face models without a token, subject to Streamlit Cloud network and memory limits.

The app uses:

- the veterinarian-review-pending CSV knowledge base in `Raw Data/`
- `sentence-transformers/all-MiniLM-L6-v2` as the open-source pretrained semantic matcher
- automatic keyword fallback if the pretrained model cannot load
- a local no-key Hugging Face LLM assistant that generates the final assessment when the public model can load
- a deterministic local fallback that formats the top 2 matches into diagnosis candidates, diagnostics, treatment principles, and immediate safety actions

Current dataset coverage is strongest for cattle, dogs, and cats. The form includes other species so the workflow is ready, but more vet-reviewed rows should be added before those species are treated as covered.

## Streamlit Cloud deployment

1. Push this repository to GitHub.
2. Streamlit Cloud redeploys from branch `main`.
3. Main file path: `app.py`.
4. No secrets are required.
5. If changes do not appear, use Streamlit Cloud -> Manage app -> Reboot app or Clear cache and reboot.

## Best next improvements

- Add more vet-approved rows for goat, sheep, poultry, buffalo, horse, camel, and rabbit.
- Add PDF case report export.
- Add role-based login before storing real patient/client data.
- Add formal validation by the veterinarian before sharing with clients.

