# CricketMatrix360 Power BI Star Schema

## Tables

### `fact_deliveries`

Central fact table containing one row per delivery.

Required foreign keys:

- `match_id`
- `batter`
- `bowler`

### `dim_matches`

Match dimension with one row per match.

- Primary key: `match_id`
- Attributes: date, venue, team1, team2, toss details

### `dim_players`

Player dimension with one unique row for every name appearing in either `fact_deliveries[batter]` or `fact_deliveries[bowler]`.

- Primary key: player name

## Relationships

- `dim_matches[match_id]` (1) -> `fact_deliveries[match_id]` (*)
- `dim_players[player_name]` (1) -> `fact_deliveries[batter]` (*)
- `dim_players[player_name]` (1) -> `fact_deliveries[bowler]` (*)

Use single-direction filtering from dimensions to the fact table. Because both batter and bowler use the same player dimension, configure one player relationship as active and the other as inactive, or create role-playing copies such as `dim_batters` and `dim_bowlers` when both roles must filter simultaneously.

## Measures Table

Create a dedicated Power BI table named `_Analytics_Measures` and add these measures.

```DAX
// Total Runs Scored
Total Runs =
SUM(fact_deliveries[runs_batter])

// Balls Faced (Excluding Wides)
Balls Faced =
CALCULATE(
    COUNT(fact_deliveries[delivery_id]),
    fact_deliveries[is_wide] = FALSE()
)

// Batting Strike Rate
Batting Strike Rate =
DIVIDE([Total Runs], [Balls Faced], 0) * 100

// Dot Ball Percentage
Dot Ball % =
VAR TotalDots =
    CALCULATE(
        COUNT(fact_deliveries[delivery_id]),
        fact_deliveries[runs_batter] = 0,
        fact_deliveries[is_wide] = FALSE()
    )
RETURN
    DIVIDE(TotalDots, [Balls Faced], 0) * 100

// Boundary Run Percentage
Boundary Run % =
VAR BoundaryRuns =
    CALCULATE(
        SUM(fact_deliveries[runs_batter]),
        fact_deliveries[runs_batter] IN {4, 6}
    )
RETURN
    DIVIDE(BoundaryRuns, [Total Runs], 0) * 100

// Wickets Taken (Excluding Run Outs & Retired Hurt)
Wickets =
CALCULATE(
    COUNT(fact_deliveries[delivery_id]),
    fact_deliveries[is_wicket] = TRUE(),
    NOT(fact_deliveries[dismissal_kind] IN {"run out", "retired hurt"})
)

// Legal Balls Bowled
Legal Balls Bowled =
CALCULATE(
    COUNT(fact_deliveries[delivery_id]),
    fact_deliveries[is_wide] = FALSE(),
    fact_deliveries[is_noball] = FALSE()
)

// Overs Bowled
Overs Bowled =
DIVIDE([Legal Balls Bowled], 6, 0)

// Total Runs Conceded
Runs Conceded =
SUM(fact_deliveries[runs_total])

// Bowling Economy Rate
Economy Rate =
DIVIDE([Runs Conceded], [Overs Bowled], 0)

// Bowling Strike Rate (Balls per Wicket)
Bowling Strike Rate =
DIVIDE([Legal Balls Bowled], [Wickets], 0)

// Powerplay Strike Rate (Overs 1 - 6)
Powerplay SR =
CALCULATE(
    [Batting Strike Rate],
    fact_deliveries[over_num] < 6
)

// Middle Overs SR (Overs 7 - 15)
Middle Overs SR =
CALCULATE(
    [Batting Strike Rate],
    fact_deliveries[over_num] >= 6 && fact_deliveries[over_num] < 15
)

// Death Overs SR (Overs 16 - 20)
Death Overs SR =
CALCULATE(
    [Batting Strike Rate],
    fact_deliveries[over_num] >= 15
)

// Death Overs Economy Rate
Death Overs Economy =
CALCULATE(
    [Economy Rate],
    fact_deliveries[over_num] >= 15
)
```
