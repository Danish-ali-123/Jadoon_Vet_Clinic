# Vet Case Assistant

A Streamlit decision-support app for veterinary case triage. The app collects animal description, history, clinical signs, vitals, and exam notes, then suggests:

- urgency level and red flags
- likely differential diagnoses
- recommended diagnostics
- treatment principles for veterinarian review
- a copyable case summary
- optional open-source semantic matching with `sentence-transformers/all-MiniLM-L6-v2`
- optional external LLM help through free-tier provider keys

## Important clinical note

This tool is not a replacement for a licensed veterinarian. It should not be used to make final diagnoses, prescribe medicine, calculate doses, or bypass a physical examination. Use it as a triage and documentation assistant.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Model approach

The app works without any paid API key. It uses:

- the veterinarian-review-pending CSV knowledge base in `Raw Data/`
- `sentence-transformers/all-MiniLM-L6-v2` for lightweight open-source semantic matching
- automatic keyword fallback if the pretrained model cannot load
- optional Groq or Hugging Face LLM calls when free-tier tokens are configured

Current dataset coverage is strongest for cattle, dogs, and cats. The form includes other species so the workflow is ready, but more vet-reviewed rows should be added before those species are treated as covered.

## Optional free-tier LLM setup

The app does not require OpenAI. For optional LLM reasoning, add one or both secrets in Streamlit Cloud:

```toml
GROQ_API_KEY = "your_groq_key"
GROQ_MODEL = "groq/compound-mini"

HF_TOKEN = "your_huggingface_token"
HF_MODEL = "deepseek-ai/DeepSeek-R1:fastest"
```

Free tiers are rate-limited and can change. The safest default is still the local knowledge-base matcher, with any LLM output treated as draft support for a veterinarian.

## Streamlit Cloud deployment

1. Push this repository to GitHub.
2. In Streamlit Cloud, create or manage the app.
3. Repository: `Danish-ali-123/Jadoon_Vet_Clinic`.
4. Branch: `main`.
5. Main file path: `app.py`.
6. Add optional secrets only if you want external LLM output.
7. Deploy or reboot the app.

## Best next improvements

- Add more vet-approved rows for goat, sheep, poultry, buffalo, horse, camel, and rabbit.
- Add role-based login before storing real patient/client data.
- Add PDF case report export.
- Add curated veterinary references for retrieval instead of relying on general web search.
- Add formal validation by the veterinarian before sharing with clients.
