## 2026-11-09 — Reconcile the Core HA-dev baseline

### Repository Status

The protected source merges are [#1439](https://github.com/pcvantol/djconnect/pull/1439) at `3505dcb29db96586fa3d8cd6b17f788413763a63`, [#1530](https://github.com/pcvantol/djconnect/pull/1530) at `980b3f0575c01e0e4d6d9a6e83d1f49858fecd83`, [#1524](https://github.com/pcvantol/djconnect/pull/1524) at `fc206a720a456ae848b356ead64fb3d18f917564`, and [#1471](https://github.com/pcvantol/djconnect/pull/1471) at `5f9edc5832ba5beb8cd6d870bd1de8519e3372af`. The source component tree is `5fba5d76bfbb05dac62b73bd6ce61be99df3ef4c`. [Core main validation](https://github.com/pcvantol/djconnect/actions/runs/42596501856)

### Management Summary

The baseline keeps Watch preference forwarding, automatic enrollment after normal pairing, and the retained Moment handoff as separate Core increments. New WidgetKit consent remains off by default and can be withdrawn per device and channel. The owner requested a development installation on HA-dev after merging the eligible Core work. [#1539](https://github.com/pcvantol/djconnect/pull/1539) remains open for Dutch Ask DJ quality work.

### Engineering Status

The retained publication candidate passed 4,792 local Core tests with 11 skips and 45 isolated Home Assistant contract probes. The enrollment component separately passed 12 isolated scenarios with fixture issuer and publisher boundaries. The older VibeCast artwork and Session feed proposals were closed after their functionality landed together. [#1535](https://github.com/pcvantol/djconnect/pull/1535)

HA-dev installation and runtime readback are separate from source and CI. Public issuer and surface readiness, device enrollment, APNs acceptance and physical display remain separately qualified. This record grants no production activation or official Ask DJ release qualification.

