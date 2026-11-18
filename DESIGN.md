---
name: FinancialApp
description: Private personal-finance ledger set like an engraved banknote, printed in storm gray, matte black and safety orange.
colors:
  storm-50: "#F2F4F5"
  storm-100: "#DEE2E5"
  storm-200: "#CBD1D6"
  storm-300: "#AEB6BD"
  storm-400: "#7D8892"
  carbon-950: "#0F1011"
  carbon-900: "#17181A"
  carbon-800: "#1E2023"
  carbon-700: "#2B2E32"
  carbon-600: "#23262A"
  carbon-500: "#4A5058"
  safety: "#FF6B1A"
  safety-ink: "#A8430A"
  safety-wash: "#FFE3D2"
  income: "#2E6B3F"
  income-wash: "#D7E7DB"
  expense: "#B0261C"
  expense-wash: "#F6DAD7"
  field: "#FFFFFF"
  ink-muted: "#49515A"
  ink-faint: "#6B747D"
typography:
  display:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "clamp(2.75rem, 7vw, 4.5rem)"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "-0.02em"
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
    fontVariation: "\"wdth\" 78"
  wordmark:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.55rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0em"
    fontVariation: "\"wdth\" 78"
  headline:
    fontFamily: "Archivo, system-ui, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.02em"
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
    fontVariation: "\"wdth\" 78"
  title:
    fontFamily: "Archivo, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.01em"
  title-sm:
    fontFamily: "Archivo, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Archivo, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
  body-sm:
    fontFamily: "Archivo, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
  label:
    fontFamily: "Archivo, system-ui, -apple-system, \"Segoe UI\", sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0em"
rounded:
  bar: "2px"
  ink: "3px"
  sm: "6px"
  md: "10px"
  lg: "14px"
  sheet: "16px"
  pill: "999px"
spacing:
  xxs: "4px"
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "24px"
  xxl: "32px"
  gutter-desktop: "40px"
components:
  button-primary:
    backgroundColor: "{colors.carbon-600}"
    textColor: "{colors.field}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.carbon-700}"
    textColor: "{colors.field}"
  button-primary-active:
    backgroundColor: "{colors.carbon-800}"
    textColor: "{colors.field}"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.carbon-800}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    height: "40px"
  button-outline-hover:
    backgroundColor: "{colors.storm-200}"
    textColor: "{colors.carbon-900}"
  button-danger:
    backgroundColor: "{colors.expense}"
    textColor: "{colors.field}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    height: "40px"
  input:
    backgroundColor: "{colors.field}"
    textColor: "{colors.carbon-900}"
    rounded: "{rounded.sm}"
    height: "42px"
  panel:
    backgroundColor: "{colors.storm-50}"
    textColor: "{colors.carbon-900}"
    rounded: "{rounded.md}"
    padding: "20px"
  chip:
    backgroundColor: "{colors.storm-200}"
    textColor: "{colors.carbon-900}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
  chip-alert:
    backgroundColor: "{colors.safety-wash}"
    textColor: "{colors.safety-ink}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
  chip-danger:
    backgroundColor: "{colors.expense-wash}"
    textColor: "{colors.expense}"
    rounded: "{rounded.pill}"
    padding: "1px 8px"
  count-badge:
    backgroundColor: "{colors.safety}"
    textColor: "{colors.carbon-950}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    height: "22px"
    padding: "0 7px"
  rail:
    backgroundColor: "{colors.carbon-800}"
    textColor: "{colors.storm-100}"
    width: "236px"
  rail-link-active:
    backgroundColor: "{colors.carbon-900}"
    textColor: "{colors.safety}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  tabbar:
    backgroundColor: "{colors.carbon-800}"
    textColor: "#B9C0C7"
    height: "64px"
  tab-active:
    textColor: "{colors.safety}"
---

# Design System: FinancialApp

## Overview

**Creative North Star: "The Engraved Ledger"**

Money is read the way a banknote is read: the big number is set like a denomination, and every account is printed in its own bank's ink. The world is industrial rather than ornamental. A light storm-gray ground carries near-white panels separated by hairline gray rules; a matte black rail (desktop) or top bar and tab bar (iPhone) frames everything; safety orange appears only where something needs the user's attention. Engraving survives in two places only: the condensed, heavy, tabular figures, and the guilloche funds rosette on the Resumen.

