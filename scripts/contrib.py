"""Draw assets/contributions.svg from the last year of GitHub contributions.

Run by .github/workflows/contributions.yml every night. Needs GITHUB_TOKEN.
Private work is counted when "Private contributions" is on in the profile's
contribution settings.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.request

USER = os.environ.get("PROFILE_USER", "mercenary19961")
OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "contributions.svg"

# Crimson palette, from empty to busiest.
LEVELS = ["#1a1a1d", "#4a1420", "#8c1a2c", "#c41f36", "#ff3b54"]
LEVEL_INDEX = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
MONO = "'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], LEVEL_INDEX[d["contributionLevel"]]) for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def draw(total, weeks):
    pitch, size, top, left = 14, 11, 52, 16
    width = left * 2 + len(weeks) * pitch - (pitch - size)
    height = top + 7 * pitch + 30
    today = dt.date.today()
    month_total = sum(c for w in weeks for d, c, _ in w if d.startswith(today.strftime("%Y-%m")))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{total} contributions in the last year">',
        "<style>",
        ".c{animation:rise 9s linear infinite backwards}",
        "@keyframes rise{0%{opacity:0}1.5%{opacity:1}86%{opacity:1}90%{opacity:0}100%{opacity:0}}",
        "@media (prefers-reduced-motion:reduce){.c{animation:none}}",
        "</style>",
        f'<rect width="{width}" height="{height}" rx="8" fill="#0a0a0b"/>',
        f'<text x="{left}" y="30" font-family="{MONO}" font-size="20" font-weight="600" fill="#ff3b54">{total:,}</text>',
        f'<text x="{left + 8 + 12 * len(f"{total:,}")}" y="30" font-family="{MONO}" font-size="13" fill="#c9c4bc">contributions in the last year</text>',
        f'<text x="{width - left}" y="30" text-anchor="end" font-family="{MONO}" font-size="12" fill="#8a8a8f">{month_total:,} this month</text>',
    ]
    last_month = None
    for c, week in enumerate(weeks):
        x = left + c * pitch
        delay = c * 0.085
        for date, _count, level in week:
            r = dt.date.fromisoformat(date).weekday()
            row = (r + 1) % 7  # Sunday first, like GitHub
            y = top + row * pitch
            parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{LEVELS[0]}"/>')
            if level:
                parts.append(f'<rect class="c" style="animation-delay:{delay:.3f}s" x="{x}" y="{y}" width="{size}" height="{size}" rx="2" fill="{LEVELS[level]}"/>')
        month = week[0][0][:7]
        if month != last_month and dt.date.fromisoformat(week[0][0]).day <= 7:
            label = dt.date.fromisoformat(week[0][0]).strftime("%b")
            parts.append(f'<text x="{x}" y="{top + 7 * pitch + 18}" font-family="{MONO}" font-size="11" fill="#8a8a8f">{label}</text>')
            last_month = month
    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    total, weeks = fetch()
    OUT.write_text(draw(total, weeks))
    print(f"wrote {OUT} ({total} contributions, {len(weeks)} weeks)")
