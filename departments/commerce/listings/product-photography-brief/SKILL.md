---
name: product-photography-brief
title: Product Photography Brief
department: commerce
function: listings
autonomy: solo
stage: launch
builds_on: [product-selection]
breaks_into: [read-image-rules, plan-shot-list, plan-short-videos, write-style-notes]
replaces: "a product photographer's brief or a creative director's shot list"
runs_on: github
status: ready
---

# Product Photography Brief

Shot list and style notes for product images and short videos; what to shoot, in what order, for which placement.

Produces a brief Charlie can shoot from with a phone and daylight. It generates no images.

## Reads from the brain
- `brain/company.md`: voice, offers, constraints (free tools only; plain, no hype)
- `ventures/<slug>/brain.md`: the venture's problem, who, gap, mvp, money, proof (who buys, the problem the product solves, the proof points to show)

## Inputs
- `ventures/<slug>/idea.json`: `kind` and `channels`.
- `ventures/<slug>/commerce/shortlist.json`: the picked product, competitor listings and complaint themes.
- `ventures/<slug>/commerce/listings.json` if it exists: the bullets, so each claim has a shot.
- `ventures/<slug>/commerce/sample-results.json` if it exists: the verdict and photographs from the sample.
- Public pages: each channel's image and video requirements, and the leading competitors' main images and videos.

## Steps
1. Read `idea.json`; stop with a `skipped` line if the kind is not a commerce kind. List the channels and the placements: main image, gallery images, product video, TikTok Shop product video, short ad creative.
2. Read each channel's current image and video rules (size, ratio, background, minimum resolution, forbidden overlays, video length). Record the values and the date read; check them each run.
3. Look at the five leading competitor listings and note what their images show and what they leave out. The brief should fill the gaps, for example scale, in-use, what is in the box, close-up of the material.
4. Write the shot list in the order to shoot, with an id, placement, framing, what must be visible and the claim it proves:
   - Main image: plain white background, product filling the frame, no props, to the channel's rules.
   - Gallery: scale against a hand or a known object, in use by the target buyer, the key feature close up, what is in the box, the answer to the top complaint theme, one lifestyle shot.
   - Video, 15 to 30 seconds vertical: a hook in the first two seconds that states the problem, the product in use, the result, then a plain end card with the price. Give a beat sheet, not a script.
5. Write the style notes: natural window light, a neutral surface, one accent colour taken from the product, the same crop across the set, no filters that change the colour, no claims in overlay text that the listing does not support. Add a phone checklist: clean lens, tripod or stack of books, grid on, 4K at 30fps, shoot twice as much as needed.
6. Add the batch plan: group shots by setup so the whole set takes one hour. Name the files `<product>-<shot-id>.jpg` so `catalogue-sync` can match them.
7. Add a rights note: Charlie's own photographs only, no supplier or competitor images unless the supplier gives written permission, and no stock photos of results the product cannot deliver.

## Output
- `ventures/<slug>/commerce/photo-brief.md`: the shot list as a table (id, placement, framing, must show, claim proved), the video beat sheets, style notes, the channel rules with dates, and the file naming rule.
- `ventures/<slug>/commerce/photo-brief.json`: `{product_id, shots: [{id, placement, channel, ratio, min_px, file}], videos: [{id, length_s, ratio, beats}]}` for `catalogue-sync` and the video jobs.

## The ladder
- Human-led: Charlie shoots from his own judgement.
- Human-assisted: Charlie shoots from the brief and sends the files back for a check against the rules.
- Fully autonomous: the default for the brief. Shooting is physical, so it stays with Charlie.

## The human
What stays with Charlie: shooting, choosing the best frames, and rejecting any image that overstates the product.

## Tools
Free first. Firecrawl free tier (500 credits as of Oct 2026, check the limit) to read the seller help centres and competitor listings; Gemini 2.5 Flash or Groq to draft the brief; Charlie's phone for the shooting. No paid studio tools or stock libraries.

## Build notes
- Requirements are read from the help centre on each run; keep the date next to each value.
- Tests offline: fixtures for two channels with different ratios, and a product with no sample photographs.
