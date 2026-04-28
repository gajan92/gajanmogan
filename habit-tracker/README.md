# Habit Tracker

A simple markdown-based system for tracking daily habits — works in GitHub, Obsidian, Notion, VS Code, or any markdown viewer.

## How It Works

Each month gets its own file (e.g. `2026-04-april.md`). Open it daily, mark each habit `✅` or `❌`, and update the monthly summary at the end of the month.

```
habit-tracker/
├── README.md              ← you are here
├── template.md            ← blank template for new months
├── 2026-04-april.md       ← April 2026 example
└── 2026-05-may.md         ← create new files like this
```

## Legend

| Symbol | Meaning |
|--------|---------|
| `✅` | Habit completed |
| `❌` | Habit missed |
| `—` | Day not applicable (future date or outside the month) |

## Starting a New Month

1. Copy `template.md` and rename it to `YYYY-MM-monthname.md`
2. Update the header (`# Habit Tracker — [Month Year]`)
3. Replace `[dates]` placeholders in each week heading
4. Fill in the correct day numbers for that month's calendar
5. Replace `—` with `✅` or `❌` each day
6. Update the **Monthly Summary** table as you go (or at month end)

## Updating Stats

The **Monthly Summary** table is updated manually. At the end of each month:

- **Done**: count all `✅` in that habit's row across all weekly tables
- **Possible**: total days in the month
- **Rate**: `Done ÷ Possible × 100`
- **Streak**: consecutive `✅` days ending on the last day of the month
- **Best**: longest unbroken run of `✅` across the whole month

## Customising Your Habits

Edit the numbered list at the top of any monthly file. Keep the emoji + name consistent between the list and the table rows. To add a habit, add a row to every weekly table. To remove one, delete its list entry and table rows.
