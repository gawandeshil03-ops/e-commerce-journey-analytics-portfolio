# Cart-recovery experiment design

## Decision

Decide whether a triggered saved-cart reminder should become the default
experience for recognized visitors who leave after adding an item to cart.

The observational baseline is useful for planning, not for estimating
treatment effect. In the fixed RetailRocket data, 4.93% of first observed cart
abandoners with a complete seven-day window transact later without a measured
intervention.

## Hypothesis

A reminder delivered shortly after an observed cart-abandonment session will
increase seven-day purchase conversion among eligible visitors without causing
an unacceptable increase in opt-outs, complaints, or low-quality orders.

## Eligibility and assignment

- Use a stable account or visitor identity that persists across sessions.
- Include the first session in the experiment period with at least one
  `addtocart` event and no `transaction` event.
- Close the session after 30 minutes of inactivity, then apply a fixed delivery
  delay. A two-hour delay is a reasonable starting treatment and should be
  agreed with CRM and product owners.
- Require a valid, consented delivery channel for an external message.
- Assign each visitor once and persist the variant. Repeated cart abandonment
  does not create another experimental unit.
- Randomize 50/50 at visitor level. Stratification by pre-assignment new versus
  returning status is acceptable if implemented before assignment.

Randomizing messages or sessions would allow one visitor to receive both
variants and would violate independence. Visitor-level assignment is the safer
unit.

## Variants

**Control:** current experience, with no experimental cart reminder.

**Treatment:** one saved-cart reminder after the fixed delay. Content, channel,
and discount policy must remain fixed during the test. A discount should not be
introduced in the first test unless the team is explicitly testing the combined
effect and can measure margin.

## Metrics

Primary metric:

```text
7-day purchase conversion =
assigned eligible visitors with at least one transaction within 7 days
----------------------------------------------------------------------
all assigned eligible visitors
```

Analyze the primary metric by intention to treat, including visitors for whom a
message was not delivered after assignment. Delivery failures are diagnostics,
not exclusions.

Secondary metrics:

- one-day purchase conversion;
- time from assignment to first transaction;
- transactions per assigned visitor within seven days;
- reminder delivery and click-through rates as mechanism diagnostics.

Guardrails:

- notification opt-out, unsubscribe, or complaint rate;
- cancellation, refund, and return rate;
- gross margin per assigned visitor;
- delivery failure rate;
- page or app performance if the treatment changes the product surface.

The public dataset contains none of these guardrails. They are required before
the experiment can support a launch decision.

## Sample size and duration

Planning assumptions:

- baseline seven-day conversion: 4.93%;
- two-sided alpha: 0.05;
- power: 0.80;
- minimum detectable effect: 25% relative, or 1.23 percentage points;
- target treatment rate: 6.16%;
- sample size: 5,416 visitors per arm, 10,832 total;
- observed inflow: about 1,483 first-time eligible visitors per complete week.

The acquisition period is approximately 7.3 weeks. Adding the seven-day outcome
window gives a planning duration of nine calendar weeks.

The 25% relative MDE is a feasibility choice, not a claim about expected lift.
A 20% MDE would require 8,286 visitors per arm and about 13 calendar weeks.

## Analysis plan

1. Validate sample ratio and assignment before reading the outcome.
2. Report counts, rates, absolute difference, relative difference, and a 95%
   confidence interval for the intention-to-treat effect.
3. Use a two-sided comparison of independent proportions for the primary
   analysis.
4. Do not stop early based on repeated unadjusted significance checks.
5. Treat new/returning and category cuts as pre-specified diagnostics unless
   the experiment is powered for interaction effects.
6. Check that missing outcomes, identity loss, and delivery failures are not
   imbalanced by variant.
7. Evaluate guardrails and practical magnitude even if the primary p-value is
   below 0.05.

## Decision rule

Recommend rollout only if:

- the lower bound of the primary effect is compatible with a meaningful
  positive impact;
- no material guardrail deterioration is observed;
- the effect is not driven by a logging or assignment issue;
- message delivery and contactability are high enough for the intervention to
  remain operationally useful.

If the confidence interval is wide around a useful effect, extend or repeat the
test rather than declaring no effect. If delivery is poor, fix the mechanism
before changing product strategy.

## Instrumentation required before launch

- `experiment_assigned` with visitor, variant, and assignment timestamp;
- `cart_abandonment_eligible` with the rule version;
- `reminder_scheduled`, `reminder_delivered`, `reminder_clicked`, and
  `reminder_suppressed` with reason;
- stable identity and consent status at assignment;
- `checkout_started`, `payment_failed`, and `order_completed`;
- order value, margin, cancellation, refund, and return.

## Main risks

- Anonymous visitor IDs may reset or split one person across devices.
- A visitor can purchase through another channel that is not logged.
- External messages require consent and a deliverable channel.
- Inventory, price changes, and promotions may alter both eligibility and
  conversion during a long test.
- A 30-minute session boundary is an analytical convention. In this dataset,
  changing it to 15 or 60 minutes moves the transaction-session rate by less
  than 0.1 percentage point, but production eligibility should still use one
  explicit rule.
