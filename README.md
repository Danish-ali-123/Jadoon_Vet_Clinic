# Vet Case Assistant

A Streamlit decision-support app for veterinary case triage at Jadoon Vet Clinic. The app collects animal description, history, clinical signs, vitals, and exam notes, then suggests:

- urgency level and red flags
- top 2 likely diagnosis candidates
- recommended confirmatory diagnostics
- treatment plan principles for veterinarian review
- a copyable case summary
- automatic case-history storage with searchable reference numbers and optional Google Sheets sync
- open-source pretrained semantic matching with `sentence-transformers/all-MiniLM-L6-v2`
- local no-key Hugging Face LLM assessment with `HuggingFaceTB/SmolLM2-135M-Instruct` by default

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
- a local no-key Hugging Face text-generation LLM assistant that generates the final assessment when the public model can load
- a deterministic local fallback that formats the top 2 matches into diagnosis candidates, diagnostics, treatment principles, and immediate safety actions

Current dataset coverage is strongest for cattle, dogs, and cats. The form includes other species so the workflow is ready, but more vet-reviewed rows should be added before those species are treated as covered.


## Case history storage

Each analyzed case is saved with a reference number like `JVC-20260822-0001`. By default it saves to `case_history.jsonl`. If Google Sheets secrets are configured, the same case is also appended to a Google Sheet. The app includes a Streamlit `Case History` page where the veterinarian can search by reference number, species, breed, condition, date, or symptoms, then download a case JSON or full history CSV/JSON.

For permanent clinic records on Streamlit Cloud, Google Sheets is the recommended first backend because it is simple for the vet to open on any device. Firebase is better later for login, role permissions, real-time app dashboards, and larger production workflows.

### Google Sheets setup

1. Create a Google Cloud service account and enable Google Sheets API.
2. Create a Google Sheet with a tab named `Cases`.
3. Share the sheet with the service account email as Editor.
4. In Streamlit Cloud, add secrets:

```toml
GOOGLE_SHEET_ID = "your_google_sheet_id"
GOOGLE_SHEET_WORKSHEET = "Cases"
GOOGLE_SERVICE_ACCOUNT_JSON = '''{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","token_uri":"https://oauth2.googleapis.com/token"}'''
```

The app still works without these secrets, but then history is only local JSONL and can be lost on Streamlit reboot.

## Medication support policy

The app can show medicine type, antibiotic class, and examples mentioned in the veterinarian knowledge base. It intentionally does not auto-generate exact dose, route, interval, or duration as a final prescription. Those details must be calculated and confirmed by the veterinarian using weight, species, pregnancy/lactation status, organ status, culture/sensitivity, local drug labels, and food-animal withdrawal rules.

To display exact clinic-approved medication protocols safely, fill `Raw Data/vet_medication_protocols_template.csv` with veterinarian-approved drug, dosage limit, route, frequency, duration, and withdrawal fields. The app will show those fields as recommendations for vet review.
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

