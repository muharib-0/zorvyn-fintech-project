# Engineering Thinking — Finance Dashboard Backend
> How I approached this project, the questions I asked, and why I made the decisions I made.

---

## 1. First Thing I Asked — What Are We Actually Building?

Before writing a single line of code I stopped and questioned the premise of the assignment.

The assignment said "finance dashboard system" — but that phrase is vague. It could mean anything from a personal budgeting app like Slice to an enterprise ERP. I asked:

- Are we connecting to bank accounts?
- Are we tracking personal finances or company finances?
- Who are the actual users of this system?

This matters because the answer completely changes the data model, the role design, and the security requirements. A consumer finance app has very different concerns than an internal company tool.

**Decision:** I framed this as an internal company finance tool — a system used by a company's finance team and senior leadership to track organizational income and expenses manually. No bank integration, no external APIs, no personal data. This made every subsequent decision cleaner.

---

## 2. I Questioned the Role Design Before Accepting It

The assignment gave me Viewer, Analyst, Admin as suggested roles. I did not just implement them blindly.

My first instinct was — if this is a company finance system, why would any random employee be able to see salary data, client revenue, and ad spend? That is a serious security concern in the real world.

Then I reframed it: **the users of this system are not random employees — they are the finance team and senior leadership only.** Accounts are created exclusively by the Admin. Nobody outside this group even has a login.

This reframing made the Viewer role legitimate instead of a security problem.

**Decision:** Viewer = CEO, CTO, Board Members. They need financial visibility for strategic decisions but should not interact with individual records. This is intentional — giving them read-only access is a feature, not a limitation.

---

## 3. I Caught That Viewer and Analyst Were Too Similar

After the initial role design, I noticed the distinction between Viewer and Analyst was paper thin — both could view records, both could see the dashboard. That is bad design. Two roles that do the same thing is not a role system, it is noise.

I asked myself: what does a CEO actually need versus what does a Finance Analyst actually need day to day?

- **CEO:** Needs to answer "Is the company healthy?" — total income, total expense, burn rate, runway, revenue sources. Big picture only. No time or need for individual transaction records.
- **Analyst:** Needs to answer "Why, where, and how much exactly?" — individual records, filters, trend analysis, category breakdowns. This is their actual job.

**Decision:** Viewer gets dashboard-only access — aggregated summaries, no individual records. Analyst gets full read access to records plus all analytical endpoints. Now the roles are genuinely distinct and map to real organizational behavior.

---

## 4. I Thought About the Frontend Split Before Being Asked

I reasoned that the role separation naturally maps to two separate pages in any frontend:

- `/dashboard` — accessible to everyone, executive summary view
- `/analytics` — accessible to Analyst and Admin only, operational detail view

From this I derived a clean rule for my backend permission design:
- Endpoints that answer "are we healthy?" → Viewer and above
- Endpoints that answer "why and how much?" → Analyst and above
- Write operations → Admin only

This gave me a clear, justifiable permission matrix instead of arbitrary role assignments.

---

## 5. I Asked About Email Delivery Without Being Prompted

When thinking about the user creation flow — Admin creates users and hands out credentials — I naturally asked: how does the user receive their credentials in a real system?

The answer is email. In real internal tools, the system emails credentials to the new user automatically.

I chose to implement this as a documented stub rather than wiring a real SMTP service. The reasoning:
- Wiring SMTP (SendGrid, AWS SES) would take 3-5 hours
- The assignment does not evaluate email functionality
- A stub with clear documentation shows I understand the production flow without wasting assessment time

**Documented as:** Future enhancement. Stub exists in `apps/users/services.py`. Production implementation would use SendGrid or AWS SES.

---

## 6. I Chose Django Over FastAPI Deliberately

FastAPI was on the table. I know it. But I made a deliberate choice to use Django for this assessment.

My reasoning:
- This is an assessment, not a learning exercise. The evaluator judges code quality and architecture, not framework choice.
- A polished Django submission beats a shaky FastAPI one every time.
- Django's built-in admin panel is a free bonus — the evaluator can see live data without me building a frontend.
- FastAPI learning should happen without time pressure, after this submission.

This is not a default choice — it is a considered one. I know what I am trading off.

---

## 7. I Added Redis Without Being Asked

Looking at the dashboard endpoints — summary, category totals, monthly trends — I recognized these are aggregation queries running over potentially thousands of records. They are read-heavy and the result does not change unless a record is created or modified.

