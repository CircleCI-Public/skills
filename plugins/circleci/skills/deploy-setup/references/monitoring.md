# Monitoring setup

Validation needs two things on the monitoring side: a **webhook** that posts to CircleCI
with the right auth header and payload, and **monitors** that call that webhook and carry
tags matching the deploy markers.

**You do not configure this yourself. The user does.** Your job is to produce
instructions precise enough to follow without guesswork, then verify the result.

This is deliberate. The webhook needs a CircleCI secret and the monitoring provider's own
credentials, and routing all three through an agent is both a security problem and a
support problem. Automating it belongs in the CircleCI CLI, where token handling already
lives — not here. Until then, hand off cleanly.

## Why handing off is the safer design

The secret is displayed once when minted. If the user mints it and pastes it straight into
their monitoring tool, **it never enters your context, any transcript, or any log.** That
is strictly better than any arrangement where you hold it.

So the rules are simple:

- Never ask the user to paste a secret into the chat. If they do anyway, tell them it is
  now in the transcript and should be revoked and reminted.
- Never run a command containing the secret, and never construct one. Give the user the
  command with a placeholder and let them substitute it themselves.
- Never write a secret into a repo file.

You still need the **org UUID** and the `webhooks[].name` values to write the
instructions. Neither is secret.

## What must be true, for any provider

The contract is the same everywhere; only the vendor UI differs.

**1. The webhook posts to the org's ingest URL:**

```
https://circleci.com/api/v3/deploy/hooks/{ORG_UUID}/validate
```

The `hook-id` segment is the organization UUID — anything else is rejected as 403. It is
knowable before any config is committed, so monitoring can be set up at any point.

**2. It authenticates with the minted secret:**

```
Authorization: Bearer CCIVWH_…
```

**3. Its JSON body carries a failure signal and the release identity.** The signal tells
CircleCI whether this is a firing alert; the identity tells it which release the alert
belongs to.

