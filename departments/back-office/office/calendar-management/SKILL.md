---
name: calendar-management
title: Calendar Management
department: back-office
function: office
autonomy: assisted
stage: none
builds_on: []
breaks_into: [read-calendar, find-slots, convert-timezones, draft-invite]
replaces: "a virtual assistant's scheduling time or a paid scheduling app, roughly 10 to 15 pounds a month"
runs_on: claude-code
status: ready
---

# Calendar Management

Scheduling, conflicts, buffers and timezone maths. Run in a Claude Code session (Sonnet): Charlie states the meeting, the session proposes three slots and drafts the invite. Nothing is sent and no calendar is connected.

## Reads from the brain
- `brain/company.md`: working hours are evenings and weekends UK time; voice for the reply text
- `ventures/<slug>/brain.md`: who the meeting is with and why, if it belongs to a venture

## Inputs
- `office/calendar/*.ics`: exports of Charlie's calendars, dropped in by him (the export file from his calendar settings, not a private feed link, which acts like a password).
- `office/calendar/availability.json`: `{"timezone": "Europe/London", "windows": [{"days": [...], "from", "to"}], "buffer_minutes": 15, "min_notice_hours": 24}`. If missing, ask Charlie once for his hours and write the file. Do not assume hours beyond "evenings and weekends".
- The request: who, length, the other party's timezone, a date window, and whether it is a call or in person.
- `office/calendar/proposals/`: earlier proposals, to avoid offering a slot twice.

## Steps
1. Parse the ICS files with the stdlib. Expand simple recurrences (daily, weekly, monthly with an interval or count). List any rule that cannot be expanded under `unexpanded` and ask Charlie about it rather than ignoring it.
2. Convert every event to UTC with `zoneinfo`, so daylight saving is handled by the library, including the UK clock changes in March and October. Treat all-day events as blocking the day only if marked busy.
3. Check the file is not stale: if the newest event export is more than 7 days old, say so in the first line of the proposal.
4. Build free intervals inside `windows`, subtract events with `buffer_minutes` either side, drop anything inside `min_notice_hours`.
5. Pick three slots of the requested length on different days where possible, preferring the other party's reasonable hours (08:00 to 20:00 their time). If none exist in the window, say so and suggest the nearest widening.
6. Show each slot in both timezones, with the weekday, and flag a clock change within the window.
7. Draft the reply in Charlie's voice, short and plain, offering the three slots, and an `.ics` invite for the one chosen once Charlie picks.
8. On request, run a conflicts check over the next 14 days: overlaps, back-to-back events with no buffer, and events on the far side of a clock change.

## Output
- `office/calendar/proposals/YYYY-MM-DD-<who>.md`: the three slots in both timezones, the reply text, the reasons for any gap.
- `office/calendar/proposals/YYYY-MM-DD-<who>.ics`: a draft invite for Charlie to import and send himself.
- `office/calendar/conflicts.md` when asked.

## The ladder
- Human-led: Charlie checks the calendar and does the timezone maths in his head.
- Human-assisted (the setting here): the session proposes and drafts; Charlie picks and sends.
- Fully autonomous: needs a live calendar connection, which is out of bounds here (no keys or accounts). Revisit only if Charlie grants one.

## The human
What stays with Charlie: exporting the calendar, choosing the slot, sending the invite and reply, and saying no to meetings.

## Tools
Claude Code with Sonnet; Python stdlib `zoneinfo` and a short ICS reader. No model call is needed for the maths. Free Google Calendar export is the data source.

## Build notes
- Why claude-code: it is interactive and on demand, with judgement over the other party's hours and awkward recurrences. The pure conflict check could later move to a weekly GitHub job reading the same files.
- One helper, `foundry/cal.py`, with tests for a clock-change week, a weekly recurrence, an all-day event and a request that has no valid slot.
