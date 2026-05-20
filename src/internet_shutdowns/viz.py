"""Visualization helpers.

Each project picks ONE visual style and declares it in the README:

- Plotly                 — best for interactive dashboards, hover-rich maps.
- matplotlib + seaborn   — best for static, publication-quality figures.
- plotnine               — best when grammar-of-graphics composition matters.

Uncomment the corresponding block below to activate the chosen style.
``save_figure`` works with all three.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIGURES_DIR = ROOT / "figures"
FIGURES_DIR.mkdir(exist_ok=True)


# ============================================================================
# Choose ONE block and uncomment it for the project.
# ============================================================================

# ----- Option A: matplotlib + seaborn -----
# import matplotlib.pyplot as plt
# import seaborn as sns
#
# sns.set_theme(style="whitegrid", context="notebook")
# plt.rcParams.update({
#     "figure.dpi": 100,
#     "savefig.dpi": 200,
#     "savefig.bbox": "tight",
#     "font.family": "sans-serif",
# })

# ----- Option B: Plotly -----
# import plotly.io as pio
# pio.templates.default = "plotly_white"

# ----- Option C: plotnine -----
# from plotnine import theme_minimal, theme_set
# theme_set(theme_minimal())

# ============================================================================


def save_figure(fig, name: str, dpi: int = 200) -> Path:
    """Save a figure to ``figures/<name>.png``.

    Auto-detects matplotlib, Plotly, and plotnine figures.
    """
    path = FIGURES_DIR / f"{name}.png"

    if hasattr(fig, "write_image"):
        # Plotly Figure
        fig.write_image(str(path), scale=2)
    elif hasattr(fig, "save"):
        # plotnine ggplot
        fig.save(str(path), dpi=dpi, verbose=False)
    elif hasattr(fig, "savefig"):
        # matplotlib Figure
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    else:
        raise TypeError(f"Don't know how to save figure of type {type(fig)!r}")

    return path
