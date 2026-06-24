# VALI Resume and Interview Blurbs

## A. One-line resume bullet

Built VALI, a Python research engine for prediction-market signal validation
using public attention/market-price divergence, walk-forward testing, leakage
controls, execution-aware gates, and explicit falsification thresholds;
delivered a 167-test validated MVP while documenting data-readiness blockers
instead of overclaiming alpha.

## B. Short project description

VALI tests whether public behavioral attention can lead prediction-market price
conviction around scheduled Fed events. I built the typed Python engine,
point-in-time data contracts, prior-only signal pipeline, grouped walk-forward
evaluation, read-only Kalshi/Google Trends provider boundaries, and reproducible
reporting. I also predeclared baselines and falsification gates and audited the
local data before allowing an empirical run. The audit found substantial Kalshi
price history but no canonical point-in-time attention history, so the project
correctly blocks alpha and trading claims pending remediation.

## C. Interview explanation (60–90 seconds)

I built VALI to explore a simple prediction-market question: can public
behavioral attention move before market price conviction, and does that gap
contain information beyond the market's own probability? I formalized attention
as `A`, executable price conviction as `P`, and tested the signed divergence of
their prior-only velocities across meeting-grouped walk-forward folds. The
interesting work was not just the formula—it was making the research hard to
fool. Outcomes are physically isolated from signal frames, features and
baselines are frozen before evaluation, providers are public and read-only, and
execution or capacity claims are disabled when historical depth is unavailable.

I decomposed the code into domain, data, configuration, research, execution,
artifact, provider, and CLI boundaries and protected it with a 167-test baseline.
Then I audited the actual data and stopped the empirical run because only three
fixture days of attention history exist. That is the point I would emphasize:
the repository is a working research engine and a demonstration of disciplined
quant ownership, not a claim that alpha or trading readiness has already been
proven.

All inputs are public-data-only. The project uses no private Kalshi data,
proprietary order flow, order submission, live trading, or `P_flow`.
