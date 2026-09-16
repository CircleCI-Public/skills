# User-handoff steps

Two steps never have a public API or CLI command, and a third falls back here on some VCS
integrations. **Give the user instructions; do not attempt them yourself.** Do not PATCH
internal endpoints, compose raw `curl`, or drive a browser (Playwright, etc.) — those
paths fail or create security risk for no gain.

The web app changes faster than this file. If a page does not look as described, trust the
page and tell the user this file is stale.

## Create the pipeline definitions (only when the API cannot)

Reach for this **only** when deploy and rollback pipelines are supported for the
integration but you could not create the definitions yourself. In practice that means
GitHub App or Enterprise Server where the CLI was missing, unauthenticated, or errored.

Check `api.md` first. On GitLab, Bitbucket Cloud, and Cursor Origin the feature
does not exist at all, so do **not** send the user here — the UI cannot create them
either. Say the integration does not support deploy and rollback pipelines, and that
markers and validation still work.

**On GitHub OAuth without the App, offer the real fix instead of these steps.** Installing
the CircleCI GitHub App is what makes deploy and rollback pipelines available; it coexists
with their OAuth integration and migrates nothing. It is an org-level action, so they may
need an admin.

Lead by saying you could not create these for them and why, so it does not read as an
oversight. Same page as the designation step:

```
https://app.circleci.com/settings/project/{vcsType}/{orgName}/{projectName}/deploys
```

They create two pipeline definitions, one per file. For each, give them the exact values
you would have sent:

| Field | Deploy | Rollback |
|-------|--------|----------|
| Name | `deploy` | `rollback` |
| Config file path | `.circleci/deploy.yml` | `.circleci/rollback.yml` |

Both point at the same repository the project already uses — they should not need a repo ID
by hand in the UI. Tell them to create both **before** moving on to designation, since the
dropdowns there only list definitions that already exist.

Then verify with `circleci pipeline list --json` if a token is available, and confirm both
names appear with the right `file_path`.

## Designate the deploy and rollback pipelines

After the pipeline definitions exist — created by you in step 9, or by the user above —
tell the user:

1. Open the project deploy settings page:

   ```
   https://app.circleci.com/settings/project/{vcsType}/{orgName}/{projectName}/deploys
   ```

   Substitute their actual VCS type, org, and project — do not leave placeholders.
   `{vcsType}` is `gh` or `bb` for classic GitHub and Bitbucket orgs, and `circleci` for
   `circleci`-type orgs, where the org and project segments are ids rather than names. If
   you cannot construct it confidently, do not guess a URL — tell them to open the project
   and go to **Project Settings → Deploys**, which is the same page.

2. On the **Deploy pipeline** card, select the definition named `deploy` (the one pointing
   at `.circleci/deploy.yml`) and save.

3. On the **Rollback pipeline** card, select the definition named `rollback` (the one
   pointing at `.circleci/rollback.yml`) and save.

4. Ask them to confirm when done.

Then verify yourself:

```bash
circleci api api/v2/deploy/projects/{project_id}/settings
```

Both `deploy_pipeline_definition_id` and `rollback_pipeline_definition_id` should be set
and should match the ids from `circleci pipeline list`. If either is missing or points at
a stale definition, say so plainly.

## Mint the validation webhook secret

Tell the user:

1. Open the org deploy settings page:

   ```
   https://app.circleci.com/settings/organization/{vcsType}/{orgName}/deploys
   ```

2. On the **Webhook secrets** card, generate a new secret. Copy it immediately — it is shown
   once and cannot be re-read.

3. Paste it straight into their monitoring provider (see `monitoring.md`).
   Do not paste it into the chat.

Minting is an org-level action. If they lack permission, say so plainly.

## Writing instructions well

The instructions are the deliverable. For each step:

- give the full URL with the user's actual org, project, and VCS substituted in
- name the card and the button as they appear on screen
- say exactly which value to select (for example the pipeline definition name you created)
- state what they should see afterwards, so they can confirm success
- tell them to come back so you can verify through the public API

Do not simply paste a path template with placeholders and leave the user to fill them in.
