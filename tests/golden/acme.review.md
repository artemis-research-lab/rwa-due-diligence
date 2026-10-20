# Review packet acme round 1

## Coverage

| group | CONFIRMED | SELF_REPORTED | THIRD_PARTY_REPORTED | INFERRED | UNRESOLVED | CONFLICTING |
|---|---|---|---|---|---|---|
| A layers and entities | 11 | 14 | 0 | 4 | 51 | 0 |
| B L1->L2 | 2 | 23 | 0 | 1 | 88 | 1 |
| C L2->L3 and default | 0 | 39 | 0 | 2 | 151 | 0 |
| D holder rights | 0 | 7 | 0 | 1 | 8 | 0 |
| E L3 business | 1 | 5 | 1 | 1 | 13 | 0 |
| F flows | 2 | 11 | 0 | 1 | 3 | 0 |
| O other | 14 | 36 | 0 | 1 | 12 | 0 |
| S supports | 0 | 4 | 0 | 0 | 4 | 0 |

## Section 1 preview

| id | type | material | blocking | k_checks | impact | statement |
|---|---|---|---|---|---|---|
| R1 | unreconciled_transaction | yes | no | -- | ownership | The memorandum reports the X13 loans as sold to E13; the independent review still lists them on the E6 balance sheet. |
| G1 | gap | yes | yes | K1 | capital_control, ownership | Issuer financial statements and the custody agreement are not public. |
| G3 | gap | no | yes | K4 | security | The security agreement over the leased equipment is not public. |
| U1 | scope_unresolved | no | yes | -- | security | The memorandum and the independent review may describe different coverage periods of the credit insurance. |

4 shown; 2 more open findings in section 6

## Portfolio components

| strategy | component | deployment | products | counted totals |
|---|---|---|---|---|
| T1 Acme equipment credit | CORE_CREDIT | DEPLOYED_VERIFIED [CONFIRMED] | P1 | 25000000 USDC CURRENT\_BALANCE @2026-09-30; 25150000 USD POSITION\_VALUE @2026-09-30 |
| T2 Acme commodity trade finance | CORE_CREDIT | DISCLOSED_UNVERIFIED [SELF_REPORTED] | P2 | -- |
| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | -- [UNRESOLVED] | P2 | 5000000 USDC CURRENT\_BALANCE @2026-10-01 |

## Framework completeness

| strategy | K1 L1 legal counterparty | K2 L1->L2 legal claim | K3 L2->L3 method | K4 L2->L3 security | K5 Loss waterfall | K6 Holder look-through | K7 L3 business |
|---|---|---|---|---|---|---|---|
| T1 Acme equipment credit | CONFIRMED | SELF_REPORTED | SELF_REPORTED | UNRESOLVED | SELF_REPORTED | SELF_REPORTED | SELF_REPORTED |
| T2 Acme commodity trade finance | CONFIRMED | UNRESOLVED | SELF_REPORTED | SELF_REPORTED | UNRESOLVED | INFERRED | SELF_REPORTED |

## Three-layer chains

- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[DL; secured\] -\> E7 Example Equipment Lessors Ltd (L3) -\> \[OTHER\] -\> E10 (L3-O)
- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[AP; ?\] -\> E8 Example Receivables Originator (L3)
- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[sale; true sale; loan INFERRED\] -\> E13 Example Loan Buyer Fund (transferee)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured\] -\> E9 (L3)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[REPO; secured; alt A1a\] -\> E9 (L3)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured; alt A1b\] -\> E9 (L3)
- T3 Acme treasury sleeve: E1 Acme Yield Issuer Ltd (L1) -\> \[OTHER\] -\> E11 Example Stablecoin Issuer Ltd (issuer) -\> \[look-through\] -\> E12 (reserve)

## Amounts

