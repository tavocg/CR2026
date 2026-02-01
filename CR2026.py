#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timezone
import base64
from io import BytesIO

import pandas as pd
import matplotlib.pyplot as plt

REGISTER = 3500000

COLUMNS = [
    "timestamp",
    "ppso",
    "pln",
    "cac",
    "pusc",
    "fa",
    "blank",
    "null",
]

COLORS = {
    "ppso": "#0f9eaf",
    "pln": "#014d27",
    "cac": "#e3051a",
    "pusc": "#13017c",
    "fa": "#efd800",
    "blank": "#c2c2c2",
    "null": "#000",
}

OUTPUT_HTML = "public/index.html"


def format_ts(ts):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    return dt.strftime("%d/%m/%Y %I:%M%p").lstrip("0")


def plot_votes_over_time(df):
    fig, ax = plt.subplots(figsize=(10, 6))

    x_labels = df["timestamp"].apply(format_ts)
    x = range(len(df))

    for col in df.columns:
        if col == "timestamp":
            continue

        color = COLORS.get(col, "#333333")

        percentages = (df[col] / REGISTER) * 100

        ax.plot(
            x,
            percentages,
            marker="o",
            label=col.upper(),
            color=color,
            linewidth=2,
        )

        last_x = x[-1]
        last_pct = percentages.iloc[-1]
        last_votes = df[col].iloc[-1]

        ax.annotate(
            f"{last_votes:,} votos",
            xy=(last_x, last_pct),
            xytext=(8, 0),
            textcoords="offset points",
            fontsize=9,
            color=color,
            va="center",
        )

    ax.axhline(
        40,
        color="red",
        linestyle="--",
        linewidth=2,
        label="Umbral 40%",
    )

    ax.set_title("Votos en el tiempo")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Porcentaje del padrón (%)")

    ax.set_xticks(list(x))
    ax.set_xticklabels(x_labels, rotation=45)

    ax.set_ylim(0, max(45, ax.get_ylim()[1]))
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)
    ax.legend()

    buffer = BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def generate_html(img_base64):
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Elecciones Costa Rica 2026 | Primera Ronda</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            padding: 2rem;
        }}
        h1 {{
            text-align: center;
        }}
        .chart {{
            text-align: center;
        }}
        img {{
            max-width: 100%;
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        }}
    </style>
</head>
<body>
    <h1>Elecciones Costa Rica 2026 | Primera Ronda</h1>
    <div class="chart">
        <img src="data:image/png;base64,{img_base64}" alt="Votos en el tiempo">
    </div>
</body>
</html>
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <input.csv>")
        sys.exit(1)

    input_csv = sys.argv[1]

    df = pd.read_csv(input_csv, dtype=int)

    if list(df.columns) != COLUMNS:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")

    os.makedirs("public", exist_ok=True)

    img_base64 = plot_votes_over_time(df)
    html = generate_html(img_base64)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
