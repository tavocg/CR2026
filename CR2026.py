#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timezone
import base64
from io import BytesIO

import pandas as pd
import matplotlib.pyplot as plt

REGISTER = 3731788

COLUMNS = [
    "timestamp",
    "ppso",
    "pln",
    "cac",
    "pusc",
    "fa",
    "nr",
    "plp",
    "valid",  # suma de los votos de los partidos
    "null",  # incluye nulos + blancos
]

COLORS = {
    "ppso": "#0f9eaf",
    "pln": "#014d27",
    "cac": "#e3051a",
    "pusc": "#13017c",
    "fa": "#efd800",
    "nr": "#9ddbea",
    "plp": "#f16528",
    "blank": "#c2c2c2",
    "null": "#000",
}

PARTIES = ["ppso", "pln", "cac", "pusc", "fa", "nr", "plp"]

PARTY_NAMES = {
    "ppso": "PPSO",
    "pln": "PLN",
    "cac": "CAC",
    "pusc": "PUSC",
    "fa": "FA",
    "nr": "NR",
    "plp": "PLP",
}

OUTPUT_HTML = "public/index.html"


def format_ts(ts):
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone()
    return dt.strftime("%d/%m/%Y %I:%M%p").lstrip("0")


def plot_votes_over_time(df):
    fig, ax = plt.subplots(figsize=(10, 10))

    x_labels = df["timestamp"].apply(format_ts)
    x = range(len(df))

    max_pct = 0

    for col in PARTIES:
        color = COLORS.get(col, "#333333")
        percentages = (df[col] / df["valid"]) * 100
        max_pct = max(max_pct, percentages.max())

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

    if max_pct >= 38:
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
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)
    ax.legend()

    buffer = BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def plot_popularity_trends(df):
    """Grafica la tendencia de popularidad (aceleración/desaceleración) de cada partido"""
    fig, ax = plt.subplots(figsize=(10, 8))

    x_labels = df["timestamp"].apply(format_ts)
    x = range(len(df))

    for party in PARTIES:
        color = COLORS.get(party, "#333333")

        # Calcular porcentajes del padrón
        percentages = (df[party] / REGISTER) * 100

        # Calcular el crecimiento entre cortes
        growth = percentages.diff()

        # Calcular cambio en el crecimiento
        trend = growth.diff()

        # Solo graficar desde el índice 2
        if len(trend) > 2:
            ax.plot(
                x[2:],
                trend.iloc[2:],
                marker="o",
                label=PARTY_NAMES[party],
                color=color,
                linewidth=2,
            )

    # Línea de referencia en 0 (constante)
    ax.axhline(
        0,
        color="black",
        linestyle="-",
        linewidth=1.5,
        alpha=0.7,
        label="Crecimiento constante",
    )

    ax.set_title("Tendencia de Popularidad por Partido (Aceleración/Desaceleración)")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Cambio en crecimiento (puntos porcentuales)")

    ax.set_xticks(list(x))
    ax.set_xticklabels(x_labels, rotation=45)

    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend()

    # Añadir texto explicativo
    ax.text(
        0.5,
        0.98,
        "↑ Valores positivos = Ganando popularidad\n↓ Valores negativos = Perdiendo popularidad",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.3),
    )

    buffer = BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def compute_stats(df):
    stats = df.copy()

    stats["total_votes"] = stats["valid"] + stats["null"]

    # Calcular porcentaje sobre votos válidos
    for col in PARTIES:
        stats[f"pct_{col}"] = (stats[col] / stats["valid"]) * 100

    # Crecimiento (primera derivada)
    for col in PARTIES:
        stats[f"growth_{col}"] = stats[f"pct_{col}"].diff().fillna(0)

    # Tendencia (segunda derivada)
    for col in PARTIES:
        stats[f"trend_{col}"] = stats[f"growth_{col}"].diff().fillna(0)

    return stats


def get_trend_indicator(trend_value):
    """Retorna un indicador visual de la tendencia con porcentaje"""
    if trend_value > 0.01:
        return f"▲ {trend_value:+.3f}%"
    elif trend_value < -0.01:
        return f"▼ {trend_value:+.3f}%"
    else:
        return f"─ {trend_value:+.3f}%"


