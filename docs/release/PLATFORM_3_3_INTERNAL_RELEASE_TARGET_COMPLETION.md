# Platform Release 3.3 — Internal Release Target Completion

Date: 2026-07-19
Decision: `PLATFORM_RELEASE_3_3_INTERNAL_TARGETS_QUALIFIED`

## Scope

All required targets in manifest `release-3.3.0-internal-20260714` have a
separately authorized, exact-artifact deployment and separate post-deployment
smoke record.

| Required target | Deployment | Smoke | Result |
| --- | --- | --- | --- |
| Home Assistant Pi 5 | [29683604435](https://github.com/pcvantol/djconnect/actions/runs/29683604435) | [29683901389](https://github.com/pcvantol/djconnect/actions/runs/29683901389) | Qualified |
| API Workers | [29364714166](https://github.com/pcvantol/djconnect-api/actions/runs/29364714166) | [29364851135](https://github.com/pcvantol/djconnect-api/actions/runs/29364851135) | Qualified |
| Website Pages | [29441732130](https://github.com/pcvantol/djconnect-website/actions/runs/29441732130) | [29441809581](https://github.com/pcvantol/djconnect-website/actions/runs/29441809581) | Qualified |
| ESP32 LilyGO | [29446964025](https://github.com/pcvantol/djconnect-esp32/actions/runs/29446964025) | [29447045601](https://github.com/pcvantol/djconnect-esp32/actions/runs/29447045601) | Qualified |
| Raspberry Pi | [29361051673](https://github.com/pcvantol/djconnect-pi/actions/runs/29361051673) | [29361739009](https://github.com/pcvantol/djconnect-pi/actions/runs/29361739009) | Qualified |
| macOS | [29452344685](https://github.com/pcvantol/djconnect-app/actions/runs/29452344685) | [29452385823](https://github.com/pcvantol/djconnect-app/actions/runs/29452385823) | Qualified |
| iPhone + paired Watch | [29453894383](https://github.com/pcvantol/djconnect-app/actions/runs/29453894383) | [29455024770](https://github.com/pcvantol/djconnect-app/actions/runs/29455024770) | Qualified |
| iPad | [29627667215](https://github.com/pcvantol/djconnect-app/actions/runs/29627667215) | [29679738565](https://github.com/pcvantol/djconnect-app/actions/runs/29679738565) | Qualified |
| Windows ARM64 | [29583151393](https://github.com/pcvantol/djconnect-windows/actions/runs/29583151393) | [29588039127](https://github.com/pcvantol/djconnect-windows/actions/runs/29588039127) | Qualified |

## Closure boundary

This closes only the Internal Release target-deployment and immediate
post-deployment-smoke scope. It does not start or satisfy operational burn-in,
public distribution, rollback exercises or Platform Release Certification.
Those activities require separate authorization and their own evidence.
