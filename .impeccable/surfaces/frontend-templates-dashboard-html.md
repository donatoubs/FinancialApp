---
version: 1
slug: "frontend-templates-dashboard-html"
primary_target: "frontend/templates/dashboard.html"
related_targets: ["frontend/templates/base.html","frontend/templates/app.html","frontend/templates/pending.html","frontend/templates/transactions.html","frontend/templates/accounts.html"]
---

# Surface brief: FinancialApp app shell, Resumen, Movimientos, Cuentas, Analíticas

Scope: the whole signed-in app plus login/registro, rebuilt as a new visual identity (replaces the storm/black/orange world). Mode: Operate. Theme: automatic light/dark from the device (user-pinned).

Audience and job: the owner and family check where their money is, what came in and went out, and confirm iPhone payments; equally on iPhone (PWA) and computer. User-pinned brief: premium fintech craft (Revolut, Monzo, Linear, Apple Wallet, Ramp, Mercury as quality bar, never copied); minimal but not empty; strong hierarchy; no generic dashboard cards, decorative charts, purposeless gradients, heavy shadows or rounded-everything. Keep every existing function; invent no financial data. New section: Analíticas (own nav item).

## Direction contract

THESIS: A naturalist's field log for money: every account wears its own color band, like a ringed Galápagos bird, and every movement is a precise, timestamped observation. Refuses the card-grid dashboard and the donut.

OWN-WORLD: Light: volcanic-ash ground #F3F3F0, basalt ink #16191C, hairline rules; dark: basalt ground #101315 with ash ink. Basalt rail in both themes. One reserved accent, blue-footed-booby turquoise (#2C9FB3 / #45B9CC dark), only for the active and selected. Money direction: deep green in, Sally-Lightfoot red-orange out. Bank colors appear only as account bands. Hanken Grotesk throughout, tabular numerals, figures on an 8px grid. Flat sections divided by rules; corner radius 6px max, mostly square.

STORY: The visitor sees the total and how it splits across accounts in one band, knows today's in/out and net, scans the timestamped log, and reaches registering or confirming in one tap.

FIRST VIEWPORT: Desktop: basalt rail left (brand, nav, Registrar). Main left: "Saldo total" with date, the 88px balance, the account band strip with legend, then a facts line (ingresos, gastos, balance neto, deuda tarjetas). Right column: "Por confirmar" then "Registro" of recent movements with time and account tags. Below: income/expense months on one fixed scale and spending by category. Mobile: top bar, balance, bands, facts, pending strip, log, tab bar.

FORM: Bitácora de Galápagos, candidate 7 of 7, seed: seed:331611068ab64de7. Signature move: the account bands, a proportional strip of color bands (one per account, bank ink) that reappears as small stacked tags on every movement and account row; hovering or choosing an account lights its band and dims the others. Raises: selection lights one band (transit); one reserved accent for active only (orienteering); figures aligned to a strict 8px grid (Crouwel); a changed balance updates digit by digit (split-flap).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
