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

width, height = 900, 260
left, right, top, bottom = 42, 18, 16, 38
chart_w = width - left - right
chart_h = height - top - bottom
max_count = max([d["contributionCount"] for d in days] or [1])
step = chart_w / max(1, len(days) - 1)
points = []
for i, d in enumerate(days):
    x = left + i * step
    y = top + chart_h - (d["contributionCount"] / max_count) * chart_h
    points.append((x, y))

line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
area = f"{left:.1f},{top+chart_h:.1f} " + line + f" {left+chart_w:.1f},{top+chart_h:.1f}"

labels = []
for i, d in enumerate(days):
    if d["date"][8:10] == "01":
        labels.append((left + i * step, d["date"][:7]))

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" rx="10" fill="#0d1117"/>
'''

# subtle horizontal grid and y-axis labels
for tick in range(5):
    value = max_count * tick / 4
    y = top + chart_h - (value / max_count) * chart_h
    label = str(round(value))
    svg += f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#21262d" stroke-width="1"/>'
    svg += f'<text x="4" y="{y+4:.1f}" fill="#6e7681" font-family="Arial, sans-serif" font-size="10">{label}</text>'

svg += f'''
<polygon points="{area}" fill="#C8A2E8" opacity="0.10"/>
<polyline points="{line}" fill="none" stroke="#89CFF0" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
'''

for x, y in points:
    svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.7" fill="#C8A2E8"/>'

for x, label in labels:
    svg += f'<text x="{x:.1f}" y="{height-10}" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">{label}</text>'

svg += '</svg>\n'

os.makedirs("assets", exist_ok=True)
with open("assets/activity-graph.svg", "w", encoding="utf-8") as f:
    f.write(svg)
