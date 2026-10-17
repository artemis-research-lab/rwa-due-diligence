# Review packet acme round 1

## Coverage

| dimension | verified | self_reported | inferred | not_found |
|---|---|---|---|---|
| L legal | 10 | 7 | 3 | 10 |
| Y yield | 1 | 22 | 1 | 12 |
| F flows | 2 | 5 | 1 | 1 |
| C onchain | 9 | 0 | 0 | 0 |
| P project | 3 | 8 | 0 | 1 |

## Blocking gaps

- **G1** [legal] Issuer financial statements and the custody agreement are not public. (S8)

## Other gaps

- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)

## Discrepancies

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7)

## Structural changes

- **C1** [onchain] Upgrade admin changed from a single key to a 2-of-3 multisig. (S4)

## Proposed next searches

- **N1** Custody agreement and issuer accounts -- Company registry filings -- Confirm custody and financials (resolves G1; est 6 calls)
- **N2** Current vault fee schedule -- Project docs and vault contract -- Resolve fee discrepancy (resolves G2, D1; est 4 calls)

## Directives template

```text
accept N1 | accept N2
# reject N<k>
# add-source <url-or-path> : <why>
# answer G<k>|D<k> : <text>
# drop G<k>|D<k> : <reason>
# note <text>
# priority N<a>,N<b>,...
# limit N<k> <calls 1..20>
# allow-fallback N<k> archive|browser
# finalize
```
