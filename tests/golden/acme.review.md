# Review packet acme round 1

## Coverage

| group | CONFIRMED | SELF_REPORTED | THIRD_PARTY_REPORTED | INFERRED | UNRESOLVED | CONFLICTING |
|---|---|---|---|---|---|---|
| A layers and entities | 10 | 13 | 0 | 4 | 50 | 0 |
| B L1->L2 | 0 | 22 | 0 | 1 | 72 | 0 |
| C L2->L3 and default | 0 | 35 | 0 | 1 | 127 | 1 |
| D holder rights | 0 | 7 | 0 | 1 | 8 | 0 |
| E L3 business | 0 | 5 | 1 | 1 | 14 | 0 |
| F flows | 2 | 11 | 0 | 1 | 3 | 0 |
| O other | 14 | 36 | 0 | 1 | 12 | 0 |
| S supports | 0 | 4 | 0 | 0 | 4 | 0 |

## Portfolio components

| strategy | component | products | counted total |
|---|---|---|---|
| T1 Acme equipment credit | CORE_CREDIT | P1 | 25000000 n/d |
| T2 Acme commodity trade finance | CORE_CREDIT | P2 | -- |
| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | P2 | 5000000 USD |

## Framework completeness

| strategy | K1 L1 legal counterparty | K2 L1->L2 legal claim | K3 L2->L3 method | K4 L2->L3 security | K5 Loss waterfall | K6 Holder look-through | K7 L3 business |
|---|---|---|---|---|---|---|---|
| T1 Acme equipment credit | CONFIRMED | SELF_REPORTED | SELF_REPORTED | CONFLICTING | SELF_REPORTED | SELF_REPORTED | SELF_REPORTED |
| T2 Acme commodity trade finance | CONFIRMED | UNRESOLVED | SELF_REPORTED | SELF_REPORTED | UNRESOLVED | INFERRED | SELF_REPORTED |

## Three-layer chains

- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[DL; secured\] -\> E7 Example Equipment Lessors Ltd (L3) -\> \[OTHER\] -\> E10 (L3-O)
- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[AP; ?\] -\> E8 Example Receivables Originator (L3)
- T1 Acme equipment credit: P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[sale; true sale\] -\> E13 Example Loan Buyer Fund (transferee)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured\] -\> E9 (L3)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[REPO; secured; alt A1a\] -\> E9 (L3)
- T2 Acme commodity trade finance: P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured; alt A1b\] -\> E9 (L3)
- T3 Acme treasury sleeve: E1 Acme Yield Issuer Ltd (L1) -\> \[OTHER\] -\> E11 Example Stablecoin Issuer Ltd (issuer) -\> \[look-through\] -\> E12 (reserve)

## Allocation

| strategy | interface | kind | amount | basis | counted | reason |
|---|---|---|---|---|---|---|
| T1 | X2 | L1_L2 | 25000000 | GROSS_FUNDED | yes | counted |
| T1 | X13 | asset_sale | 3000000 USD | SALE_PROCEEDS | no | basis SALE_PROCEEDS |
| T3 | X9 | sleeve_holding | 5000000 USD | GROSS_FUNDED | yes | counted |
| T3 | X10 | reserve_lookthrough | 5000000 USD | LOOKTHROUGH | no | basis LOOKTHROUGH |

## Alternative paths

- A1 (T2): a X11; b X12

## Material findings

- **G1** [legal] Issuer financial statements and the custody agreement are not public. (S8)

## Scope checks pending

- none

## Blocking gaps

- **G1** [legal] Issuer financial statements and the custody agreement are not public. (S8)
- **G3** [credit] Perfection of the security interest over the leased equipment is not evidenced. (S8)

## Other gaps

- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)

## Discrepancies

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7) -- scope: Both state the vault fee charged to P2 holders; S7 is the March 2026 version.
- **D2** [credit] The memorandum describes the equipment loans as secured; the independent review describes them as unsecured. (S5, S8) -- subjects: X4.security -- scope: Both describe the security of the X4 equipment loans as currently documented.

## Scope unresolved

- **U1** [credit] The memorandum and the independent review may describe different coverage periods of the credit insurance. (S5, S8) -- subjects: Z1.coverage

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
