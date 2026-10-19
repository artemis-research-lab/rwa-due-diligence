# Review packet acme round 1

## Coverage

| group | CONFIRMED | PARTIALLY_VERIFIED | UNRESOLVED | CONFLICTING |
|---|---|---|---|---|
| A layers and entities | 10 | 14 | 32 | 0 |
| B L1->L2 | 0 | 15 | 27 | 0 |
| C L2->L3 and default | 0 | 21 | 56 | 1 |
| D holder rights | 0 | 8 | 8 | 0 |
| E L3 business | 0 | 6 | 8 | 0 |
| F flows | 2 | 12 | 3 | 0 |
| O other | 14 | 37 | 12 | 0 |

## Framework completeness

| strategy | K1 L1 legal counterparty | K2 L1->L2 legal claim | K3 L2->L3 method | K4 L2->L3 security | K5 Loss waterfall | K6 Holder look-through | K7 L3 business |
|---|---|---|---|---|---|---|---|
| T1 Acme equipment credit | CONFIRMED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | CONFLICTING | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED |
| T2 Acme commodity trade finance | CONFIRMED | UNRESOLVED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | UNRESOLVED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED |

## Three-layer chains

- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[DL; secured\] -\> E7 Example Equipment Lessors Ltd (L3) -\> \[OTHER\] -\> E10 (L3-O)
- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[AP; ?\] -\> E8 Example Receivables Originator (L3)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured\] -\> E9 (L3)

## Blocking gaps

- **G1** [legal] Issuer financial statements and the custody agreement are not public. (S8)
- **G3** [credit] Perfection of the security interest over the leased equipment is not evidenced. (S8)

## Other gaps

- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)

## Discrepancies

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7)
- **D2** [credit] The memorandum describes the equipment loans as secured; the independent review describes them as unsecured. (S5, S8)

## Structural changes

- **C1** [onchain] Upgrade admin changed from a single key to a 2-of-3 multisig. (S4)

## Issuer requests

- **Q1** (priority 1) Security agreement and lien filings for the equipment loans -- Confirm whether the T1 loans are secured and the security interest is perfected (answers C2, C5)
- **Q2** (priority 2) Commodity purchase and offtake contracts for the trade vault -- Identify the T2 counterparties and how the L3 business generates cash (answers A4, E1, E2)

## Proposed next searches

- **N1** Custody agreement and issuer accounts -- Company registry filings -- Confirm custody and financials (resolves G1; est 6 calls)
- **N2** Current vault fee schedule -- Project docs and vault contract -- Resolve fee discrepancy (resolves G2, D1; est 4 calls)
- **N3** Lien filings over the leased equipment -- Examplestan collateral registry -- Resolve the secured/unsecured discrepancy (resolves G3, D2; est 3 calls)

## Directives template

```text
accept N1 | accept N2 | accept N3
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
