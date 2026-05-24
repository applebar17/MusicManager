# Music Manager

Local-first desktop app for mirroring SoundCloud playlist knowledge, matching it to
local audio files, and preparing USB folder exports for DJ use.

## Shape

- `backend/` - Python backend, domain logic, adapters, and local API.
- `apps/desktop/` - Tauri desktop shell with a TypeScript frontend.
- `docs/` - product, requirements, domain, architecture, and decision notes.

The current codebase is a scaffold. Requirements are captured in [docs](docs/README.md).

See [scaffold notes](docs/development/scaffold.md) for the layer boundaries.

## Local Docker Workflow

Use Docker when the host machine cannot run the required Node 20 frontend toolchain.

Start the backend and browser-based desktop frontend:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:1420
```

The frontend container runs with Node 20. Browser API calls go through the Vite
dev-server proxy, which forwards to the backend container at
`http://backend:8000`, avoiding local CORS friction. Backend data is stored under
the repo-local `local/` directory, which is ignored by git.

Run the full containerized validation gate:

```bash
docker compose -f compose.ci.yml build --no-cache
```

That CI image runs backend migrations, lint, typecheck, tests, frontend
TypeScript checks, frontend tests, and the Vite desktop build. It does not create
a native macOS Tauri installer; producing `.app` or `.dmg` artifacts still needs a
macOS build environment with Node 20 and Rust.
