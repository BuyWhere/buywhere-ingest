## BUY-29229 Root Execution Path For BUY-26662

Date: 2026-06-02 UTC

Purpose: document the exact operator/root action needed to clear the Playwright
system dependency blocker referenced by `BUY-26662`.

### What Was Verified

- The current execution user is `paperclip` (`uid=997`, not root).
- `npx playwright --version` resolves and reports `Version 1.60.0`.
- `sudo -n true` fails with `sudo: a password is required`.
- `sudo -n npx playwright install-deps chromium` fails with the same sudo
  password prompt before any package installation can start.

Conclusion: the agent can invoke Playwright, but this runtime has no
passwordless sudo or root-capable elevation path. The blocker is the host's
privilege boundary, not a missing repo dependency or missing Playwright binary.

### Required Manual Resolution

An operator with root or sudo access on the target host must run:

```bash
cd /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default
sudo npx playwright install-deps chromium
```

If the operator prefers a root shell instead of one-shot sudo, the equivalent
path is:

```bash
cd /paperclip/instances/default/projects/177bc805-e3c8-4336-84cb-8e1e482d5a17/18221361-973a-493e-9e19-4c43b7a1c6eb/_default
sudo -i
npx playwright install-deps chromium
```

### Success Signal

`BUY-26662` can be considered unblocked once a privileged operator posts
evidence that `npx playwright install-deps chromium` completed successfully on
the target host, or provides an equivalent passwordless/root-capable execution
path for the assignee.
