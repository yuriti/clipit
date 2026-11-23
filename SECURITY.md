# Security

## Reporting a vulnerability

Please report it privately through GitHub: the repository's **Security** tab → **Report a vulnerability**. Do not open
a public issue for it. We answer within a week and credit you in the release notes unless you prefer not.

Only the latest version gets fixes; update from SMTV's window when it offers a new version.

## What SMTV protects, in plain words

- **Your keys** to AI services stay on your computer — in the system's password store, or encrypted in a file in
  SMTV's folder — and go only to the service they belong to. They never appear in the window, logs or problem reports.
- **The SMTV page** answers only on this computer, and every request to it needs a secret that only SMTV's own window
  and page have: another program or a web site cannot work SMTV on your behalf. Even the page itself opens only
  from SMTV (its icon or the `smtv` command), so another user of this computer cannot get that secret.
- **A phone** sees SMTV only when you switch it on (Settings → Phone) and scan the QR code, which carries a new
  random secret; switching it off cuts every phone off at once. From a phone you cannot see or change keys, update or
  remove SMTV; the account is only shown there — signing in, signing out and paying happen on the computer.
- **A link** you paste goes to StreamMoment's server, which fetches the recording for SMTV and stores nothing. A file
  of your own is not sent anywhere. The text of the stream goes only to the AI you chose.
- **Updates** come only from a list of releases signed by SMTV's authors; SMTV checks the signature, never goes back
  to an older list, and installs only files whose checksums match that list.
- **Fixes** that SMTV offers (installing ffmpeg, for example) run a program SMTV itself knows for your system, shown
  to you before it runs; SMTV never runs a command it got from the internet.

What it does not protect from: a program that already runs under your own user account on this computer can read
what you can read, SMTV's files included — as with any other program.
