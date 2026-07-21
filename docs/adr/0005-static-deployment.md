# ADR-0005 — Static Deployment Via Nginx; No Backend In V1

Status: Accepted

## Context

The v1 product scope is a static frontend fed by build-time data and does not require runtime APIs.

## Decision

Deploy the built web app as static assets served by nginx on a VPS. Do not introduce a backend in v1.

## Consequences

- Deployment stays simple and low-cost.
- Runtime application state is entirely client-side.
- Any future API or SSR work will require a new architectural decision.

## Trade-Offs

- Server-side auth, synchronization, and dynamic querying are unavailable in v1.
- Data refreshes require rebuilding and redeploying static assets.

## Implementation Notes

- TLS is terminated at nginx.
- Build artifacts should be publishable without application servers.

## Alternatives Considered

- Server-rendered app: rejected as out of scope for v1.
- Object storage hosting only: deferred until deployment requirements are better understood.

## Links To Relevant Code

- `deploy/nginx.conf`
