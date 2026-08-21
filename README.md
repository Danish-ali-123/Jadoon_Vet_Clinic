# Vet Case Assistant

A zero-budget friendly Streamlit prototype for veterinary decision support. The app collects animal description, symptoms, history, vitals, and exam notes, then suggests:

- urgency level and red flags
- likely differential diagnoses
- recommended diagnostics
- treatment principles for veterinarian review
- a copyable case summary
- optional open-source semantic matching with `sentence-transformers/all-MiniLM-L6-v2`
- optional AI assessment when `OPENAI_API_KEY` is configured

## Important clinical note

This tool is not a replacement for a licensed veterinarian. It should not be used to make final diagnoses, prescribe medicine, calculate doses, or bypass a physical examination. Use it as a triage and documentation assistant.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Model approach

The app works without any OpenAI key. It uses:

- the veterinarian-review-pending CSV knowledge base in `Raw Data/`
- `sentence-transformers/all-MiniLM-L6-v2` for lightweight open-source semantic matching
- automatic keyword fallback if the pretrained model cannot load

This is safer and cheaper than trying to run a large LLM on free hosting.

Current dataset coverage is strongest for cattle, dogs, and cats. The form includes other species so the workflow is ready, but more vet-reviewed rows should be added before those species are treated as covered.

## Optional OpenAI setup

The app works without an API key. This step is only for extra paid LLM-style text output.

To enable AI output:

```bash
set OPENAI_API_KEY=your_api_key_here
set OPENAI_MODEL=gpt-5-mini
streamlit run app.py
```

On macOS/Linux, use `export` instead of `set`.

## Free deployment path

GitHub Pages is for static HTML/CSS/JavaScript sites, so it will not run this Python app. For a Python front end, use Streamlit Community Cloud:

1. Create a GitHub repository.
2. Upload `app.py`, `vet_ai.py`, `data_kb.py`, `knowledge_base.py`, `requirements.txt`, `README.md`, and the `Raw Data/` folder.
3. Go to Streamlit Community Cloud and create a new app from the repo.
4. Main file path: `app.py`.
5. Add `OPENAI_API_KEY` in Streamlit secrets only if you want paid AI output. It is not required.

## Best next improvements

- Add a vet-approved dataset of local diseases, medicines, and farm/pet workflows.
- Add role-based login before storing real patient/client data.
- Add PDF case report export.
- Add a retrieval layer over curated veterinary references instead of scraping random internet pages.
- Add validation by the veterinarian before sharing with clients.
