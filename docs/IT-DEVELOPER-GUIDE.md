# IT Developer Guide

### How to brief, drive and verify a developing agent so the codebase ships working

*Project-agnostic. Nothing here is specific to one app. The examples are
drawn from a real build where three successive testing passes found three
production bugs that the first two passes had declared clean.*

---

## 0. The whole thing on one page

```
  BRIEF ──▶ BUILD ──▶ PASS A ──▶ PASS B ──▶ PASS C ──▶ GATE ──▶ DELIVER
            (agent)   compiles   interfaces  runtime    checklist  sign-off
```

**The rule that makes it work:** each pass can only find what the previous
one *cannot* see. A pass that repeats the last one finds nothing, and
"nothing found" gets reported as "all good" — which is how three real
bugs survived a green test suite.

| Pass | Question it answers | Catches |
|---|---|---|
| **A — compiles** | Does it build at all? | Type errors, missing imports, broken builds |
| **B — interfaces** | Do the two halves agree on names and shapes? | Wrong field names, wrong HTTP method, missing required fields |
| **C — runtime** | Does it actually work when you call it? | 404, 405, 422, 500, dead features, silent data loss |

Then the **gate** (§5) before you let anyone near a client, and the
**sign-off** (§7).

---

## 1. Before you brief the agent

Most rework comes from a brief that described a *feature* when it needed
to describe a *contract*.

### 1.1 Write the acceptance criteria first

Do not open with "build me X". Open with what "done" means. Give the
agent something checkable:

> **Instead of:** "Add a settlements feature."
>
> **Say:** "Add settlements. A settlement has: branch, period, per-trip
> lines, status (draft→submitted→approved→paid), and totals. Approved
> and paid are locked. Every headline figure must be traceable to the
> trips behind it. Acceptance: creating, submitting, approving and paying
> a settlement all work; an edit to an approved settlement returns 409;
> the totals equal the sum of the lines. Here is the model, the schema,
> the router and the screens I want."

That paragraph is worth more than the feature description, because it is
the thing you will check against.

### 1.2 State the constraints you actually have

The agent cannot see your environment. Tell it, or it will guess and
you will find out in hour three:

- Languages, frameworks, and **versions** (pinned, not "latest")
- What the build/deploy pipeline is, and what it will run
- Whether Docker is available, whether there is a database, or only a mock
- Whether the agent may use sub-agents, or must work solo
- What "finished" means for *this* project — often "the deployment
  builds and the app renders", nothing more

### 1.3 Ask for the tests to be written *with* the code

Not after. The prompt sentence that changes outcomes most:

> "Every function you add comes with a test that would have failed
> before the change."

### 1.4 Ask for honest reporting

> "If something does not work, say so and show me the output. Do not
> describe a feature as complete until you have run it."

An agent that says "done" without running things is worse than one that
reports a blocker, because you find out at the end.

---

## 2. While the agent works

### 2.1 Drive it in phases, and gate each phase

Do not ask for the whole app and walk away. Ask for one vertical slice,
review the output, then extend. Each phase should end with a runnable
artifact — not just "code written".

| Ask for | You get back | You check |
|---|---|---|
| "Scaffold and boot the project" | Something that starts | Does it start? Does health check pass? |
| "Add domain X end to end" | Model → API → screen | Can you use it end to end? |
| "Harden it" | Tests, guards, docs | Do the guards actually fail when broken? |

### 2.2 Watch for the three tells

**Tell 1 — the agent reports success but shows no output.** "The tests
pass" is a claim. "Tests pass" *with the run output* is evidence. Ask
for the output.

**Tell 2 — the agent writes a test that cannot fail.** A test asserting
`assert True`, or asserting only on a mock it also wrote, proves
nothing. Ask: *"what input would make this test fail?"*

**Tell 3 — the agent declares victory after a static check.** Static
checks prove a narrow slice. See §3.

### 2.3 Make the agent keep its own notes

Ask for a running `NOTES.md` or `DECISIONS.md` in the repo. Two reasons:
you will need it at handover, and it forces the decisions to be written
down while they are still fresh rather than reconstructed at the end.

---

## 3. The three testing passes

This is the core of the guide. The ordering matters more than the tools.

### Pass A — Does it compile?

Cheap, fast, catches the obvious. Never skip it, never treat it as
evidence of correctness.

```bash
# backend
python -m pytest -q                 # the suite must be green
python -m mypy . 2>/dev/null || true # optional
# frontend
npx tsc --noEmit                    # zero errors
npm run build                       # or your bundler's production build
```

**A green Pass A means:** the code is internally consistent. It says
nothing about whether the right things happen.

### Pass B — Do the two halves agree?

The dangerous zone: a frontend and a backend, written separately, that
*each* typecheck perfectly and don't match. The compiler cannot see this
because the boundary between them is a runtime string.

**What to compare:**

| Compare | Catches |
|---|---|
| Path + **HTTP method** | The 404 and the 405 |
| **Required** query params & body fields | The 422 |
| Response field names, backend model → frontend type | The blank screen |
| Role requirements, backend → frontend screen gating | The 403 wall |
| Enum values | The "invalid value" error |

