# Production data coverage

Generated from canonical PostgreSQL data and the checked-in authoritative source manifest.

## Sources

| Source | Authority | Domain | Year | Format | Status | Last retrieved | Notes |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| JoSAA Participating Institutes | Joint Seat Allocation Authority | engineering_institutions | 2026 | HTML_TABLE | FETCHED | 2026-09-11T06:58:16.493448+00:00 | Contains 138 source-coded participating institutes, addresses, contacts and official websites. |
| JoSAA 2026 Opening and Closing Ranks - Round 5 | Joint Seat Allocation Authority | engineering_cutoffs | 2026 | ZIP_HTML | FETCHED | 2026-09-11T06:58:58.168762+00:00 | Fetch combines the four official institute-type result tables into one reproducible HTML snapshot. |
| JoSAA 2026 Seat Matrix | Joint Seat Allocation Authority | engineering_seats | 2026 | HTML_TABLE | FETCHED | 2026-09-11T06:59:11.344683+00:00 | Category, quota and gender-pool seat counts including supernumerary seats. |
| MCC NEET UG 2026 Round 1 Seat Matrix | Medical Counselling Committee | medical_seats | 2026 | PDF_TABLE | FETCHED | 2026-09-11T06:59:13.342241+00:00 | Eight columns: state, institute type, institute, quota, branch, category, total seats, seat gender. |
| MCC NEET UG 2026 Round 1 Final Allotment Result | Medical Counselling Committee | medical_admissions | 2026 | PDF_TABLE | FETCHED | 2026-09-11T06:59:15.085154+00:00 | Eight columns: serial, rank, quota, institute, course, allotted category, candidate category, remarks. |
| NMC MBBS Seat Matrix 2026-27 | National Medical Commission | medical_regulatory_seats | 2026 | PDF_TABLE | FETCHED | 2026-09-11T06:59:57.893356+00:00 | Current MBBS recognition/intake cross-check; institute rows begin after the state summary. [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1032) Local TLS chain validation is unavailable; the URL was verified on the official NMC page before retrieval. |
| Top Class Scholarship for SC Students Guidelines | Department of Social Justice and Empowerment | scholarships | 2026 | PDF_TEXT_TABLES | FETCHED | 2026-09-11T06:59:18.961102+00:00 | The portal labels this 2026-27; the PDF states guidelines are applicable from 2025-26. |
| PM-USP CSSS FAQ 2025-26 | Department of Higher Education | scholarships | 2025 | PDF_TEXT | BLOCKED | not retrieved | Search indexing confirms the official document, but the Ministry origin currently returns 404. |

## Canonical coverage

```json
{
  "engineering": {
    "institutions": 96,
    "programs": 657,
    "branches": 148,
    "cutoff_rows": 8428,
    "seat_rows": 8557,
    "years": [
      2025,
      2026
    ]
  },
  "medical": {
    "institutions": 31,
    "mbbs_programs": 31,
    "cutoff_admission_rows": 124
  },
  "scholarships": {
    "providers": 3,
    "schemes": 3,
    "cycles": 3,
    "rules": 3
  },
  "quality": {
    "ingestion_runs": 6,
    "records_staged": 8603,
    "validation_errors": 14,
    "official_links": 836,
    "institutions_missing_url": 0
  }
}
```