Recalculating these on every request is wasteful and does not scale. The natural solution is caching.

**Decision:** Cache all dashboard aggregation endpoints in Redis with a 15-minute TTL. Invalidate the cache on any write operation (create, update, soft delete) so data stays fresh. This is the standard cache-invalidation-on-write pattern.

This was not in the assignment requirements. I added it because it reflects how a production system should actually behave.

---

## 8. I Questioned Whether Analyst Could "Manipulate" Records

When the discussion came up about Analyst manipulating records to their needs, I immediately asked for clarification before implementing anything.

Manipulation in a finance context could mean:
- Filtering and searching — legitimate, that is their job
- Editing record values — not legitimate, Analyst is read only

The answer was filtering, sorting, and searching only. I then implemented this cleanly using DRF's built-in filter backends — no custom code needed, no new endpoints needed. The Analyst gets full query flexibility over existing data without any write access.

---

## 9. I Chose DecimalField Over FloatField for Money

This is a decision most developers get wrong. Float types have inherent binary precision issues that cause rounding errors. For example:

```python
>>> 0.1 + 0.2
0.30000000000000004
```

In a finance system this is unacceptable. A ₹1,00,000 transaction must store and return exactly ₹1,00,000.00 — not ₹99,999.99999999997.

`DecimalField` uses Python's `Decimal` type which stores exact decimal representations. This is the correct choice for any monetary value, always.

---

## 10. I Chose Soft Delete for Financial Records

Hard deleting financial records is dangerous for several reasons:
- Audit trail is destroyed — you cannot explain historical imbalances
- Compliance risk — financial data often has legal retention requirements
- Accidental deletion is unrecoverable

I implemented `is_deleted = BooleanField(default=False)` on the FinancialRecord model. Delete operations set this flag to True. All queries filter on `is_deleted=False` by default. Records are never actually removed from the database.

---

## 11. I Designed Categories With Business Logic Validation

Categories are split between expense-only and income-only. For example, `OFFICE_RENT` can only be an expense — it makes no sense as income. `CLIENT_REVENUE` can only be income.

I implemented cross-field validation in the serializer's `validate()` method that checks the category against the record type and raises a validation error if they are incompatible.

This is the kind of domain-specific business logic that separates a thoughtful backend from a generic CRUD implementation.

---

## 12. I Kept Aggregation Logic Out of Views

All dashboard calculation logic lives in `apps/dashboard/services.py`, not in views.

Views handle one thing — HTTP. They receive a request, call a service function, and return a response. The actual business logic — aggregations, date truncations, cache reads and writes — lives in the service layer.

This makes the codebase testable (services can be unit tested without HTTP), maintainable (business logic is in one place), and readable (views are thin and obvious).

---

## 13. The `/recent/` Endpoint Behaves Differently by Role

This was a deliberate design decision. The same endpoint — `/api/dashboard/recent/` — returns different data depending on who is calling it.

- VIEWER gets: record_type, category, amount, date — enough context, no sensitive detail
- ANALYST and ADMIN get: full record including notes and who created it

This shows that access control is not just about blocking endpoints — it is also about controlling data exposure within accessible endpoints. A CEO does not need to see internal notes written by the finance team. An Analyst does.

---

## Summary of Key Decisions

| Decision | What I chose | Why |
|----------|-------------|-----|
| System type | Internal company tool | Eliminates ambiguity, makes role design meaningful |
| Framework | Django over FastAPI | Confidence, assessment context, built-in admin |
| Viewer role framing | CEO/CTO, executive view | Justifies read-only access as a feature not a gap |
| Role separation | Dashboard vs Analytics page split | Meaningful functional distinction, not arbitrary |
| Money field | DecimalField | Float precision errors unacceptable in finance |
| Delete strategy | Soft delete only | Audit trail, compliance, recoverability |
| Caching | Redis on dashboard endpoints | Read-heavy aggregations, cache-invalidation-on-write |
| Aggregation | Django ORM, not Pandas | Pushes computation to PostgreSQL, no memory loading |
| Business logic | services.py, never in views | Testability, maintainability, separation of concerns |
| Email delivery | Stub with documentation | Production awareness without wasted assessment time |
| Category validation | Cross-field serializer validation | Domain-specific business logic, not generic CRUD |
| /recent/ endpoint | Role-aware serializer | Data exposure control within accessible endpoints |
