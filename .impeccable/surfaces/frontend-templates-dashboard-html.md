---
version: 1
slug: "frontend-templates-dashboard-html"
primary_target: "frontend/templates/dashboard.html"
related_targets: ["frontend/templates/base.html","frontend/templates/pending.html","frontend/templates/app.html"]
---

# Surface brief: FinancialApp app shell and Dashboard

Scope: the whole signed-in app (shell, Dashboard first, then Pendientes, Movimientos, Cuentas, Tarjetas, Presupuestos) plus login/registro. Mode: Operate.

Audience and job: the owner and family check what they have, what they owe and how the month goes (Dashboard), and confirm payments arriving from the iPhone (Pendientes). Used equally on iPhone (PWA) and computer.

Constraints: keep each bank's color to identify accounts. Palette and type pinned by the user (second revision, replacing sand/olive/yellow and Bodoni/Public Sans): storm gray, matte black, safety orange; a different typeface. Avoid looking like a generic bank app. No marketing page, no simulation buttons, no hype copy.

## Direction contract

THESIS: Money read like an engraved banknote: figures set like denominations and every account printed in its own bank ink. Refuses the category's blue sidebar, four identical KPI cards and donut chart.

OWN-WORLD: Light storm-gray ground (#DEE2E5) with near-white storm panels and hairline gray rules; matte black (#1E2023) rail, mobile top bar, tab bar and primary buttons; safety orange (#FF6B1A) reserved for attention only: pending counts, active navigation, new-payment marks, warning actions, link underlines. Bank colors appear only as account inks. Archivo throughout: condensed (wdth 78%) heavy for headline figures and the wordmark, normal width for UI, tabular numerals everywhere. Flat panels, no gradients or glass. Translation of the banknote world: engraving survives as the guilloche center of the funds rosette and the denomination-style figures, rendered in the pinned industrial palette.

STORY: In one glance the user sees net worth, available money and card debt, which account holds what, and whether anything from the iPhone is waiting; one tap reaches Pendientes.

FIRST VIEWPORT: Desktop: matte black left rail (brand, navigation, pending count in safety orange). Main: net worth figure large at left with available, debt and month savings beneath; at right the funds rosette. Right column: pending queue. Below: latest transactions table and 6-month income/expense bars on one fixed scale. Mobile: top bar, figure, rosette, pending queue, bottom tab bar.

FORM: Papel moneda grabado (sucre banknote engraving), candidate 6 of 7, seed: seed:331611068ab64de7. Signature move: the funds rosette, one concentric guilloche ring per account in its bank ink, arc length proportional to balance, with a legend; replaces the donut. Raises: new payments stay marked in safety orange until seen (gate board); destructive actions isolated (console); all monthly charts share one fixed scale (folio); one tabular numeric voice (datamatics).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