| strategy | interface | entry | kind | value | unit | basis | as_of | scope | counted | reason |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | X2 | 0 | L1_L2 | 25000000 | USDC | CURRENT_BALANCE | 2026-09-30T12:00:00Z | USDC supplied by E1 to the E5 credit pool, read at the block | yes | counted |
| T1 | X2 | 1 | L1_L2 | 25150000 | USD | POSITION_VALUE | 2026-09-30 | E1 units in Acme Credit Fund LP | yes | counted |
| T1 | X2 | 2 | L1_L2 | 18000000 | USD | CUMULATIVE_FUNDED | 2026-06-30 | AUP loan sample: 12 loans funded 2026-01-01 to 2026-06-30 (S9); management figure, not tested | no | basis CUMULATIVE_FUNDED not counted |
| T1 | X13 | 0 | asset_sale | 3000000 | USD | SALE_PROCEEDS | 2026-08-15 | Proceeds of the X13 loan sale to E13 | no | not a funding edge |
| T3 | X9 | 0 | sleeve_holding | 5000000 | USDC | CURRENT_BALANCE | 2026-10-01 | Stablecoin held by E1 in the treasury sleeve | yes | counted |
| T3 | X10 | 0 | reserve_lookthrough | 5000000 | USD | RESERVE_LOOKTHROUGH | 2026-09-30 | Reserve assets of E11 backing the sleeve stablecoin | no | not a funding edge |

## Alternative paths

- A1 (T2): a X11; b X12

## Conflicts

| finding | conflict status | scope match | resolution | subjects | assertion sources |
|---|---|---|---|---|---|
| D1 | CONFLICTING | matched | open | X6.terms | S7, S1 |
| D2 | RESOLVED | matched | resolved | X4.security | S8, S5 |
| R1 | UNRECONCILED_TRANSACTION | matched | open | X13 | S8, S5 |
| U1 | SCOPE_UNRESOLVED | not_matched | open | Z1.coverage | S8, S5 |

## Provenance

| claim | status | origin | assurance | sources |
|---|---|---|---|---|
| T1.l3\_business.performance | verified | auditor_procedure | TESTED | S9 |
| X2.amounts\[2\].value | self_reported | issuer_management | NOT_TESTED | S9 |

## QA

| id | rule | result | detail |
|---|---|---|---|
| QA1 | basis | pass | ok |
| QA2 | lookthrough | pass | ok |
| QA3 | alternative | pass | ok |
| QA4 | proceeds | pass | ok; unverified: X13.amounts\[0\] |
| QA5 | asof | pass | ok |
| QA6 | stockflow | pass | ok |
| QA7 | provenance | pass | ok |
| QA8 | conflicts | pass | ok |
| QA9 | placeholder | pass | ok |
| QA10 | section1 | pass | ok |
| QA11 | deployment | pass | ok |

## Migration checks pending

- none

## Material findings

- **G1** [legal] Issuer financial statements and the custody agreement are not public. (S8)
- **R1** [credit] The memorandum reports the X13 loans as sold to E13; the independent review still lists them on the E6 balance sheet. (S5, S8)

## Blocking gaps

- **G1** [legal] Issuer financial statements and the custody agreement are not public. (S8)
- **G3** [credit] The security agreement over the leased equipment is not public. (S8)

## Other gaps

- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)

## Discrepancies

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7) -- subjects: X6.terms -- scope: Both state the vault fee charged to P2 holders; S7 is the March 2026 version.
- **D2** [credit] The memorandum describes the equipment loans as secured; the independent review describes them as unsecured. (S5, S8) -- subjects: X4.security -- scope: Both describe the security of the X4 equipment loans as currently documented.

## Scope unresolved

- **U1** [credit] The memorandum and the independent review may describe different coverage periods of the credit insurance. (S5, S8) -- subjects: Z1.coverage -- scope: The memorandum covers the 2026 policy year; the review may describe the 2025 policy.

## Unreconciled transactions

- **R1** [credit] The memorandum reports the X13 loans as sold to E13; the independent review still lists them on the E6 balance sheet. (S5, S8) -- subjects: X13 -- scope: Both accounts concern the X13 sale of the equipment loan pool in August 2026.

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
# answer G<k>|D<k>|U<k>|R<k> : <text>
# drop G<k>|D<k>|U<k>|R<k> : <reason>
# note <text>
# priority N<a>,N<b>,...
# limit N<k> <calls 1..20>
# allow-fallback N<k> archive|browser
# finalize
```
