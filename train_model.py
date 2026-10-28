import os
import sqlite3
import pandas as pd
import numpy as np
import pickle
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss


def prepare_chase_dataset(db_path="data/cricket_matrix.db"):
    conn = sqlite3.connect(db_path)

    # Query to compute live chase status ball-by-ball
    query = """
    WITH match_targets AS (
        SELECT match_id, SUM(runs_total) + 1 AS target
        FROM deliveries
        WHERE inning = 1
        GROUP BY match_id
    )
    SELECT
        d.match_id,
        d.over_num,
        d.ball_num,
        d.runs_total,
        d.is_wicket,
        m.target,
        m_info.winner,
        d.batting_team,
        d.bowling_team
    FROM deliveries d
    JOIN match_targets m ON d.match_id = m.match_id
    JOIN matches m_info ON d.match_id = m_info.match_id
    WHERE d.inning = 2 AND m_info.match_type = 'T20'
    ORDER BY d.match_id, d.over_num, d.ball_num;
    """

    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    # Feature Engineering
    df["balls_bowled"] = df["over_num"] * 6 + df["ball_num"]
    df["balls_left"] = 120 - df["balls_bowled"]

    # Running cumulative sum for runs and wickets
    df["current_score"] = df.groupby("match_id")["runs_total"].cumsum()
    df["wickets_fallen"] = df.groupby("match_id")["is_wicket"].cumsum()

    df["runs_left"] = df["target"] - df["current_score"]
    df["crr"] = np.where(
        df["balls_bowled"] > 0,
        (df["current_score"] * 6) / df["balls_bowled"],
        0,
    )
    df["rrr"] = np.where(
        df["balls_left"] > 0,
        (df["runs_left"] * 6) / df["balls_left"],
        0,
    )

    # Target variable: Did batting team win?
    df["is_winner"] = np.where(df["winner"] == df["batting_team"], 1, 0)

    # Filter valid match conditions
    df = df[
        (df["balls_left"] >= 0)
        & (df["runs_left"] >= -10)
        & (df["wickets_fallen"] <= 10)
    ]

    features = ["runs_left", "balls_left", "wickets_fallen", "crr", "rrr", "target"]
    X = df[features]
    y = df["is_winner"]

    return train_test_split(X, y, test_size=0.2, random_state=42)


def train_and_save():
    os.makedirs("models", exist_ok=True)
    X_train, X_test, y_train, y_test = prepare_chase_dataset()

    model = XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.05,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)
    print(f"Model Accuracy: {accuracy_score(y_test, preds):.4f}")
    print(f"Log Loss: {log_loss(y_test, probs):.4f}")

    with open("models/win_predictor.pkl", "wb") as f:
        pickle.dump(model, f)
    print("SUCCESS: Model saved to models/win_predictor.pkl")


if __name__ == "__main__":
    train_and_save()
