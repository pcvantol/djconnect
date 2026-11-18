# Engineering dashboard loading fix

**Status:** Implemented through PR #644
**Implementation merge:** `0d1d7912318cde580ab8c477070ddc6758a9186c`

## Immutable implementation prompt

```text
fix die loading hang
```

## Outcome

The private, read-only Engineering Status dashboard now renders a complete
degraded status when its local status projection is absent or unavailable. It
does not gain transaction, Product, Runtime, Release, Deployment or publication
authority.