Density is that of an operating tool used on a thumb and on a large screen equally. Panels are flat, information sits in ruled rows and figure lines rather than in stacks of identical cards, and charts that compare months share one fixed scale. The interface speaks Spanish (Ecuador): amounts are written $1.234,56 with a true minus sign (U+2212), percentages with a decimal comma, dates as "5 nov" (year added only when it is not the current one).

Confirmed rejections from the brief: the category's blue sidebar, rows of four identical KPI cards, the donut chart, gradients and glass.

**Key Characteristics:**
- Three-color world: storm gray ground, matte black frame and primary actions, safety orange for attention only.
- Bank colors exist only as account and card ink (dots, row inks, meters, rosette bands).
- One typeface, Archivo, in two widths: condensed 78% heavy for figures and the wordmark, normal width for all UI.
- Tabular, lining numerals on every surface.
- Flat panels on hairline rules; the only lifted object is the modal.
- Spanish (Ecuador) money and date formatting as a visual invariant.

## Colors

An industrial palette: cool storm grays and near-blacks do almost all the work, with one hot signal color held in reserve and a red/green pair kept for money direction.

### Primary
- **Matte Black** (carbon-800): the frame. Desktop rail, iPhone top bar and tab bar, the mobile pending strip, browser theme color.
- **Carbon Action** (carbon-600): primary buttons, checked checkboxes and toggles, links, focus outline, the rosette medallion. Hover lifts to carbon-700, press sinks to carbon-800.
- **Deep Carbon** (carbon-900): body ink and the active rail item's well. carbon-950 is the text color on safety orange and the modal backdrop.

### Secondary
- **Safety Orange** (safety): attention only. Pending counts, the active navigation item (rail text and tab), the "Nuevo" marker and the 2px inset ring on unseen pending payments, text selection, link underlines, the focus glow on form fields, the skip link.
- **Safety Ink** (safety-ink) on **Safety Wash** (safety-wash): the readable form of orange on light ground, for "Cerca del límite" and "Vence en N días" chips and warning alerts.

### Tertiary
- **Ledger Green** (income) with **Green Wash** (income-wash): income amounts, positive month balance, income bars, success alerts.
- **Ledger Red** (expense) with **Red Wash** (expense-wash): expense amounts, negative net worth, expense bars, destructive buttons and the "Superado" chip.

### Neutral
- **Storm Ground** (storm-100): page background, read-only fields, input-group addons.
- **Storm Panel** (storm-50): panels, ruled row lists, modals, sheets, auth panel.
- **Storm Rule** (storm-200): hairline rules between rows and panels; also chip, meter and progress tracks, outline-button hover.
- **Storm Rule Strong** (storm-300): input borders, outline-button borders, table header rule, the ledger's top rule, rosette track circles.
- **Storm Slate** (storm-400): default ink when an account has no bank color; the rosette's "Otras cuentas" band.
- **Field White** (field): input surfaces and text on dark buttons.
- **Muted Ink** (ink-muted): labels, secondary lines, table headers. **Faint Ink** (ink-faint): placeholders only.
- **Carbon Slate** (carbon-500): neutral bars (category spend), focus border on fields, empty-state icons, disabled primary.

### Named Rules
**The Attention Rule.** Safety orange marks only what needs the user: something waiting, something new, where they are, something close to its limit. Never a primary button, never decoration, never a chart series. Bootstrap's warning and info buttons are deliberately neutralized to outline gray.

**The Bank Ink Rule.** A bank's own color appears only as the ink of its account or card: the 10-12px ink square, the row's ink mark, its meter fill, its rosette band. It never tints a panel, a button or text.

**The Money Direction Rule.** Green means money in and red means money out; neither is used for anything else except success and destructive states.

## Typography

**Display Font:** Archivo, condensed (wdth 78), with system-ui fallback
**Body Font:** Archivo, normal width, with system-ui, -apple-system, Segoe UI fallback

**Character:** One grotesque in two widths. The condensed heavy cut gives figures the compressed, engraved authority of a denomination; the normal width keeps the UI plain and readable. Loaded as a variable font (wdth 62-125, wght 400-800).

