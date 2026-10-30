# Productization map

Where the product stands against the surface it declares. This map points at
the generated sources rather than restating their numbers: a count typed here
would go stale the first time a page was added, which is exactly how one
document came to describe the same application with three different endpoint
counts at three different times.

| question | the answer lives in |
|---|---|
| what interfaces does the product declare? | `docs/INTERFACE_REGISTRY.md`, generated from `core/interfaces` |
| what endpoints does the application actually serve? | `docs/endpoint_inventory.json`, generated from the built application |
| does every page belong to an interface? | `docs/REGISTRY_EVIDENCE.md`, part two |
| what is still legacy? | the lifecycle section of `docs/REGISTRY_EVIDENCE.md`, and `LEGACY_INTERFACE_IDS` in `core/interfaces` |
| what does a page look like and how is it reached? | `docs/EXPERIENCE_CONTRACT.md` |

## What "legacy" means here

Three things were legacy before the registry: routes that existed only to be
linked to, deprecation knowledge that lived in prose, and counts that lived in
whatever document was written last. Each has a single owner now - the registry
for the first two, the generators for the third - so "legacy" describes code
that predates the interface model, not figures nobody maintains.

## The gap this map does not close

Registering an interface does not make its page good, and a green coverage
check does not say that a screen is finished. The remaining work is measured
elsewhere: `docs/COMPONENT_LIBRARY.md` for the presentation layer,
`docs/ACTION_SURFACE_AUDIT.md` for what the action model cannot yet express,
and `docs/SCREEN_INSPECTOR_EVIDENCE.md` for what a screen is composed of.
