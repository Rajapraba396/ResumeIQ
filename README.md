# ResumeIQ

ResumeIQ extracts text from PDF and TXT resumes, then returns structured resume analysis.

## Run locally

Install the backend dependencies and start the API from the project root:

```powershell
py -m venv .\backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload
```

In another terminal, install frontend dependencies and start Vue:

```powershell
npm install
npm run dev
```

## Gemini configuration

Copy `backend/.env.example` to `backend/.env` and set `GEMINI_API_KEY` to a Google Gemini API key. The key is read only by the backend and must not be placed in frontend configuration. The model is `gemini-3.8-flash`.

When no key is configured, `/api/resumes/analyze` returns explicitly labelled **DEMO MODE** results based on basic keyword and section matching. These results are not AI-generated.

If Gemini reports that the key is invalid, create or copy a valid key from [Google AI Studio](https://aistudio.google.com/apikey), replace the value of `GEMINI_API_KEY` in `backend/.env`, remove any stale `GOOGLE_API_KEY` entry, and restart the backend. Never paste the key into Vue files, source control, or chat.
