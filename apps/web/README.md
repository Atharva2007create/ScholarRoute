# ScholarRoute web

Production Next.js frontend for the ScholarRoute college and scholarship discovery journeys.

## Local development

1. Copy `.env.example` to `.env.local` and set `NEXT_PUBLIC_API_BASE_URL` to the Phase 6 API origin.
2. Run `npm install`.
3. Run `npm run dev`.

Validation commands: `npm test`, `npm run typecheck`, `npm run lint`, and `npm run build`.

Search values and the latest response are kept in browser session storage so Back to Search restores the current journey without indefinitely persisting profile data.
