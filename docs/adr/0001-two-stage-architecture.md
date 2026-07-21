# ADR-0001 — Two-Stage Architecture: Offline Parser + Static Web App

Status: Accepted

## Context

The product must keep personal financial data local, avoid runtime backend infrastructure in v1, and support deterministic imports from bank statement PDFs.

## Decision

Use a two-stage architecture:

- A Python parser reads local PDF statements offline and produces normalized JSON.
- A React web app consumes that JSON statically at build time.

## Consequences

- Personal financial data remains in local files under user control.
- Deployments stay simple because the web app is static.
- Data refreshes require rerunning the parser and rebuilding the frontend.

## Trade-Offs

- There is no live synchronization or server-side querying.
- Import failures must be debugged locally at parse time.
- The frontend must tolerate build-time rather than runtime data updates.

## Implementation Notes

- The parser package is responsible for PDF extraction, normalization, and JSON serialization.
- The web app must not make outbound network requests for transaction data.

## Alternatives Considered

- A server-backed app with uploaded PDFs: rejected for privacy and operational complexity.
- A frontend-only PDF parser in the browser: rejected due to parser portability and testability constraints.

## Links To Relevant Code

- `parser/src/lethal_expenses/`
- `web/src/`
