import fs from "node:fs";

const token = process.env.GITHUB_TOKEN;
const username = process.env.GITHUB_USERNAME || "stutijha";

if (!token) throw new Error("GITHUB_TOKEN is required");

const to = new Date();
// Stuti's contribution history starts on 2025-08-07.
const from = new Date("2025-08-07T00:00:00Z");
const iso = (d) => d.toISOString();

const query = `
  query($login: String!, $from: DateTime!, $to: DateTime!) {
    user(login: $login) {
      contributionCalendar(from: $from, to: $to) {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
`;

const response = await fetch("https://api.github.com/graphql", {
  method: "POST",
  headers: {
    Authorization: `bearer ${token}`,
    "Content-Type": "application/json",
    "User-Agent": "stutijha-activity-graph"
  },
  body: JSON.stringify({ query, variables: { login: username, from: iso(from), to: iso(to) } })
});

if (!response.ok) throw new Error(`GitHub API returned ${response.status}`);
const body = await response.json();
if (body.errors) throw new Error(JSON.stringify(body.errors));

let days = body.data.user.contributionCalendar.weeks
  .flatMap((w) => w.contributionDays)
  .sort((a, b) => a.date.localeCompare(b.date));

const today = new Date().toISOString().slice(0, 10);
days = days.filter((d) => d.date >= "2025-08-07" && d.date <= today);
if (!days.length) throw new Error("No contribution data found");

const width = 1000, height = 390;
const left = 58, right = 18, top = 68, bottom = 58;
const plotW = width - left - right, plotH = height - top - bottom;
const max = Math.max(5, Math.ceil(Math.max(...days.map((d) => d.contributionCount), 0) / 5) * 5);
const step = days.length > 1 ? plotW / (days.length - 1) : plotW;
const x = (i) => left + i * step;
const y = (v) => top + plotH - (v / max) * plotH;
const points = days.map((d, i) => `${x(i).toFixed(1)},${y(d.contributionCount).toFixed(1)}`);
const line = points.join(" ");
const area = `${left},${top + plotH} ${line} ${x(days.length - 1)},${top + plotH}`;
const ticks = Array.from({ length: max / 5 + 1 }, (_, i) => i * 5);

const gridY = ticks.map((v) => `
  <line x1="${left}" y1="${y(v)}" x2="${width - right}" y2="${y(v)}" stroke="#183b66" stroke-width="1" stroke-dasharray="2 5"/>
  <text x="${left - 10}" y="${y(v) + 4}" text-anchor="end" fill="#2f81f7" font-size="12" font-family="Arial, sans-serif">${v}</text>
`).join("");

const labelEvery = Math.max(1, Math.floor(days.length / 10));
const gridX = days.map((d, i) => {
  if (i !== 0 && i !== days.length - 1 && i % labelEvery !== 0) return "";
  const label = d.date.slice(5);
  return `
  <line x1="${x(i)}" y1="${top}" x2="${x(i)}" y2="${top + plotH}" stroke="#183b66" stroke-width="1" stroke-dasharray="2 5"/>
  <text x="${x(i)}" y="${height - 25}" text-anchor="middle" fill="#2f81f7" font-size="11" font-family="Arial, sans-serif">${label}</text>
`;
}).join("");

const dots = days.map((d, i) => `
  <circle cx="${x(i)}" cy="${y(d.contributionCount)}" r="4.2" fill="#ff7a00"/>
`).join("");

const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#0d1117"/>
  <text x="${width / 2}" y="27" text-anchor="middle" fill="#2f81f7" font-size="18" font-weight="700" font-family="Arial, sans-serif">Stuti's Contribution Graph</text>
  <text x="18" y="${top + plotH / 2}" transform="rotate(-90 18 ${top + plotH / 2})" text-anchor="middle" fill="#2f81f7" font-size="12" font-family="Arial, sans-serif">Contributions</text>
  ${gridY}
  ${gridX}
  <polygon points="${area}" fill="#2f81f7" opacity="0.10"/>
  <polyline points="${line}" fill="none" stroke="#2f81f7" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
  ${dots}
  <text x="${width / 2}" y="${height - 5}" text-anchor="middle" fill="#2f81f7" font-size="12" font-family="Arial, sans-serif">2025-08-07 → ${today}</text>
</svg>
`;

fs.mkdirSync("assets", { recursive: true });
fs.writeFileSync("assets/activity-graph.svg", svg);
console.log(`Generated graph from 2025-08-07 to ${today} (${days.length} days).`);
