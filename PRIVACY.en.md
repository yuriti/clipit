# Privacy

<!-- The source is the Russian PRIVACY.md; a change to it changes this file in the same PR. -->

This is about one thing: what our StreamMoment server learns when Clip It! downloads a recording **by link** (YouTube,
Twitch). You do not need to sign in for it. Files from your computer, your clips, your settings and your keys never go
to the server.

## What we collect

When you paste a link, the request to the server carries:

- **A device id** — a hash (an irreversible fingerprint) of your computer's id. The id itself is never sent or stored.
  If it cannot be read, Clip It! makes a random id once and keeps it in its own settings.
- **The Clip It! version** and **the system** (for example macOS 15 or Windows 11, and the processor type).
- **Which videos were downloaded**, **when**, and **how long it took**.
- **A hash of the IP address** of your connection, computed with our secret key: the address itself cannot be recovered
  from it.

We do not receive your name, your e-mail, the content of the videos or your clips.

## Why

- **Abuse limits**: a cap on downloads per device and per address.
- **Usage statistics**: how many people use Clip It! and which recordings are downloaded.
- **Improving the product**, including our own recommendations and special offers inside Clip It!, possibly from
  partners (content authors). Partners are **not given any of your data**: Clip It! itself shows the offer.
- **Anonymous aggregate statistics for content authors** — for example, how many devices downloaded their recordings.
  We never show a figure computed from fewer than 5 devices.

## What we do not do

- We do not sell the data and do not pass it to third parties.
- We show no third-party ads.

## How long it is kept

12 months. After that only anonymous totals remain, from which no device or person can be identified.

## Your choice

You will be able to opt out of offers in Clip It!'s settings. Downloading by link without sending this information is not
possible: it is needed for abuse limits. If that does not suit you, use files from your computer — nothing is sent for them.

Questions and requests to delete a device's data: [an issue on GitHub](https://github.com/yuriti/clipit/issues).
