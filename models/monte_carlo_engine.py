import numpy as np


def simulate_innings(
    current_score,
    current_over,
    wickets_lost,
    historical_over_distribution,
    n_simulations=5000,
):
    overs_remaining = 20 - current_over
    simulated_final_scores = []

    for _ in range(n_simulations):
        score = current_score
        wickets = wickets_lost

        for over in range(int(current_over), 20):
            if wickets >= 10:
                break
            runs_in_over = np.random.choice(
                [4, 6, 8, 10, 12, 15],
                p=[0.2, 0.3, 0.25, 0.15, 0.07, 0.03],
            )
            wicket_event = np.random.choice([0, 1], p=[0.88, 0.12])

            score += runs_in_over
            wickets += wicket_event

        simulated_final_scores.append(score)

    p10 = int(np.percentile(simulated_final_scores, 10))
    p50 = int(np.percentile(simulated_final_scores, 50))
    p90 = int(np.percentile(simulated_final_scores, 90))

    return p50, (p10, p90)