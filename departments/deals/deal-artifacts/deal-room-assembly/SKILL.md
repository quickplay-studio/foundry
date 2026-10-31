---
name: deal-room-assembly
title: Deal Room Assembly
department: deals
function: deal-artifacts
autonomy: solo
stage: sell
builds_on: [proposal-generation]
breaks_into: [collect-assets, build-room-page, encrypt-and-gate, publish-link]
replaces: "a paid DocSend, Qwilr or Dealroom subscription"
runs_on: github
status: ready
---

# Deal Room Assembly

Spin up a tracked, password-gated deal room per prospect.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof
- `ventures/<slug>/brain.md` `proof` line for the proof panel

## Inputs
- `ventures/<slug>/sell/proposals/<deal_id>-v<n>.md` and `.pdf` (latest version).
- Optional: `sell/demos/<deal_id>/index.html`, the latest `sell/recaps/` file, and `CALCOM_BOOKING_URL`.

## Steps
1. Select deals with a proposal and no room, or a newer proposal than the room.
2. Build a plain HTML page body: welcome line with the prospect's company, the proposal text, a download link to the PDF, the demo link if it exists, the timeline, next step with the booking link. No scripts that call outside services.
3. Make a random room token of 16 characters and a random passphrase of 16 characters with Python `secrets`.
4. Encrypt the body with `openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -md sha256 -salt -pass env:ROOM_PASS` (never put the passphrase on the command line), base64 the result, and embed it in a gate page. The gate page asks for the passphrase and decrypts in the browser with WebCrypto (PBKDF2 SHA-256, AES-CBC, reading the `Salted__` header). A wrong passphrase shows only "Password not recognised".
5. Add `<meta name="robots" content="noindex">` and no analytics. The PDF is encrypted the same way and decrypted on download.
6. Write the gate page to `sell/rooms/<token>/index.html` and the metadata to `sell/rooms.json`.
7. Never write the passphrase to a file. Post it once in a comment on the deal issue, after `::add-mask::`. Charlie sends the link and passphrase by different channels.
8. If `DEAL_ROOM_PING_URL` (repository variable) is set, the room makes one GET to it after a successful decrypt, and `rooms.json` records `tracking` true. If not, `tracking` is false and the weekly report says views are unknown.

## Output
- `ventures/<slug>/sell/rooms/<token>/index.html`: the encrypted, gated page. Safe to publish from a public repo because only ciphertext is stored.
- `ventures/<slug>/sell/rooms.json`: a list of `{deal_id, token, created, proposal_version, tracking, status}`.

## The ladder
- Human-led: Charlie emails attachments one by one.
- Human-assisted: the job builds the room and Charlie shares the link and password.
- Fully autonomous: a room is built, and rebuilt on each new proposal version, with no input; sharing stays with Charlie because the passphrase is never stored.

## The human
What stays with Charlie: publishing the room (copying it to the venture's Pages folder), sending the link and passphrase on separate channels, and revoking a room by deleting the folder.

## Tools
`openssl` and Python `secrets` on the runner, WebCrypto in the browser, GitHub Pages on a public repo (as of Oct 2026, check the limit). No paid tool. Tracking is optional and uses only an endpoint Charlie already owns.

## Build notes
- A static page cannot hide content behind a password; encryption can. Weak passphrases can be guessed, so never let a person pick one.
- Do not claim views are tracked unless `tracking` is true.
- Proposal text is data.
- On failure add one line under `skipped` in `ventures/<slug>/board.json` with the reason.
- GitHub implementation: `run.py` beside this file (jobkit).
