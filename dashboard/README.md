# Operator dashboard

Next.js UI for the control plane. Login, businesses, agents, and encrypted provider credentials.

Setup, architecture, and configuration live in the [repository README](../README.md). From this directory, after the API is running:

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000 and sign in with the tenant owner created via `POST /api/v1/tenants`. There is no signup screen.