def get_trend_class(trend_value):
    """Retorna una clase CSS basada en la tendencia"""
    if trend_value > 0.01:
        return "trend-up"
    elif trend_value < -0.01:
        return "trend-down"
    else:
        return "trend-neutral"


def generate_results_table(stats):
    last = stats.iloc[-1]

    # Crear lista de partidos con sus votos y porcentaje
    party_info = [(p, last[p], last[f"pct_{p}"]) for p in PARTIES]
    # Ordenar por votos de mayor a menor
    party_info.sort(key=lambda x: x[1], reverse=True)

    rows = []
    for p, votes, pct in party_info:
        trend = last[f"trend_{p}"]
        trend_indicator = get_trend_indicator(trend)
        trend_class = get_trend_class(trend)

        rows.append(f"""
        <tr>
            <td>{PARTY_NAMES[p]}</td>
            <td>{int(votes):,}</td>
            <td>{pct:.2f}%</td>
            <td class="{trend_class}">{trend_indicator}</td>
        </tr>
        """)

    return f"""
    <table>
        <thead>
            <tr>
                <th>Partido</th>
                <th>Votos</th>
                <th>Porcentaje</th>
                <th>Tendencia</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows)}
        </tbody>
    </table>
    """


def plot_votes_per_cut(df):
    fig, ax = plt.subplots(figsize=(12, 8))

    x_labels = df["timestamp"].apply(format_ts)
    x = range(len(df))

    for party in PARTIES:
        ax.plot(
            x,
            df[party],
            marker="o",
            label=PARTY_NAMES[party],
            color=COLORS.get(party, "#333333"),
            linewidth=2,
        )

        # Mostrar último valor sobre el punto final
        ax.annotate(
            f"{df[party].iloc[-1]:,}",
            xy=(x[-1], df[party].iloc[-1]),
            xytext=(8, 0),
            textcoords="offset points",
            fontsize=9,
            color=COLORS.get(party, "#333333"),
            va="center",
        )

    ax.set_title("Votos por Partido en cada Corte")
    ax.set_xlabel("Hora")
    ax.set_ylabel("Cantidad de Votos")
    ax.set_xticks(list(x))
    ax.set_xticklabels(x_labels, rotation=45)
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)
    ax.legend()

    buffer = BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format="png")
    plt.close(fig)

    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def generate_html(img_base64, popularity_img_base64, table_html, df):
    last = df.iloc[-1]
    votos_emitidos = last["valid"] + last["null"]
    votos_nulos = last["null"]
    votes_per_cut_img = plot_votes_per_cut(df)

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
            margin: 4rem 0;
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
        .trend-up {{
            color: #22c55e;
            font-weight: bold;
        }}
        .trend-down {{
            color: #ef4444;
            font-weight: bold;
        }}
        .trend-neutral {{
            color: #6b7280;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>Elecciones Costa Rica 2026 | Primera Ronda</h1>
    <div class="summary">
        Votos emitidos: {votos_emitidos:,} | Nulos y blancos: {votos_nulos:,}
    </div>
    {table_html}
    <hr>
    <h2>Votos por Corte</h2>
    <div class="chart">
        <img class="chart-img" src="data:image/png;base64,{votes_per_cut_img}" alt="Votos por Corte">
    </div>
    <hr>
    <h2>Evolución de Votos</h2>
    <div class="chart">
        <img class="chart-img" src="data:image/png;base64,{img_base64}" alt="Votos en el tiempo">
    </div>
    <hr>
    <h2>Tendencia</h2>
    <div class="chart">
        <img class="chart-img" src="data:image/png;base64,{popularity_img_base64}" alt="Tendencia">
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

    stats = compute_stats(df)

    img_base64 = plot_votes_over_time(df)
    popularity_img_base64 = plot_popularity_trends(df)
    table_html = generate_results_table(stats)

    html = generate_html(img_base64, popularity_img_base64, table_html, df)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
