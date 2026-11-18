# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The owner and a few trusted people (family or partner), each with their own account. They live in Ecuador, bank with local banks (Banco Pichincha, Banco Guayaquil, Diners, etc.), and pay with Apple Pay, DeUna and mobile banking. They use the app equally on iPhone (installed to the home screen as a PWA, to record and confirm payments on the go) and on a computer (to review, analyze and plan).

## Product Purpose

A private personal-finance ledger: one place for bank accounts, cash, credit and debit cards, income, expenses, transfers, card payments and monthly budgets. Success means every real payment ends up recorded with the right category and account with minimal effort, and balances, card debt and budgets stay accurate.

## Positioning

Payments made on the iPhone arrive automatically through an iOS Shortcuts webhook (Apple Pay transaction trigger, DeUna and bank notification text) into a pending inbox. The user confirms each one with a tap; the app learns each merchant's category and card, so known merchants then register on their own.

## Operating Context

- iPhone: Shortcuts automation fires after an Apple Pay payment; DeUna and bank alerts are sent as text. The user opens the app to confirm pending payments.
- Computer: reviewing the dashboard, transactions, budgets and exporting CSV reports.
- Money is USD (Ecuador). Dates follow Ecuador time (America/Guayaquil).
- Deployed on Render with a Supabase PostgreSQL database.

## Capabilities and Constraints

- FastAPI + SQLAlchemy backend, Jinja2 templates with Bootstrap 5, Chart.js, vanilla JS. No build step.
- Modules: accounts, cards (credit utilization, cut-off and due dates), transactions with automatic balance sync and reversal, categories, budgets and alerts, CSV export, pending inbox with learned merchant rules, iOS webhook with personal token.
- Only last four digits of cards are stored; never full card numbers or credentials.
- Not a public product: there is no marketing site to maintain.

## Brand Commitments

Name: FinancialApp. Existing logo at `frontend/static/img/logo.png` (also app icons). Interface language: Spanish (Ecuador). No other binding brand assets.

## Evidence on Hand

No testimonials, statistics or marketing claims exist. Do not invent claims such as "100% private", "24/7" or setup times.

## Product Principles

1. Accuracy over decoration: balances and debts must be trustworthy and easy to verify.
2. Recording a payment should take one tap; anything uncertain waits in the pending inbox instead of being guessed.
3. Plain, honest Spanish copy; no hype.
4. Works equally well with a thumb on an iPhone and with a mouse on a large screen.
5. Personal data stays private to each user.