**Do it by machine, not by eye.** Write a script that reads the
backend's own route table and the frontend's own call sites and diffs
them. Do it *twice*: once on paths, once on fields. The second pass finds
things the first cannot.

> **The trap:** a path-only diff reports everything as fine while a
> frontend `POST` to a backend `GET` route fails with 405 at runtime.
> **The trap:** a field diff done by eye misses one name in 147 fields.

**Corollary — your frontend types are hand-written and can lie.** A
`tsc` pass proves your `interface Settlement` matches *itself*. It
proves nothing about the JSON the server actually sends. Generate the
frontend types from the backend schema, or diff them mechanically.

### Pass C — Does it actually run?

This is where the real bugs live, and it is the pass most often skipped.

**The method:** boot the real application with a **mock/in-memory
database**, seed it, then **fire every call the frontend makes** with
realistic values — and look at the status codes.

```python
# the shape of it — the specifics depend on your stack
calls = scan_frontend_for_api_calls()   # method + path + params + body
for call in calls:
    resp = client.request(call.method, fill(call.path), **call.payload)
    assert resp.status_code not in (404, 405, 422, 500)
```

**Why the mock database matters:** you need to *execute* the code paths.
A mock DB that stores dates as real `datetime` objects, honours
`is_active` filters and rejects bad enum values will reproduce the bugs
a real DB would. A mock that returns canned fixtures will not — it will
hide exactly the class of bug you are looking for.

**Seed it like the app writes.** Use the same field names, the same
enum values, the same flags the real code sets. A seed built from a
different assumption produces noise, not signal.

**Make the payloads realistic.** A generic body of `{"id": "test"}`
turns into a wall of "invalid id" errors, and you drown in false
positives. Use the real payload shapes.

**Order the calls so destructive ones go last.** A `DELETE` that runs
before the `GET`s will make every later `GET` 404 and you will chase
ghosts.

### What Pass C found on a real project

All three of these were live in production, and all three passed the
static checks and a green test suite:

| Bug | Why everything else missed it |
|---|---|
| Two PDF exports returned 500 on **every** request | The code assumed dates arrive as ISO strings; the database returns native datetimes. No test had ever called either endpoint. |
| A whole feature was silently dead | The writer used collection `maintenance`; the reader used `maintenance_records`. Both are valid strings. The reader found nothing and reported "no maintenance due" — forever. |
| Eight hot tables had no index | Nothing errors; the app just gets slower as data grows. |

The common root cause of all three: **the absence of a test on that
code path.** Not a bad test — no test.

---

## 4. Traps worth knowing

### 4.1 Names are strings. Typos do not raise.

| Thing | Failure mode |
|---|---|
| DB collection names | Reader sees an empty collection, forever |
| Env vars | Feature silently disabled |
| Dict / JSON keys | `undefined` renders as blank |
| Enum values | "Invalid value" at runtime |
| Route paths | 404 |
| Route **methods** | 405 |

A typo in a collection name is **worse** than a typo in a variable name,
because the variable name raises and the collection name does not.

### 4.2 The same check at two levels finds different things

A path-only diff passes while a method mismatch waits to 405. A field
diff passes while an enum mismatches. Run each check against each
boundary.

### 4.3 "No test exists" is the real cause of almost every bug

When you find a bug, ask: *why did nothing catch this?* If the answer is
"nothing exercised that path", the fix is not just the bug — it is the
missing test. See §6.

### 4.4 Hand-maintained documents drift. Generated ones do not.

A checklist that says "147 endpoints verified" is worthless the day
someone adds an endpoint. Generate it from the code, and add a test
that fails when the document and the code disagree.

### 4.5 Verify the artifact, not the working copy

Build it, zip it, extract it somewhere clean, and run the checks *there*.
A build that only works in your working directory has a missing file, a
gitignored artefact, or a stale cache in it.

### 4.6 Destructive tests destroy the data later tests read

Order: reads, then creates, then updates, then deletes.

---

## 5. The pre-delivery gate

Run all of it. Tick the boxes. **A green test suite is not the gate** —
the gate is this list.

### 5.1 Does it build and start?

- [ ] Clean install from the lockfile / requirements file, in a fresh directory
- [ ] The app starts with no manual fixing
- [ ] The health check passes
- [ ] The production build succeeds (not just dev mode)
- [ ] The deploy pipeline completes
- [ ] There is a guard that stops the pipeline breaking again (see §5.5)

### 5.2 Does it do the job?

- [ ] The main flows work end to end, exercised by a human, not a script
- [ ] Every screen loads with real data
- [ ] Every screen has a sensible empty state and error state
- [ ] Every form validates and saves
- [ ] Every list filters, searches, paginates and sorts
- [ ] Every "delete" asks first and can be undone or is confirmed irreversible
- [ ] The numbers on the dashboard agree with the underlying records

### 5.3 Is it correct at the boundaries?

