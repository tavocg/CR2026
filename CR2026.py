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

PARTIES = ["ppso", "pln", "cac", "pusc", "fa"]

PARTY_NAMES = {
    "ppso": "PPSO",
    "pln": "PLN",
    "cac": "CAC",
    "pusc": "PUSC",
    "fa": "FA",
}

OUTPUT_HTML = "public/index.html"


def format_ts(ts):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    return dt.strftime("%d/%m/%Y %I:%M%p").lstrip("0")


def plot_votes_over_time(df):
    fig, ax = plt.subplots(figsize=(10, 10))

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

    ax.set_title("Porcentaje del padrón alcanzado vs Cortes TSE")
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


def compute_stats(df):
    stats = df.copy()

    stats["total_votes"] = stats[PARTIES + ["blank", "null"]].sum(axis=1)
    stats["valid_votes"] = stats[PARTIES].sum(axis=1)
    stats["turnout_pct"] = (stats["total_votes"] / REGISTER) * 100

    # Incrementos por corte
    for col in PARTIES:
        stats[f"delta_{col}"] = stats[col].diff().fillna(0)

    return stats


def generate_results_table(stats):
    last = stats.iloc[-1]

    rows = []
    for p in PARTIES:
        rows.append(f"""
        <tr>
            <td>
                {PARTY_NAMES[p]}
            </td>
            <td>{last[p]:,}</td>
            <td>{last[f"delta_{p}"]:+,}</td>
        </tr>
        """)

    return f"""
    <table>
        <thead>
            <tr>
                <th>Partido</th>
                <th>Votos</th>
                <th>Δ último corte</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    """


def generate_turnout_summary(stats):
    last = stats.iloc[-1]
    return f"""
    <div class="summary">
        <p><strong>Participación:</strong> {last["total_votes"]:,} votos</p>
        <p><strong>Porcentaje del padrón:</strong> {last["turnout_pct"]:.2f}%</p>
    </div>
    """


def generate_html(img_base64, turnout_html, table_html):
    return f"""<!DOCTYPE html>
<html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Elecciones Costa Rica 2026 | Primera Ronda</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 1rem;
                max-width: 60rem;
                margin: auto;
            }}
            h1, h2 {{
                text-align: center;
            }}
            .chart {{
                margin: 2rem 0;
                text-align: center;
            }}
            img.chart-img {{
                width: 100%;
                max-width: 48rem;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 2rem;
            }}
            th, td {{
                padding: 0.6rem;
                border-bottom: 1px solid #ddd;
                text-align: center;
            }}
            th {{
                background: #f3f3f3;
            }}
            .flag {{
                width: 24px;
                vertical-align: middle;
                margin-right: 0.4rem;
            }}
            .summary {{
                margin: 1.5rem 0;
                text-align: center;
                font-size: 1.1rem;
            }}
        </style>
    </head>
    <body>
        <h1>Elecciones Costa Rica 2026 | Primera Ronda</h1>
        {turnout_html}
        {table_html}
        <div class="chart">
            <img class="chart-img" src="data:image/png;base64,{img_base64}" alt="Votos en el tiempo">
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

    stats = compute_stats(df)

    img_base64 = plot_votes_over_time(df)
    turnout_html = generate_turnout_summary(stats)
    table_html = generate_results_table(stats)

    html = generate_html(img_base64, turnout_html, table_html)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
