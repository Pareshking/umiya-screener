# Next Audit — Phase 5 Closure

Phase 5 is not formally closed yet.

## Single remaining action

Verify/configure the actual Cloudflare R2 bucket lifecycle/retention policy.

### Recommended initial configuration

```text
Historical datasets:
  datasets/  → expire after 30 days
  metrics/   → expire after 30 days

Never expire through this rule:
  pointers/

Incomplete multipart uploads:
  abort after 7 days
```

The 30-day value is a proposed starting point and should be confirmed against the desired rollback window.

### Verification checklist

- [ ] Open the actual production R2 bucket.
- [ ] Inspect Settings → Object Lifecycle Rules.
- [ ] Confirm historical `datasets/` retention.
- [ ] Confirm historical `metrics/` retention.
- [ ] Confirm `pointers/` is not accidentally covered by the delete rule.
- [ ] Confirm the active/latest dataset remains available.
- [ ] Configure the rule if absent or incorrect.
- [ ] Save and re-check the final rule configuration.
- [ ] Record the final retention period in this repository.

Cloudflare's current R2 documentation supports lifecycle rules by prefix and age, and provides dashboard/Wrangler/API methods to inspect and configure them.

## APCOTEXIND clarification

`APCOTEXIND.NS` is a data-pipeline test fixture only. It was never intended to appear in the production frontend.

## After this action

Mark Phase 5 complete, then start Phase 6 with real deployed performance and UX measurements.
