Use this pack when `package.json` exposes reusable package metadata such as `exports`, `main`, `module`, `types`, `files`, or `bin`.

- Treat package entrypoints, generated declarations, and published files as contract-sensitive surfaces.
- Keep source entrypoints, build output, package metadata, and docs aligned when any public API changes.
- Prefer the repo's existing build, pack, test, and typecheck commands over invented release steps.
- Call out semver or migration impact when exports, types, runtime behavior, or supported platforms change.
- Do not use app-only validation guidance unless another selected pack, such as frontend or API service, also applies.