### Hierarchy
- **Display** (700, condensed, clamp(2.75rem, 7vw, 4.5rem), 0.95): the net-worth figure only. Cents are split off, set at roughly half size and raised (vertical-align 0.72em) like a banknote's denomination; the figure turns red when negative.
- **Wordmark** (800, condensed, 1.55rem rail / 1.3rem top bar / 2rem auth): "FinancialApp" in the frame.
- **Headline** (700, condensed, 1.6rem, 1): ledger-line figures and row balances (1.5rem in ink rows, 1.75rem for pending amounts, 1.35rem on phones).
- **Title** (700, 1.5rem, 1.3rem on phones): page titles. **Title Small** (700, 1rem): panel and section titles; modal titles at 1.0625rem.
- **Body** (400, 0.9375rem): UI text. Form inputs are 1rem so iOS never auto-zooms. Page intros cap at 62ch.
- **Body Small** (0.8125rem): row sub-lines, legends, metadata.
- **Label** (600, 0.75rem, sentence case): definition-list terms, table headers, chips, badges. No uppercase, no tracking.

### Named Rules
**The Datamatics Rule.** Every number is tabular and lining (set globally on body). Columns of amounts must align digit for digit.

**The Two Widths Rule.** Condensed width is reserved for money figures and the wordmark. Small print attached to a figure (a `small` under a ledger value) drops back to normal width and 500 weight.

## Layout

Two shells from one template. At 992px and up, a fixed 236px matte black rail sits on the left and content is padded 32px top, 40px sides, 48px bottom. Below 992px the rail disappears for a 56px sticky top bar (wordmark, round storm-50 "+" button, profile) and a fixed 64px five-slot tab bar (four sections plus "Más", which opens a bottom sheet with the rest); content pads 20px/16px and clears the tab bar. Safe-area insets are honored at top and bottom. Content maxes at 1280px.

Every page opens with a page head: title and a one-line muted intro at left, actions at right, wrapping on small screens. Summary numbers sit in a **ledger line**: a ruled strip (strong rule above, hairline below) of label-over-figure pairs in an auto-fit grid of 140px minimum columns, two columns on phones. Lists are ruled rows inside one panel, not grids of cards.

The Resumen uses a main column plus a 360px side column at 1200px and up (pending queue, credit cards); below that, a mobile pending strip in matte black replaces the side queue's position at the top. Spacing rhythm steps 4, 8, 12, 16, 20, 24, 32, 40; panels pad 20px, ink rows 16px by 18px.

## Elevation & Depth

Flat by default. Depth comes from tonal layering (storm-100 ground, storm-50 panel, white field) and 1px rules, not shadows. Bootstrap's shadow utilities are forcibly zeroed inside the app.

### Shadow Vocabulary
- **Modal lift** (`box-shadow: 0 24px 48px -12px rgba(15, 16, 17, 0.4)`): modal dialogs only, over a carbon-950 backdrop at 45% opacity.
- **Attention ring** (`box-shadow: inset 0 0 0 2px var(--safety)`): marks an unseen pending payment until it is seen. A state, not elevation.
- **Field focus glow** (`box-shadow: 0 0 0 3px rgba(255, 107, 26, 0.22)`): inputs, selects and checks on focus, with the border shifting to carbon-500.

### Named Rules
**The Flat Panel Rule.** Panels, rows and cards never cast shadows. If something must stand forward, it is a modal.

## Shapes

Softly squared. Controls and small containers use a 6px radius; panels and row lists 10px; modals and the auth panel 14px; the bottom sheet 16px on its top corners only. Counts, chips and badges are full pills. Ink marks are 3px-rounded squares (never circles), bars are 2px-rounded, meters 3px. The one circle is the mobile "+" button and profile target. The `details` disclosure uses a drawn chevron (two 1.5px borders rotated) instead of the native marker.

## Components

### Buttons
Plain and firm: dark slabs for the one main action, gray outlines for everything else.
- **Shape:** gently squared (6px), 600 weight, 40px minimum height (34px small).
- **Primary:** carbon-600 with white text; hover carbon-700, active carbon-800, disabled carbon-500. Bootstrap's success button is mapped to the same carbon.
- **Outline / Secondary:** transparent, carbon-800 text, storm-300 border; hover fills storm-200; active storm-300. Warning, info and outline-success variants all render as this neutral outline.
- **Danger:** expense red with white text; hover a deeper red. Outline-danger is red text on a pale red border, filling red on hover.
- **Segmented filters:** outline buttons; the selected one fills carbon-700 with white text.

