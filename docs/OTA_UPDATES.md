# Over-the-air updates — the playbook

> **What this is.** Expo Update lets a JavaScript or asset fix reach a
> phone that already has TransitOS installed. No new APK, no Play Store
> review, no re-installation for the crew. The fix is on the phone the
> next time the app is opened.
>
> **What it does not do.** It cannot deliver a native change — a new
> permission, a new native library, a change to the app icon or the
> signing key. Those still need a new APK. See §4.

---

## 1 · The one thing that has to happen first

`expo-updates` is a **native** library. The update client lives in the
APK. So the APK the field is currently running **does not have an update
client**, and no update can reach it.

**One more APK has to be built and distributed.** That APK contains
`expo-updates` and every future JavaScript fix rides on top of it.

After that APK is in the field, the routine becomes:

```
a JavaScript fix  →  eas update  →  the crew's phones get it on next launch
a native change   →  eas build   →  a new APK, distributed the usual way
```

Both were already true in one sense — a native change always needed a
new APK — but until now *every* fix did.

> **Do not skip the first OTA-capable APK.** Shipping an update before
> any phone has an update client means the fix goes nowhere and looks
> like it shipped.

---

## 2 · Publishing a fix

From `frontend/`, with the EAS CLI logged in:

```bash
eas login                      # once per machine
cd frontend

# a fix for the internal testers
npm run update:preview

# a fix for the field
npm run update:production
```

Both scripts run `eas update --channel <name>`. The CLI asks for a
short message describing the change — that message is what the team
sees in the EAS dashboard, so write it like a commit message.

The full command, if you want it explicitly:

```bash
npx eas-cli update --channel production --message "Fix the cash-up variance display"
```

> `--environment` is **not** required on SDK 54. It becomes required
> when the project moves to SDK 55 or later; add
> `--environment production` then.

### What happens on the phone

1. The app starts and asks the update server whether anything newer
   exists for its runtime version.
2. If there is, the update is **downloaded in the background**. The app
   carries on working — the user is not blocked.
3. The update is **applied the next time the app is opened**. For a
   release build that means force-closing and reopening it, up to twice.

So a fix published at 09:00 is on the crew's phones by their first
journey of the following morning.

---

## 3 · Channels

A **channel** decides which builds receive an update. The channel is
baked into the binary when it is built and **cannot be changed
afterwards**.

| Channel | Build profile | Who has it | What it receives |
|---|---|---|---|
| `development` | `development` | Developers, with a development client | Everything, constantly |
| `preview` | `preview` | The internal testers | Preview updates only |
| `production` | `production` | The field | Production updates only |

This separation is the point: a fix published to `preview` can never
reach a driver's phone, whatever happens. The two channels are
configured in `frontend/eas.json` under `build.<profile>.channel`, and
`tools/contract/check_updates.py` fails the build if a profile has no
channel or two profiles share one.

The app tells the truth about itself: a build on any channel other
than `production` shows a **Preview build** strip on the dashboard, so
a tester cannot accidentally show an internal build to the client.

---

## 4 · What can and cannot go over the air

| Change | Over the air? |
|---|---|
| JavaScript / TypeScript — screens, logic, copy | ✅ yes |
| Styles, colours, fonts | ✅ yes |
| Images and other assets in `frontend/assets/` | ✅ yes |
| A new npm package that is pure JavaScript | ✅ yes |
| A new or changed **native** module (`expo-camera`, a camera plugin, a push SDK…) | ❌ new APK |
| A new **permission** in `app.json` | ❌ new APK |
| The app icon, splash screen, package name, bundle id | ❌ new APK |
| `app.json` fields that change the native project (`expo-build-properties`, the `expo-camera` plugin, `newArchEnabled`) | ❌ new APK |
| A change to `eas.json` channels | ❌ new APK (the channel is baked in) |

**How to tell:** if the change touches anything under
`frontend/android/` or `frontend/ios/`, or adds a package with native
code, it needs a new APK. If it is only `.tsx`, `.ts`, `.css` or an
asset, it goes over the air.

---

## 5 · Runtime version — the rule that trips people up

Every update is filed under a **runtime version**, and it is only ever
served to a binary with the same one. This project uses:

```json
"runtimeVersion": { "policy": "appVersion" }
```

so the runtime version is the app version — currently **1.2.0**.

That gives the behaviour you want:

- Fixes published while the field is on **1.2.0** reach every 1.2.0
  phone. ✅
- When a native change forces a new APK, the version goes to **1.3.0**,
  so the runtime version goes with it, and updates published for 1.2.0
  stop reaching those phones. ✅ Correct — a 1.3.0 binary must not
  receive a bundle built for 1.2.0.

