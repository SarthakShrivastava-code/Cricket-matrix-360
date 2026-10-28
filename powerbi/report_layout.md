# CricketMatrix360 Power BI Report Layout

## Report Theme

Use a dark sports-analytics theme across all pages:

| Token | Color | Use |
| --- | --- | --- |
| Background | `#0F172A` | Page and canvas background |
| Primary accent | `#38BDF8` | Selected states, batting metrics, primary series |
| Highlight | `#F59E0B` | Key highlights, chasing series, alerts |
| Surface | `#1E293B` | Cards, slicers, and visual containers |
| Text | `#F8FAFC` | Headings and primary values |
| Muted text | `#94A3B8` | Labels and secondary values |

Use compact KPI cards with white values, muted labels, and no visual borders. Use `#38BDF8` for batting or first-innings series and `#F59E0B` for chasing or highlight series.

## Page 1: Match & Team Strategy Hub

### Slicers

- Match Format: `matches[match_type]`, values `T20`, `ODI`
- Date Range: `matches[match_date]`, Between slicer
- Teams: team selector from the match team fields
- Venue: `matches[venue]`

### KPI Cards

- Total Matches
- Avg 1st Innings Score
- Chasing Win %
- Toss Win-Match Win Correlation %

### Visual 1: Phase Scoring

- Visual: Stacked bar chart
- Axis: match phase
- Values: average runs scored
- Legend: selected team
- Phases: Powerplay, Middle Overs, Death Overs
- Source: phase-wise batting analytics and phase measures
- Styling: primary accent for Powerplay, progressively darker blue for Middle, amber for Death

### Visual 2: Venue Win Conversion

- Visual: Map when venue coordinates are available; otherwise clustered bar chart
- Axis: venue
- Values: win conversion percentage
- Legend: batting first versus chasing
- First innings series: `#38BDF8`
- Chasing series: `#F59E0B`

## Page 2: Batter Profile & Matchup Matrix

### Slicers

- Batter Selection: `dim_players[player_name]` filtered to batters
- Opposition Team: opposition team field from `dim_matches`
- Bowler Type: Spin or Pace classification

### KPI Cards

- Total Runs
- Batting Average
- Batting Strike Rate
- Boundary Run %
- Dot Ball %

### Visual 1: Player Phase Profile

- Visual: Radar or spider chart custom visual
- Category axis: Powerplay SR, Middle Overs SR, Death Overs SR, Spin SR, Pace SR
- Values: selected batter's corresponding measures
- Center baseline: league or filtered-team average when supported
- Series color: `#38BDF8`

### Visual 2: Batter vs Bowler Matrix

- Visual: Matrix table
- Rows: batter, bowler
- Values: runs scored, balls faced, dismissals, strike rate
- Filter: matchup rows with at least 18 balls faced
- Conditional formatting: amber for high strike rate and blue for high dismissal count
- Source: `sql/batter_vs_bowler.sql`

## Page 3: Death-Over Bowling Specialists

### Slicers

- Minimum Overs Filter: `Overs Bowled`, default threshold greater than 10 overs

### Visual 1: Death Bowling Performance

- Visual: Scatter plot
- X-axis: Death Economy Rate
- Y-axis: Wickets in Death Overs
- Bubble size: Death Dot Ball %
- Details: bowler
- Analytics: add average economy and average wickets reference lines
- Lower economy and higher wickets indicate the preferred top-right performance direction after axis interpretation

### Visual 2: Top Death Bowlers

- Visual: Clustered column chart
- Axis: bowler
- Value: Death Economy Rate
- Filter: Top N = 10 by lowest Death Economy Rate
- Scope: overs 16-20 only
- Sort: ascending economy rate
- Accent: `#38BDF8`; highlight the selected or top-ranked bowler with `#F59E0B`
- Source: `sql/death_bowling_clutch.sql`

## Page Navigation

Add a consistent header with three page buttons:

1. Match & Team Strategy Hub
2. Batter Profile & Matchup Matrix
3. Death-Over Bowling Specialists

Keep slicer placement consistent on the left or in a narrow top filter band. Enable cross-highlighting between KPI cards and visuals, and add report-page tooltips for metric definitions and sample sizes.