### Chips
- **Style:** pill, 0.75rem 600, storm-200 ground with ink text ("Inactiva").
- **State:** chip-alert in safety ink on safety wash (near limit, due soon); chip-danger in expense on expense wash (exceeded).

### Count Badge
Safety orange pill with carbon-950 text, 22px (18px on the tab icon), hidden at zero. Sits at the right of the Pendientes rail link and on the tab icon; it is the main reason orange exists.

### Cards / Containers
- **Corner Style:** 10px.
- **Background:** storm-50 on the storm-100 ground.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px storm-200.
- **Internal Padding:** 20px; panel heads put a 1rem bold title left and a 0.875rem 600 link right, baseline-aligned.

### Inputs / Fields
- **Style:** white field, storm-300 border, 6px radius, 42px min height, 1rem text, faint-ink placeholder; label above in 0.8125rem 600 muted ink.
- **Focus:** border to carbon-500 plus a 3px orange glow at 22% opacity.
- **Disabled / Read-only:** storm-100 fill. Amount fields accept "1.234,50", "4,5" or "4.50" and are parsed to a dot decimal for the API.

### Navigation
- **Rail (desktop):** matte black, wordmark top, links 0.9375rem 500 in light gray with a line icon; hover fills carbon-700; active sits in a carbon-900 well with safety orange text and icon. Profile and logout at the foot above a carbon-700 rule.
- **Top bar and tab bar (iPhone):** matte black; tabs are icon over 0.6875rem 600 label, active in safety orange. "Más" opens a storm-50 bottom sheet of ruled links; the logout link is red.

### Ink Row (signature)
The list unit for accounts, cards and budgets: a three-column grid (12px ink square, title and sub-line, right-aligned condensed figure), 16px by 18px padding, hairline-ruled, all inside one panel. The bank color arrives as a single custom property and drives the ink square and the meter fill (6px storm-200 track). A detail line spans under title and figure for meters, chips and row actions. Card numbers show as last four digits with slight tracking.

### Ledger Line (signature)
Replaces KPI cards: label (0.75rem 600 muted) over condensed 1.6rem figure, optional normal-width small note beneath, in a ruled auto-fit strip.

### Funds Rosette (signature)
Resumen only. One concentric guilloche band per account (top five, the rest grouped as "Otras cuentas" in storm-400), drawn as nine interlaced sine threads in the bank's ink around thin storm-300 track circles, arc length proportional to balance (minimum visible sweep about 12 degrees; the real percentage lives in the legend). A fine epitrochoid medallion in carbon-600 at 55% opacity sits at the center. Bands draw in over 1.4s on the ease-out curve unless reduced motion is requested. A legend of ink squares, account, bank, amount and percentage accompanies it.

### Fixed-Scale Bars
Monthly income and expense bars share one maximum across all six months; 10px bars, 2px radius, green and red, with tabular values right-aligned in a 96px column. Category bars are 6px carbon-500.

### Danger Zone
Destructive actions live at the bottom of their edit dialog, below a hairline rule, behind a two-step ask and confirm swap. They never sit in a row or toolbar.

## Do's and Don'ts

### Do:
- **Do** format every amount through the shared money formatter: $1.234,56, U+2212 minus, explicit + only where direction matters.
- **Do** write dates as "5 nov", adding the year only outside the current year.
- **Do** set money figures in Archivo condensed 78% at 700, with tabular lining numerals.
- **Do** keep safety orange for pending counts, active navigation, unseen marks, near-limit and due-soon chips, and focus glow.
- **Do** carry each bank's color as a row or legend ink through the ink custom property, falling back to storm-400 when none is set.
- **Do** put summary numbers in a ruled ledger line and lists in ruled ink rows inside one panel.
- **Do** keep every monthly comparison on one fixed scale.
- **Do** isolate deletes in a danger zone with an ask and confirm step.
- **Do** keep form inputs at 1rem and touch targets at 40px or more.

### Don't:
- **Don't** use safety orange for primary buttons, chart series, headings or decoration.
- **Don't** let a bank color tint a panel, a button, a heading or body text.
- **Don't** add shadows to panels or rows, or use gradients or glass.
- **Don't** build rows of identical KPI cards or donut charts; use the ledger line and the rosette.
- **Don't** use the condensed width for UI text, labels or paragraphs.
- **Don't** uppercase or letter-space labels; they are sentence-case 600.
- **Don't** use a hyphen as a minus sign or a dot as the decimal separator in displayed amounts.
