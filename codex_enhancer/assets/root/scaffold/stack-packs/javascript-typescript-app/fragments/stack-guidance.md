Use this pack when the repo has `package.json` plus recognizable JavaScript or TypeScript build tooling.

- Keep the existing package manager and lockfile intact.
- Prefer the repo's actual scripts over guessed framework defaults.
- If the repo exposes typechecking, treat it as part of the normal validation loop.
- Keep toolchain changes aligned with the existing config instead of swapping tools casually.
