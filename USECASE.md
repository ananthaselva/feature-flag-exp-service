# Real-World Walkthrough (Uber Eats-style)

> Scenario: Uber Eats is rolling out a **new checkout** flow. They want employees to always see it, iOS users in Canada to see a **10%** canary, and everyone else stays on the old flow.


## Quick Glossary
* **Tenant**: An isolated namespace (customer, BU, or environment).
* **Flag**: A keyed switch that selects a **variant** for a user/context.
* **Variant**: A named outcome (e.g., `control`, `treatment`) with optional **weight**. Think of it as the “experience bucket” a user lands in - consider these variants of flag. In A/B testing, `control` and `treatment` are often used to represent the different groups. `A` being `control` and `B` being `treatment`. But flags can have many variants (A/B/n)—each with an optional weight used for default traffic split.
* **Rule**: An ordered targeting condition with an **action** that decides the variant. Think “if this user/cohort matches → do X.” Rules are evaluated **top-down; first match wins**.
  Examples:

  * `when: { attr: { role: "employee" } }` → `rollout: { variant: "treatment" }` (force a variant)
  * `when: { segment: "ca_ios_new_users" }` → `rollout: { percentage: { treatment: 0.10 } }` (10% canary)
    If no rule matches, the service falls back to the flag’s **default variant distribution**. Each rule should have a stable `id` so evaluations can report which rule fired.

* **Segment**: A **reusable cohort** referenced by rules (DRY for targeting). It describes who’s in the group using attribute criteria (your evaluator decides the exact shape).
  Examples: `employees`, `new_users_<30_days`, `vip_customers`, `ca_ios`.
  Segments are **tenant-scoped** and can be cached for fast lookups. Rules can then say “if user ∈ segment X, apply rollout Y.”

* **Bucket**: A **stable hash** mapped to a float in **`[0, 1)`** used for percentage rollouts. It’s computed from `(tenant, flag_key, user_id)` so a user’s bucket is **deterministic** for that flag and tenant (they won’t “flip-flop” on refresh).
  Example: bucket `0.037` < `0.10` ⇒ user falls into the 10% treatment canary.

* **Reason / Rule ID**: The **explanation** fields in an evaluation response for debuggability and analysis.

  * `reason`: why the user got that variant. Common values: `rule_match`, `default_distribution`, `flag_off`, (optionally) `explicit_deny`.
  * `rule_id`: the specific rule that matched (when `reason == "rule_match"`).
  * `details`: extra context like `{ "bucket": 0.037, "matched": {"segment":"ca_ios_new_users"} }`.
    Example response:

  ```json
  {
    "variant": "treatment",
    "reason": "rule_match",
    "rule_id": "r2",
    "details": { "bucket": 0.037 }
  }
  ```


### 1) Define a segment (cohort)

Create a segment for “CA iOS users who are **new** (joined ≤ 30 days)”.

```http
POST /v1/segments
X-Tenant-ID: ubereats-prod
Authorization: Bearer <token>
Content-Type: application/json

{
  "key": "ca_ios_new_users",
  "criteria": {
    "all": [
      {"attr": {"country": "CA"}},
      {"attr": {"os": "iOS"}},
      {"attr": {"account_age_days_lte": 30}}
    ]
  }
}
```

### 2) Create the flag with variants and rules

```http
POST /v1/flags
X-Tenant-ID: ubereats-prod
Authorization: Bearer <token>
Content-Type: application/json

{
  "key": "checkout_new",
  "description": "New checkout flow",
  "state": "on",
  "variants": [
    {"key": "control",   "weight": 1},
    {"key": "treatment", "weight": 1}
  ],
  "rules": [
    {
      "id": "r1",
      "when": {"attr": {"role": "employee"}},
      "rollout": {"variant": "treatment"}          // employees always
    },
    {
      "id": "r2",
      "when": {"segment": "ca_ios_new_users"},
      "rollout": {"percentage": {"treatment": 0.10}} // 10% canary
    }
  ]
}
```

**How it evaluates (top-down):**

1. If user’s `role == "employee"` → **treatment** (rule `r1`).
2. Else if user is in `ca_ios_new_users` → **10%** get **treatment** via deterministic bucket; others get **control**.
3. Else → use **default variant distribution** (here 50/50 from `variants` weights).

### 3) Evaluate for a few users

**Employee (always treatment):**

```http
POST /v1/evaluate
X-Tenant-ID: ubereats-prod
Authorization: Bearer <token>
Content-Type: application/json

{
  "flag_key": "checkout_new",
  "user": {
    "id": "u-emp-42",
    "attributes": {"role": "employee", "country": "US", "os": "Android"}
  }
}
```

**Response (shape):**

```json
{
  "variant": "treatment",
  "reason": "rule_match",
  "rule_id": "r1",
  "details": {"bucket": 0.734512}
}
```

**CA iOS new user (10% canary):**

```http
POST /v1/evaluate
X-Tenant-ID: ubereats-prod
Authorization: Bearer <token>
Content-Type: application/json

{
  "flag_key": "checkout_new",
  "user": {
    "id": "u-123",
    "attributes": {"country": "CA", "os": "iOS", "account_age_days": 7}
  }
}
```

**Response (two possibilities, but **deterministic** per user):**

* If bucket `< 0.10` → `treatment` with `rule_id: "r2"`
* Else → `control` with `rule_id: "r2"`

**Everyone else (default distribution):**

```http
POST /v1/evaluate
X-Tenant-ID: ubereats-prod
Authorization: Bearer <token>
Content-Type: application/json

{
  "flag_key": "checkout_new",
  "user": {"id": "u-usa-999", "attributes": {"country": "US", "os": "Android"}}
}
```

**Response (50/50 from variants weights):**

```json
{
  "variant": "control",
  "reason": "default_distribution",
  "details": {"bucket": 0.481203}
}
```

### 4) Ramp up safely

When metrics look good, bump the canary **10% → 25% → 50%** by editing rule `r2`:

```http
PUT /v1/flags/checkout_new
X-Tenant-ID: ubereats-prod
Authorization: Bearer <token>
Content-Type: application/json

{
  "state": "on",
  "rules": [
    {"id": "r1", "when": {"attr": {"role": "employee"}}, "rollout": {"variant": "treatment"}},
    {"id": "r2", "when": {"segment": "ca_ios_new_users"}, "rollout": {"percentage": {"treatment": 0.25}}}
  ]
}
```

Every change records an **audit** entry so you can answer “who changed what, when, and why.”

### 5) Tenancy keeps customers isolated

All calls include `X-Tenant-ID: ubereats-prod`. A request with `X-Tenant-ID: ubereats-staging` sees **different** flags/segments and results. Trying to access `ubereats-prod` data with `ubereats-staging` should **404**—this is part of your negative tests.