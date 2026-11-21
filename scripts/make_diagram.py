"""Draws the pipeline + ML diagram used in the app, README, report and slides.

    python scripts/make_diagram.py      -> app/static/pipeline.png and app/static/pipeline.svg
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NAVY, TEXT, GREY = "#1f3a5f", "#1e2b3c", "#6b7280"
TEAL_FILL, YELLOW, WHITE, BG = "#e3edf0", "#f1d96b", "#ffffff", "#f6f5f2"

fig, ax = plt.subplots(figsize=(20, 9), dpi=150)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 200)
ax.set_ylim(0, 90)
ax.axis("off")


def box(x, y, w, h, title, body="", fill=TEAL_FILL, edge=NAVY, tsize=12.5, bsize=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6",
                                fc=fill, ec=edge, lw=1.6))
    ty = y + h - 3.2 if body else y + h / 2
    ax.text(x + w / 2, ty, title, ha="center", va="center", fontsize=tsize, fontweight="bold", color=TEXT)
    if body:
        ax.text(x + w / 2, y + (h - 5) / 2, body, ha="center", va="center", fontsize=bsize, color=TEXT,
                linespacing=1.35)


def arrow(x1, y1, x2, y2, style="-|>", color=NAVY, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=18, color=color,
                                 lw=1.8, linestyle=ls, shrinkA=2, shrinkB=2))


ax.text(100, 86, "Who Can Rise the Most: from survey files to a decision tool", ha="center", va="center",
        fontsize=21, fontweight="bold", color=NAVY)
ax.text(100, 81.5, "Open data from randomised trials in 8 places, 11,522 households", ha="center", va="center",
        fontsize=12.5, color=GREY)

# row 1: the pipeline
Y, H = 45, 28
box(2, 60, 24, 13, "Survey files", "Kenya, Uganda +\n6 graduation countries\n(Harvard Dataverse)", WHITE, bsize=10)
box(2, 45, 24, 12, "World Bank API", "PPP, exchange rates, CPI", WHITE, bsize=10)
box(30, Y, 22, H, "Python loaders", "in Docker\n\nloads each file once\nadds new columns\nretries a slow API")
box(56, Y, 20, H, "Snowflake RAW", "untouched data\n\n+ a load log\n(file hash, rows,\nnew columns)")
ax.add_patch(FancyBboxPatch((80, Y), 42, H, boxstyle="round,pad=0.4,rounding_size=1.6", fc=TEAL_FILL, ec=NAVY,
                            lw=1.6))
ax.text(101, Y + H - 3.2, "dbt on Snowflake", ha="center", va="center", fontsize=12.5, fontweight="bold",
        color=TEXT)
layers = [("Bronze", "views on\nraw tables"), ("Silver", "1 clean row\nper household"),
          ("Gold", "types, effects,\nspending")]
for i, (name, txt) in enumerate(layers):
    bx = 82.5 + i * 13.3
    ax.add_patch(FancyBboxPatch((bx, Y + 7.5), 11.5, 13, boxstyle="round,pad=0.3,rounding_size=1.2",
                                fc=WHITE, ec=NAVY, lw=1.2))
    ax.text(bx + 5.75, Y + 17.3, name, ha="center", va="center", fontsize=10.5, fontweight="bold", color=TEXT)
    ax.text(bx + 5.75, Y + 12.1, txt, ha="center", va="center", fontsize=9, color=TEXT, linespacing=1.25)
    if i < 2:
        arrow(bx + 11.7, Y + 14, bx + 13.2, Y + 14)
ax.text(101, Y + 3.5, "17 models · 68 tests · contracts on gold", ha="center", va="center", fontsize=10,
        color=TEXT)
box(126, Y, 22, H, "Analysis / ML",
    "Python\n\nwho gains most\nwhat $100 buys\nthe trade-off with\nreaching the poorest", YELLOW)
box(152, Y, 19, H, "Snowflake ML", "results\nwritten back\n\nread-only user\nfor the app")
box(175, Y, 23, H, "Streamlit app", "for NGOs and\ngovernments\n\n10 pages\nupload your\nown data", WHITE)

arrow(26.6, 66, 30, 62)
arrow(26.6, 51, 30, 54)
for x1, x2 in [(52.4, 56), (76.4, 80), (122.4, 126), (148.4, 152), (171.4, 175)]:
    arrow(x1, Y + H / 2, x2, Y + H / 2)

# row 2 left: running and testing it
ax.add_patch(FancyBboxPatch((2, 5), 116, 32, boxstyle="round,pad=0.4,rounding_size=1.6", fc=WHITE, ec=GREY,
                            lw=1.2, linestyle="--"))
ax.text(60, 33.3, "Running and testing it", ha="center", va="center", fontsize=12.5, fontweight="bold",
        color=TEXT)
box(6, 8, 52, 21, "GitHub Actions (CI)",
    "every branch is built and tested\nin separate CI_ schemas.\nThen every app page is opened\n\n"
    "main + every Monday: the real tables", TEAL_FILL, NAVY, 11.5, 10)
box(62, 8, 52, 21, "Airflow + Cosmos",
    "the whole pipeline as one DAG:\nloaders, every dbt model and test\nas its own task, analysis\n\n"
    "runs locally in Docker", TEAL_FILL, NAVY, 11.5, 10)
arrow(60, 37.6, 60, Y - 0.6, style="<|-|>", color=GREY, ls="--")

# row 2 right: the ML in detail
ax.add_patch(FancyBboxPatch((122, 5), 76, 32, boxstyle="round,pad=0.4,rounding_size=1.6", fc=WHITE, ec=NAVY,
                            lw=1.6))
ax.text(160, 33.3, "Inside the analysis", ha="center", va="center", fontsize=12.5, fontweight="bold", color=TEXT)
items = [("ANCOVA per household type", "gain vs no cash, with a 95% range"),
         ("Causal forest (EconML)", "checks the types without knowing them"),
         ("Budget simulation", "targeting rules vs reaching the poorest"),
         ("Meta-analysis", "8 places combined: poorer vs less poor")]
for i, (title, sub) in enumerate(items):
    yy = 27.2 - i * 6.2
    ax.add_patch(FancyBboxPatch((126, yy - 2.3), 3.2, 4.6, boxstyle="round,pad=0.2,rounding_size=0.8",
                                fc=YELLOW, ec=NAVY, lw=1))
    ax.text(127.6, yy, str(i + 1), ha="center", va="center", fontsize=10, fontweight="bold", color=TEXT)
    ax.text(131.5, yy + 0.9, title, ha="left", va="center", fontsize=11, fontweight="bold", color=TEXT)
    ax.text(131.5, yy - 1.6, sub, ha="left", va="center", fontsize=10, color=TEXT)
arrow(137, Y - 0.6, 137, 37.6, color=NAVY)

out = ROOT / "app" / "static"
out.mkdir(exist_ok=True)
fig.savefig(out / "pipeline.png", facecolor=BG, bbox_inches="tight", pad_inches=0.2)
fig.savefig(out / "pipeline.svg", facecolor=BG, bbox_inches="tight", pad_inches=0.2)
print("saved", out / "pipeline.png", "and .svg")