- [ ] The two halves of the app agree on every path, method, field and enum
- [ ] Every request the frontend can make has been fired against a running backend
- [ ] Every illegal state transition is refused, and leaves the record unchanged
- [ ] Role permissions match what the UI advertises — no screen shows a role that then gets 403
- [ ] One branch's data is invisible to another branch's team

### 5.4 Is it safe?

- [ ] No secret is in the repository
- [ ] Secrets come from the environment, and a missing one fails loudly
- [ ] Auth is enforced on every non-public endpoint
- [ ] Input is validated at the boundary
- [ ] Injection attempts are refused (query operators, script tags)
- [ ] One user cannot read another's data
- [ ] Rate limits exist on the endpoints that matter (login, password reset)
- [ ] Errors do not leak internals

### 5.5 Is it *protected*?

The most important box on this list.

- [ ] The CI pipeline runs the full suite on every push
- [ ] Each bug you found during this build has a permanent test that would fail without the fix
- [ ] There is a guard for the class of bug, not just the instance
- [ ] The contract check (frontend ↔ backend) runs in CI, not just on your machine
- [ ] A stale document or generated artifact fails the build

### 5.6 Is it maintainable?

- [ ] Someone else can run it from the README alone
- [ ] Setup, seeding and running are one command each
- [ ] The decisions are written down
- [ ] The code is where a reader expects it

---

## 6. When you find a bug

Five steps. The last two are the ones people skip.

1. **Reproduce it.** A bug you cannot reproduce is a bug you cannot fix
   or prove you fixed.
2. **Find the root cause**, not the symptom. "The PDF crashed" is a
   symptom. "The date formatter assumed the wrong type" is a cause.
3. **Fix it.**
4. **Write the test that would have failed before the fix.** If you
   cannot write that test, you have not understood the bug yet.
5. **Ask what class of bug it was**, and add a guard for the class:
   - wrong field name → a contract check between the two halves
   - wrong method → a method-aware contract check
   - typo'd collection → a check that each collection has one name
   - missing test on a path → a coverage report of untested endpoints
   - silent failure → assert on behaviour, not just on status codes

Step 5 is what turns *one* fix into a *class* of fixes.

---

## 7. Client delivery

### 7.1 Write the manual from the code, not from memory

Generate it. A manual that says "147 endpoints verified" is worthless the
moment endpoint 148 is added. The generator reads the code; a test
asserts the manual still covers it.

Include, at minimum:

- Every endpoint: method, path, required input, who may call it
- Every screen: route, what it shows, what must be true
- Every state machine: the full matrix of legal **and illegal** moves
- The security checks
- The performance expectations
- A sign-off sheet with names and dates

### 7.2 Write UAT scenarios as tasks, not features

> ❌ "Verify the trip module."
> ✅ "The dispatcher schedules tomorrow's trip, assigns a driver, and it
> appears on the driver's live board."

The client should be able to read it and say "yes, that is our job."

### 7.3 Let the client sign, on the record

A sign-off sheet with roles, names, signatures and dates. It converts
"it seemed fine" into a shared, recorded fact — and it is what makes
"ready for the client" a statement rather than an opinion.

---

## 8. Prompts you can paste

### 8.1 Starting a project

> Build X. Before writing code, read the existing code and tell me: the
> structure, the conventions already in use, and anything that will
> constrain the design. Then propose the data model, the API surface and
> the screens, and wait for my go-ahead before implementing. Every
> function comes with a test that would fail without it. Do not report
> anything as done unless you have run it and shown me the output.

### 8.2 Asking for an audit (Pass B + C)

> Audit this codebase against its own API surface. I want three passes:
> (A) does every route, method, required field and role in the backend
> match what the frontend calls and what the UI advertises — compare them
> mechanically, not by eye; (B) boot the app against an in-memory
> database, seed it the way the app writes, and fire every call the
> frontend makes with realistic payloads, then report every non-2xx;
> (C) report anything the code reads that no test exercises. Give me
> findings with a reproduction for each. Do not change code yet.

### 8.3 Asking for a pre-delivery check

> Before I hand this to a client, run the pre-delivery gate: clean
> install from the lockfile in a fresh directory, full test suite,
> typecheck, production build, contract check, and a fresh-extract
> smoke test. Then give me a checklist with honest pass/fail per item
> and the actual output. Do not summarise away failures.

### 8.4 Asking for a bug fixed properly

> Here is a bug and its reproduction. Fix the root cause. Then write the
> test that fails before the fix and passes after. Then tell me what
> class of bug this was and add a guard that catches the whole class —
> a check in the repo that runs automatically, not a note in a document.

---

## 9. The one-paragraph version

Write the acceptance criteria before the agent starts. Drive it in
phases and demand output, not claims. When it is built, test it three
times and make each pass able to see what the last one could not:
compiles, interfaces agree, it actually runs against a mock database with
real payloads. When a bug appears, the fix is not finished until there is
a test that would have caught it and a guard that catches the whole
class. Before the client sees it, run the gate — every item, honestly —
and hand over a manual generated from the code, signed by both sides.
