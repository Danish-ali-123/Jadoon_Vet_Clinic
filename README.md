# Vet Case Assistant

A Streamlit decision-support app for veterinary case triage at Jadoon Vet Clinic. The app collects animal description, history, clinical signs, vitals, and exam notes, then suggests:

- urgency level and red flags
- top 2 likely diagnosis candidates
- recommended confirmatory diagnostics
- treatment plan principles for veterinarian review
- a copyable case summary
- automatic case-history storage with searchable reference numbers and optional Supabase / Google Sheets sync
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

Each analyzed case is saved with a reference number like `JVC-20260822-0001`. By default it saves to `case_history.jsonl`. If Supabase or Google Sheets secrets are configured, the same case can also sync to that cloud backend. The app includes a Streamlit `Case History` page where the veterinarian can search by reference number, species, breed, condition, date, or symptoms, then download a case JSON or full history CSV/JSON.

For permanent clinic records on Streamlit Cloud, Supabase is the recommended first database backend because it gives structured tables, JSON case storage, and future login/security options. Google Sheets is still supported when the vet wants spreadsheet access.

### Supabase setup

Create a table named `cases` in Supabase SQL editor:

```sql
create table if not exists public.cases (
  id uuid primary key default gen_random_uuid(),
  case_ref text unique,
  saved_at timestamptz,
  patient_label text,
  animal_type text,
  species text,
  breed text,
  age text,
  sex text,
  symptoms text,
  urgency text,
  top_condition text,
  case_json jsonb,
  result_json jsonb,
  record_json jsonb,
  created_at timestamptz default now()
);
```

For quick prototype testing with the public Streamlit app, enable RLS and add these policies:

```sql
alter table public.cases enable row level security;

create policy "Allow public insert cases"
on public.cases for insert
to anon
with check (true);

create policy "Allow public read cases"
on public.cases for select
to anon
using (true);
```

This public read/write setup is only for a prototype. For real clinic data, add authentication before storing client-identifiable records.

In Streamlit Cloud, add secrets:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-or-service-key"
SUPABASE_TABLE = "cases"
SUPABASE_CASE_SYNC_ENABLED = "true"
SUPABASE_STORE_FULL_CASE = "false"
```

`SUPABASE_CASE_SYNC_ENABLED` must be `true`; URL/key alone will not silently upload clinic cases. By default the app stores summary history only. If the vet explicitly wants full JSON case/result records in Supabase, set:

```toml
SUPABASE_STORE_FULL_CASE = "true"
```

Nested Streamlit connection secrets are also supported:

```toml
[connections.supabase]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-supabase-anon-or-service-key"
SUPABASE_TABLE = "cases"
SUPABASE_CASE_SYNC_ENABLED = "true"
SUPABASE_STORE_FULL_CASE = "false"
```

The app still works without these secrets, but then history is only local JSONL unless Google Sheets is configured.

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
4. No secrets are required for the app to run.
5. Supabase/Google Sheets secrets are only needed for cloud case history sync.
6. If changes do not appear, use Streamlit Cloud -> Manage app -> Reboot app or Clear cache and reboot.

## Best next improvements

- Add more vet-approved rows for goat, sheep, poultry, buffalo, horse, camel, and rabbit.
- Add PDF case report export.
- Add role-based login before storing real patient/client data.
- Add formal validation by the veterinarian before sharing with clients.