> **The rule:** bump `version` in `frontend/app.json` whenever you
> publish a build, and **never** bump it for a JavaScript-only fix. If
> you bump the version for a JS-only fix, you have cut the field off
> from every update until the next APK.

`tools/contract/check_updates.py` also fails the build if the version
in `app.json` and the version in `package.json` disagree — they are
kept in step because the runtime version is derived from `app.json`.

> **One trap.** `eas.json` sets `cli.appVersionSource` to `remote`, so
> EAS takes the version from the Expo servers rather than from
> `app.json`. That is what makes `autoIncrement` work. The consequence
> is that an APK built **locally** (`eas build --local`) carries the
> `app.json` version, while updates published from the servers carry
> the remote one. If those differ, a locally built APK will not
> receive the updates you publish. Use cloud builds, or keep the two
> versions in step.

---

## 6 · Rolling a fix out to the fleet gradually

The field is not a website. A bad update reaches every driver at once.
EAS can stage a rollout:

```bash
# to 10% of the fleet
eas update --channel production --rollout-percentage 10 --message "Fix X"

# widen it once the first group looks right
eas update:edit <update-group-id> --rollout-percentage 50
eas update:edit <update-group-id> --rollout-percentage 100
```

`eas update:edit` without an id lists the update groups and asks
which one to change. The update-group id is printed by the publish
command and is in the EAS dashboard.

---

## 7 · Getting a bad update back

Three different tools, for three different situations.

| Situation | Command | What it does |
|---|---|---|
| The rollout is still going and you want to stop it | `eas update:revert-update-rollout` | Stops the rollout and returns everyone to the previous update |
| The update is already at 100% and is wrong | `eas update:rollback` | Publishes a new update that puts the previous update back |
| Nothing works and you want the version inside the APK | `eas update:roll-back-to-embedded` | Falls back to the JavaScript bundled in the APK |

`npm run update:rollback` runs the interactive `eas update:rollback`,
which asks whether to roll back to an earlier update or to the embedded
one.

> **Roll forward when you can.** If the bug is in the JavaScript, a
> second update fixes it in minutes. Roll back only when you cannot
> publish — for example when the update itself breaks the app on
> launch, before it can download its replacement.

---

## 8 · Checking that an update actually landed

**On the phone.** The app does not show the update id, so check it
this way:

1. Publish the update.
2. Force-close the app and reopen it (twice if needed).
3. Look at the change.

**From the dashboard.** <https://expo.dev> → your project → **Updates**
shows every published update group, its channel, its runtime version
and how many devices have fetched it.

**From the CLI.**

```bash
npx eas-cli update:view <update-group-id>
```

**The fingerprint.** When an update does not arrive, the usual reason
is that the update's runtime version does not match the binary's. This
compares the two:

```bash
eas fingerprint:compare --build-id <BUILD-ID>
```

---

## 9 · When an update does not arrive

| Symptom | Likely cause | What to do |
|---|---|---|
| Nothing changes after two restarts | The update was published for a different runtime version | Check `version` in `app.json` against the update's runtime version in the dashboard |
| Nothing changes | The build has no update client | The APK predates `expo-updates` — it needs the new APK (§1) |
| Nothing changes | The build is on another channel | A `preview` phone does not take `production` updates, and the other way round |
| The phone is on a build with no channel | It was built locally, not through EAS | A local build has no channel and no update server |
| The app is on the wrong code | The update was published but the branch was not the branch the channel points at | `eas update --channel <name>` publishes on the branch named after the channel by default — check the dashboard |
| The app crashes on launch after an update | The update broke the JavaScript | `eas update:rollback` — then fix forward |

---

## 10 · The rules, in one place

1. **One OTA-capable APK first.** Nothing ships over the air until the
   field has it.
2. **JavaScript and assets go over the air. Native changes do not.**
3. **Bump `version` when you publish a build. Never for a JS-only fix.**
4. **Test on `preview` before `production`.**
5. **Write a real message.** It is the only description the team gets.
6. **Keep `app.json` and `package.json` versions equal.**
7. **Run `python tools/contract/check_updates.py`** — it is in CI, and it
   catches a broken configuration before it ships.

---

## 11 · What is checked automatically

`tools/contract/check_updates.py` runs in CI and fails the build when:

- `expo-updates` is not a dependency;
- the update URL does not match this project's update server;
- no runtime version is declared;
- the version in `app.json` and the version in `package.json` disagree;
- a build profile has no channel, or two profiles share one;
- a publish script targets a channel that does not exist.

`backend/app/tests/test_update_config.py` proves each of those checks
actually fires, so the guard cannot rot into a check that always passes.
