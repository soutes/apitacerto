# Handoff: ApitaCerto — Dashboard + Classificação

## Overview
Two high-fidelity mockups for ApitaCerto, a dashboard that analyzes Brazil's Campeonato Brasileiro Série A segmented by referee, looking for statistical patterns of favoritism. Screens covered: **Dashboard** (season KPIs, referee highlights, standings preview) and **Classificação** (full 20-club standings table).

Editorial framing is a hard product requirement carried into the UI copy and layout: the design signals **statistical pattern**, never **accusation**. Copy like "não é veredito sobre uma decisão isolada" appears deliberately next to punitive referee stats — keep it (or an equivalent) when implementing.

## About the Design Files
The bundled `ApitaCerto Mockups.dc.html` is a **design reference built in HTML** — it renders standalone in a browser and shows intended layout, color, type, spacing, and micro-interactions. It is **not production code to copy verbatim**. Recreate it in the target codebase: **React 19 + Vite, plain CSS with custom properties** (no Tailwind, no component library — confirmed constraint from the design brief). Charts stay hand-rolled SVG.

## Fidelity
**High-fidelity.** Colors, type, spacing, and radii below are final values from the mockup, not placeholders.

## Which option to build
The file contains two visual options explored during review, both built from the same real data:
- **Option 2a (top of file, `#opt-2a`) — build this one.** It's the one iterated on last (pill top-of-sidebar nav → dark sidebar, glow shadows, dashed dividers, teal/gold/coral palette, whistle+ball logomark). Sidebar is dark (`oklch(20% 0.014 235)`).
- **Option 1a (`#opt-1a`, below it) — superseded reference only.** Earlier direction with a plain dark-navy sidebar and neutral white cards. Kept in the file for context; do not build it.

## Screens

### 1. Dashboard (`#opt-2a`, first artboard)
**Purpose**: at-a-glance season read — league-wide KPIs, which referees card most, home-side bias, and a 6-row standings preview.

**Layout**: 1440px desktop artboard, `display:flex`. Left: 232px fixed dark sidebar (logo + 5 nav pills). Right: flexible content column, `padding: 22-26px 28px 32px`, vertical stack with 16-22px gaps:
1. Header row (`justify-content:space-between`): page title + subtitle (left) · "Rodada 27 · em andamento" status pill + "Temporada 2026" gradient pill (right).
2. KPI row: `grid-template-columns: repeat(4,1fr)`, 16px gap. Each KPI card: white, 18px radius, colored glow `box-shadow` (no top color stripe — removed per feedback), 16-18px inner padding, entrance animation `fadeUp .5s ease both` staggered 0/.05/.1/.15s.
3. Two-column grid, `grid-template-columns: 1.5fr 1fr`, `align-items: stretch` (both columns must match height — a footer note is pinned to the bottom of the shorter card via `margin-top:auto` to prevent a visual gap).
   - Left: "Prévia da classificação" card — 6 rows (positions 1,2,3,4,5,12) with crest, club name, pts, jogos, saldo. Footer note: "Mostrando 6 de 20 posições…".
   - Right, stacked: "Árbitros que mais punem" card (ranked bars, NO medals/celebratory styling — deliberate, to avoid glamorizing a negative stat) → dashed-border "regra de nome longo" annotation card (see Edge cases) → "Viés de mandante" card (pill-badge values).

### 2. Classificação (`#cls-v2`, second artboard)
**Purpose**: full, dense, scannable 20-club standings table, portal-style.

**Layout**: same 1440px artboard/sidebar shell as Dashboard. Content column:
1. Header row: title + subtitle · status pill + season pill (same components as Dashboard).
2. "ZONAS" row: 4 pill legend chips (Libertadores grupos / playoff, Sul-Americana, Rebaixamento), each a tinted-bg pill with a colored dot + label, right-aligned, sitting above a dashed divider.
3. Table, `border-radius:14px`, `overflow:hidden`, `border:1px solid oklch(90% 0.006 80)`:
   - Header row: solid teal bg (`oklch(50% 0.12 195)`), 12 mono uppercase column labels + "FORMA".
   - Column grid: `44px 250px 56px 42px 40px 40px 40px 46px 46px 46px 42px 42px 104px` = Pos / Clube / Pts / J / V / E / D / GP / GC / SG / CA / CV / Forma.
   - Each row: `border-left: 6px solid <zoneColor>` (continental-zone indicator, by position, not by team performance — computed from rank, not fabricated), white bg, hover tint. Crest = circle with 2-3 letter initials + colored ring. Club name truncates with `text-overflow:ellipsis` + native `title` tooltip for full name.
   - "Forma" column: 5 small neutral gray dots — **placeholder only**, no data backing it yet (see Edge cases).
   - Rows without real backing data render at `opacity:0.55` with `—` in every numeric cell — never fabricated numbers.

