# Deploy after pushing to GitHub

Deployment is prepared, not performed. The owner will push the code and choose a
hosting service. The app needs one Python process, WebSocket support, HTTPS and a
persistent local filesystem. Ephemeral storage loses both memory and conversations.

## Render Blueprint

`render.yaml` defines one native Python web service, a 1 GB disk at `/data`, and a `/health`
check. Render persistent disks require a paid service and cannot be shared between
instances; see [persistent disks](https://render.com/docs/disks) and
[Blueprint specification](https://render.com/docs/blueprint-spec).

1. Push the repository to GitHub. Check `git status --ignored` and confirm `.env`,
   `data/`, credentials and database files are ignored. Do not upload those files.
2. In Render, create **New → Blueprint**, connect the GitHub repository and select
   its branch. Render reads `render.yaml`, installs the locked dependencies with uv,
   and starts Chainlit on its assigned port.
3. Supply `OPENROUTER_API_KEY` with credits/model access, and `TEST_ACCOUNTS_JSON`.
   The configured model is `deepseek/deepseek-v4.1-flash`.
   For the latter, copy the JSON **value** from your private local `.env`, without
   the dotenv wrapper quotes; preserve the dollar signs in the password hashes.
   The setup script can create your two accounts before deployment. Passwords are
   the ones you chose or the private local generated credentials.
4. Keep the generated `CHAINLIT_AUTH_SECRET` stable across redeploys. The Blueprint
   sets `DATA_DIR=/data`, one instance, and HTTPS Secure cookies. The Render origin
   is added automatically from `RENDER_EXTERNAL_URL`. If using a custom domain,
   set `APP_URL=https://your-domain` too.
5. Deploy. Open the HTTPS service URL and sign in. Check recommendations, a temporary
   budget override, remembered preferences and resuming a conversation.
   Test both users, new conversation, resume and a service restart. The built-in
   `/health` endpoint confirms process health, not model entitlement or model quality.
6. Restart/redeploy and confirm the same conversation/profile can be resumed.
   Keep the disk attached. Do not scale the service to multiple processes/instances.

The native service uses the platform runtime user for its persistent disk, avoiding
container volume ownership differences. Its build and start commands are in
`render.yaml`; the disk is needed only at runtime. The lockfile also supports the
included Docker image for other providers.

## Other Docker hosts / local container verification

For Docker CLI use an ignored `.env.docker` containing the same configuration as
`.env`, with **unquoted** values (including the JSON account mapping). Docker CLI
`--env-file` does not remove dotenv wrapper quotes. Keep this file private.

```sh
docker build -t restaurant-menu-assistant-menu .
docker volume create restaurant-menu-assistant-data
# Ensure a mounted volume is writable by the image's application user.
docker run --rm --user root -v restaurant-menu-assistant-data:/data --entrypoint chown restaurant-menu-assistant-menu 10001:10001 /data
docker run --rm --env-file .env.docker -e DATA_DIR=/data -p 8000:8000 -v restaurant-menu-assistant-data:/data restaurant-menu-assistant-menu
```

Use `CHAINLIT_COOKIE_SAMESITE=lax` for local HTTP, `none` for deployed HTTPS. Bind a
persistent volume at `DATA_DIR`, preserve the auth secret, and configure `APP_URL`
for the public origin. A static-site host or Sites deployment cannot run this Python
WebSocket/SQLite service.

## Storage operations

Back up **both** SQLite databases together while the application is stopped, including
any WAL files if present. Alternatively use SQLite’s backup API for each DB during a
maintenance window without in-flight turns. Copying an active database file without
its WAL can lose committed data. Checkpoint/profile commits are separate transactions;
a consistent cross-database backup needs a pause in incoming turns.

Conversation deletion removes that thread and its checkpoints, while current profile
and preference history remain. “Forget” removes current preference values while
retaining assignment-required audit evidence. Full personal-data deletion and retention
policy tooling are outside this baseline and must include both stores and backups.

No Docker build or hosted deployment was claimed in the local validation: Docker
Desktop was unavailable. The Python app, health/auth HTTP responses, browser login,
memory view and checkpoint/history adapter were checked locally. Run the deployment
smoke steps after configuring your deployed environment. The hosted deployment still needs its own smoke check.