**4. Monitors both call the webhook and carry matching tags.** See
[Tagging](#tagging-monitors) — this is where setups usually break.

## Minting the secret

Direct the user to:

```
https://app.circleci.com/settings/organization/{vcsType}/{orgName}/deploys
```

They use the webhook secrets card, generate a secret, and **copy the value immediately** —
it is shown once and cannot be re-read. Existing secrets can be listed and revoked there,
but never viewed again.

Tell them to keep it on the clipboard and go straight to the monitoring provider, so it is
never written down anywhere.

Minting is an org-level action. If they lack permission, say so plainly rather than
suggesting workarounds.

## Datadog

The worked example. Other providers follow the same contract.

### Create the webhook

Have the user go to **Integrations > Webhooks** in Datadog and add a new webhook:

| Field | Value |
|-------|-------|
| Name | `circleci-validation` (referenced from monitors as `@webhook-circleci-validation`) |
| URL | `https://circleci.com/api/v3/deploy/hooks/{ORG_UUID}/validate` |
| Encode as | JSON |
| Custom Headers | `{"Authorization": "Bearer <paste the CCIVWH_ secret>"}` |
| Payload | see below |

```json
{"provider":"datadog","alert_transition":"$ALERT_TRANSITION","tags":"$TAGS"}
```

`$ALERT_TRANSITION` and `$TAGS` are Datadog template variables, substituted at send time.
Leave them written exactly like that — they are not placeholders for you to fill in.
`alert_transition` becomes `criteria`, which the default Datadog `fail_when` tests for
`"triggered"` or `"re-triggered"`. `$TAGS` carries the release identity.

Substitute the real org UUID into the URL before showing it. Leave the secret as a
placeholder.

### If the user prefers the API

Give them this to run themselves. **Do not run it for them** — it contains all three
secrets.

```bash
# Your Datadog site. A wrong value returns a confusing 403 rather than a helpful error.
# One of: datadoghq.com us3.datadoghq.com us5.datadoghq.com datadoghq.eu
#         ap1.datadoghq.com ap2.datadoghq.com ddog-gov.com
DD_SITE="datadoghq.com"
ORG_UUID="<your CircleCI org UUID>"

# Prompts without echoing, so the secret stays out of your shell history.
read -rsp 'CCIVWH secret: ' CCI_SECRET && echo

body=$(jq -nc \
  --arg auth "Bearer ${CCI_SECRET}" \
  --arg url "https://circleci.com/api/v3/deploy/hooks/${ORG_UUID}/validate" \
  '{
     name: "circleci-validation",
     url: $url,
     encode_as: "json",
     payload: "{\"provider\":\"datadog\",\"alert_transition\":\"$ALERT_TRANSITION\",\"tags\":\"$TAGS\"}",
     custom_headers: ({Authorization: $auth} | tostring)
   }')

curl -sS -X POST \
  "https://api.${DD_SITE}/api/v1/integration/webhooks/configuration/webhooks" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H 'Content-Type: application/json' \
  -d "$body"

unset CCI_SECRET body
```

The `$ALERT_TRANSITION` and `$TAGS` inside `payload` are Datadog's own template variables,
not shell variables. They survive because the jq program is single-quoted — keep it that
way if you edit this.

Requires the `create_webhooks` permission.

## Tagging monitors

Every monitor feeding validation needs **both** of the following. Missing either produces
silence, not an error.

**Notify the webhook.** Add `@webhook-circleci-validation` to the monitor's notification
message. Without it the monitor never calls the webhook at all — the most common reason a
correctly configured setup produces nothing.

**Carry matching tags.** Parsed as `key:value`:

| Tag | Required | Must match |
|-----|----------|------------|
| `component_name` (or `app` / `service`) | yes | `--component-name` in the deploy marker |
| `env` (or `environment`) | yes | `--environment-name` in the deploy marker |
| `signal_name` (or `alert_name`) | when routing several webhooks | `validation.webhooks[].name` |
| `namespace` | when markers set one | `--namespace` |
| `version` | **usually omit** | — |

These are **exact-match** filters. A trailing space, or `prod` against `production`,
silently stops matching.

Generate these values from the same variables you used for the markers and present them to
the user as literal strings to copy. Never let them be typed independently on both sides.

Omit `version` unless the monitor is multi-alert grouped by a version tag. A static
`version` tag cannot track the deployed version, so it matches the first release and then
never again. When absent, any version matches — which is what you want.

Datadog reads `signal_name` from `request.tags.alert_name`, `request.tags.signal_name`,
`request.alert_name`, or `request.signal_name`. Note Datadog uses **`alert_name` with an
underscore**, unlike the Grafana family's `alertname`.

## The named providers

`datadog`, `alertmanager`, `prometheus`, `grafana`, and `custom`. `custom` is the default
when `provider` is omitted.

Alertmanager, Prometheus, and Grafana share one mapping, reading from `groupLabels`:

- `component_name` from `groupLabels.component_name`, `groupLabels.app`, `groupLabels.service`
- `env` from `groupLabels.env`, `groupLabels.environment`
- `signal_name` from `groupLabels.alertname`, `groupLabels.signal_name`, `alertname`
- `criteria` from `status`, with default `fail_when` of `criteria == "firing"`

Alertmanager's native webhook payload already carries `groupLabels` and `status`, so it
usually needs no custom body — just the URL and the `Authorization` header, with the
identifying labels present on the alert.

## Any other tool also works — say so

**That list is not a compatibility list.** It is the set of tools whose payload shapes are
already known, so their defaults work with no mapping. `provider: custom` exists precisely
so anything else can be wired up, and the bar is low:

> Any tool that can send an HTTP POST to a URL with a custom header, when an alert fires,
> can drive release validation.

That covers most of the market — New Relic, Honeycomb, Sentry, Dynatrace, Splunk,
CloudWatch, PagerDuty, Zabbix, Nagios, Better Stack, Checkly, and plenty of in-house
alerting. **Mention this when you ask about monitoring in step 2.** Users routinely assume
an unlisted tool means "not supported" and silently drop validation from the scope, which
is the wrong outcome — say up front that other tools are fine and ask what they use.

### When the user names a tool you do not know

Do not guess at its payload, and do not tell them it is unsupported. Find out.

**1. Pull the tool's own documentation.** Search for its outbound alerting integration —
the feature names vary: "webhook notification", "notification channel", "alert action",
"outbound integration", "custom webhook", "HTTP action". Read the actual reference, not a
blog post, because the answer you need is the exact payload shape.

**2. Answer these four questions from the docs.** They determine everything that follows:

| Question | Why it matters |
|----------|----------------|
| Can it send a webhook when an alert fires or resolves? | If no, the tool cannot drive validation at all |
| Can it set custom request headers? | Needed for `Authorization: Bearer`. See the fallback below if not |
| Is the request body **templatable**, or a fixed vendor shape? | Decides which of the two paths below you take |
| What template variables expose alert name, tags/labels, and firing state? | These become the release identity and the failure signal |

**3. Take the matching path.**

**Path A — templatable body (much preferred).** Have the tool emit the shape CircleCI
already understands, and change nothing in the config. Keep `provider: custom` and its
defaults:

```json
{
  "signal_name": "<the tool's alert-name variable>",
  "status": "<the tool's firing-state variable>",
  "tags": {
    "component_name": "my-service",
    "env": "staging"
  }
}
```

`signal_name`, `status` and `tags.*` are all paths the `custom` mapping reads, so this works
with no `data_points` override. This is the better path whenever the tool allows it —
mapping is something else to get wrong.

**Path B — fixed vendor body.** Map their shape to the variables with `data_points`, a
plain `variable → path` map. Paths are dot-notation and **prefixed with `request.`**, where
`request` is the received body:

```yaml
validation:
  enabled: true
  webhooks:
    - name: error_rate
      provider: custom
      data_points:
        component_name: request.data.attributes.service
        env: request.data.attributes.environment
        signal_name: request.data.attributes.condition_name
        criteria: request.data.attributes.state
      fail_when: criteria == "open"
```

Only override the variables whose location actually differs; the rest keep their defaults.

### Rules that bite on custom mappings

**`fail_when` can only reference known variables.** Valid names are the keys you declare in
`data_points` plus the provider's built-ins — `component_name`, `version`, `namespace`,
`project_id`, `env`, `criteria`, `signal_name`. Referencing anything else is a config
error, caught at parse time. To threshold on a vendor-specific number, declare it in
`data_points` first, then use it:

```yaml
      data_points:
        criteria: request.state
        error_count: request.metric.value
      fail_when: criteria == "open" and error_count > 10
```

**Write `fail_when` in lowercase, and check the payload's case.** The expression is
lowercased server-side, the payload values are not. So `criteria == "Firing"` becomes
`criteria == "firing"` and then never matches a payload sending `"Firing"`. If the tool
emits capitalised states and you cannot change them, map `criteria` to a field that is
lowercase, or reconsider Path A.

**`criteria` has only two default paths for `custom`** — `request.alert_transition` and
`request.status`. Anything else needs an explicit `data_points.criteria`.

**If the tool cannot set custom headers**, it cannot authenticate, and there is no query
-parameter alternative. Options, in order: check for a generic "HTTP action" that does
support headers, route through something that can (an Alertmanager instance, a small
relay), or fall back to `agentic` validations if the tool has an MCP server. Say plainly
that the direct webhook path is closed rather than improvising.

**Where `provider: custom` looks for the signal name.** Six paths, tried in order, so you
do not need `data_points` for this field if the payload puts it in one of them:

```text
groupLabels.alertname   tags.alertname   groupLabels.signal_name
tags.signal_name        alertname        signal_name
```

Prefer moving the payload onto one of these (Path A) over adding a `data_points` override.

### Verify a custom mapping before trusting it

A mapping is a guess about someone else's payload until you have seen the payload. Have the
user trigger the monitor once and read the delivery log in their tool, which shows the body
actually sent — then compare it against your `data_points` paths field by field. This is
cheap and catches the wrong-nesting mistake that otherwise surfaces as silence at step 12.

Full field semantics are in `validation.md`.

## Verifying

Ask the user to confirm the webhook exists and the monitor references it, then verify what
you can yourself.

A test POST to the ingest URL proves the URL, token, and payload shape. It **cannot** prove
matching — the endpoint returns success even when nothing matches. See
`validation.md`.

For the monitor side, have the user trigger or resolve the monitor and check the webhook's
delivery log in their provider. To confirm matching end to end, run a real deploy and
inspect the resulting validation plan. There is no shortcut, and no amount of
configuration review substitutes for it.