## Edge cases the layout must survive (do not simplify away)
1. **Referee names up to 50 chars** (e.g. "Fernando Antonio Mendes de Salles Nascimento Filho"). Rule: display **first name + last surname token(s)** only in space-constrained UI (cards/lists); full name always available via native `title` tooltip. See the dashed-border "REGRA · NOME LONGO" annotation card in the Dashboard mockup — it documents the before/after transform, implement the same truncation function.
2. **Club names up to 23 chars** (e.g. "Fortaleza Esporte Clube", row 6 of the table). Rule: use the club's common abbreviated form where one exists (e.g. "Athletico-PR", "Fortaleza EC"); otherwise `white-space:nowrap` + `text-overflow:ellipsis` + `title` tooltip. Never wrap the table row height.
3. **Partial season**: current-season clubs can have 26 or 27 games played. Communicated via (a) a small amber "Rodada 27 · em andamento/jogos variam 26–27" status pill near the season selector, always visible, and (b) the per-row "J" column simply showing each club's real count — no extra badge per row.
4. **Club crest images**: production crests load from a CBF URL and will sometimes fail (irregular quality, some 404s). Fallback implemented here: a circular monogram (2-3 letter initials, white text) on a muted color pulled from a small fixed 6-color palette (cycled by row index — not team brand colors). Implement the `<img>` with an `onError` handler that swaps to this same monogram markup.
5. **Standings completeness**: this mockup only has real stats for positions 1,2,3,4,5,8,12 (from the brief) plus the name-only placeholder at position 6 (Fortaleza). Positions 7,9–11,13–20 are intentionally rendered with dashed stats and reduced opacity — **do not treat these as real data to copy**; wire the real 20-row dataset when implementing.

## Interactions & Behavior
- Nav pill hover: background tint (`style-hover` in mockup → CSS `:hover` in implementation).
- KPI card hover: `transform: translateY(-2px)`.
- Table row hover: light teal background tint.
- Entrance animation: KPI cards fade+slide up 8px over 0.5s, staggered 50ms apart, `ease`. Wrap in `@media (prefers-reduced-motion: reduce) { animation: none !important; transition: none !important; }` — required, not optional.
- No modals, no click-through navigation implemented in the mockup (static reference); nav pills are visual targets only — wire real routing.

## Design Tokens

**Colors** (OKLCH — convert to your token format, keep the values, don't re-derive):
- Page/artboard bg: `oklch(96% 0.006 80)` / `oklch(97% 0.01 80)`
- Sidebar bg (dark): `oklch(20% 0.014 235)`, border `oklch(15% 0.01 235)`
- Sidebar text (inactive): `oklch(78% 0.008 235)`; hover bg `oklch(28% 0.02 235)`
- Primary teal (brand/active states): `oklch(50-55% 0.12 195)`; gradient variant `oklch(58% 0.13 195) → oklch(45% 0.1 195)`; active-pill glow `oklch(52% 0.12 195 / 0.35-0.4)`
- Amber (in-progress/status): pill bg `oklch(90% 0.1 85)`, dot `oklch(45% 0.13 60)`, text `oklch(35% 0.1 60)`
- Coral/negative: `oklch(52-60% 0.15-0.17 25-30)`
- Positive green: `oklch(48% 0.13 145)`
- Continental zones: Libertadores-grupos `oklch(58% 0.13 145)`, Libertadores-playoff `oklch(72% 0.13 80)`, Sul-Americana `oklch(60% 0.11 235)`, Rebaixamento `oklch(55% 0.16 25)` (each with a light tint background + darker text variant for legend pills)
- Crest monogram palette (cycled): `oklch(52% 0.1 25)`, `oklch(50% 0.1 145)`, `oklch(50% 0.1 235)`, `oklch(55% 0.1 80)`, `oklch(50% 0.1 300)`, `oklch(48% 0.1 170)`
- White surfaces: `#fff`

**Typography**:
- UI/headings: **Plus Jakarta Sans** 500/600/700/800
- Numbers/data/labels: **JetBrains Mono** 500/600/700, `font-variant-numeric: tabular-nums` on every numeric cell
- Scale: KPI value 28px/700 mono · H2 22px/800 · Card title 14.5px/700 · Body/label 11-13px/500-700 · Table header 10.5px/700 mono uppercase

**Spacing**: sidebar padding `22px 16px`; card padding `16-20px`; stack gaps `10-26px`; grid gaps `16-20px`

**Radius**: logo badge `7-8px`; pills `999px`; cards `12-20px`; table container `12-14px`

**Elevation**: colored glow shadows only, never plain black — pattern `0 6px 20px <hue oklch>/0.08-0.18`; artboard-level shadow `0 10px 32px oklch(52% 0.12 195 / 0.12)`

**Dividers**: dashed 3px teal/coral-tinted (section headers) as an intentional stylistic choice; solid 1px hairlines elsewhere

## Assets
No external image/icon assets — logo is inline SVG (whistle shape + small pentagon "ball" accent, white on a teal/green gradient badge); crests are CSS monogram circles (see Edge case 4); all icons are hand-built minimal SVG (rects/circles/polygons only).

## Files
- `ApitaCerto Mockups.dc.html` — the design reference (open directly in any browser)
- `design-brief.md` — original product brief with the real dataset (standings, referee stats, league averages) used throughout the mockup — use this as your source of truth for real numbers, not values you might infer from the HTML
