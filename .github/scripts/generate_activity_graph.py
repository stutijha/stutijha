import json
import os
import urllib.request
from datetime import date, timedelta

USERNAME = "stutijha"
TOKEN = os.environ["GITHUB_TOKEN"]

query = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""

end = date.today()
start = end - timedelta(days=364)
payload = json.dumps({
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": f"{start.isoformat()}T00:00:00Z",
        "to": f"{end.isoformat()}T23:59:59Z",
    },
}).encode()

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "stutijha-activity-graph",
    },
)

with urllib.request.urlopen(request) as response:
    result = json.load(response)

if result.get("errors"):
    raise RuntimeError(result["errors"])

days = [
    d
    for w in result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    for d in w["contributionDays"]
]
days = [d for d in days if start.isoformat() <= d["date"] <= end.isoformat()]

# Weekly totals make the chart readable even when one day has a much larger spike.
weeks = []
for i in range(0, len(days), 7):
    chunk = days[i:i + 7]
    if chunk:
        weeks.append({
            "date": chunk[0]["date"],
            "count": sum(d["contributionCount"] for d in chunk),
        })

width, height = 900, 230
left, right, top, bottom = 18, 18, 18, 34
chart_w = width - left - right
chart_h = height - top - bottom
max_count = max([w["count"] for w in weeks] or [1])
step = chart_w / max(1, len(weeks) - 1)

# Gentle square-root scaling keeps small activity visible without hiding larger activity.
points = []
for i, w in enumerate(weeks):
    x = left + i * step
    normalized = (w["count"] / max_count) ** 0.5
    y = top + chart_h - normalized * chart_h
    points.append((x, y))


def smooth_path(pts, closed_base_y=None):
    """Catmull-Rom -> cubic Bezier, so the line curves instead of zig-zagging."""
    if len(pts) < 3:
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} "
        d += " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts[1:])
        return d

    p = [pts[0]] + pts + [pts[-1]]
    d = f"M{p[1][0]:.1f},{p[1][1]:.1f} "
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d += f"C{c1x:.1f},{c1y:.1f} {c2x:.1f},{c2y:.1f} {p2[0]:.1f},{p2[1]:.1f} "
    return d


line_path = smooth_path(points)
area_path = (
    f"M{left:.1f},{top+chart_h:.1f} L{points[0][0]:.1f},{points[0][1]:.1f} "
    + line_path.split(" ", 1)[1]
    + f" L{left+chart_w:.1f},{top+chart_h:.1f} Z"
)

labels = []
for i, w in enumerate(weeks):
    if w["date"][8:10] <= "07":
        labels.append((left + i * step, w["date"][:7]))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<defs>
  <linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#C8A2E8" stop-opacity="0.35"/>
    <stop offset="100%" stop-color="#C8A2E8" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="lineStroke" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#C8A2E8"/>
    <stop offset="100%" stop-color="#FF69B4"/>
  </linearGradient>
</defs>
<rect width="100%" height="100%" rx="10" fill="#0d1117"/>
'''

# Subtle grid, without adding a title inside the image.
for tick in range(5):
    y = top + chart_h - (tick / 4) * chart_h
    svg += f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#21262d" stroke-width="1"/>'

svg += f'''
<path d="{area_path}" fill="url(#areaFill)"/>
<path d="{line_path}" fill="none" stroke="url(#lineStroke)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
'''

for x, y in points:
    svg += (
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#C8A2E8" opacity="0.18"/>'
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#FFF3A0"/>'
    )

for x, label in labels:
    svg += f'<text x="{x:.1f}" y="{height-10}" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">{label}</text>'

svg += '</svg>\n'

os.makedirs("assets", exist_ok=True)
with open("assets/activity-graph.svg", "w", encoding="utf-8") as f:
    f.write(svg)
