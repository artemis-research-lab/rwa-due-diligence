# RWA Due Diligence: Acme Yield

| field | value |
|---|---|
| slug | acme |
| root URL | https://acme-yield.example/ |
| run id | acme-20261001T080000Z |
| status | draft |
| rounds | 1 |
| started | 2026-10-01T08:00:00Z |
| finalized | -- |
| Report generated | draft 2026-10-20 |
| Data observed | 2026-06-30 to 2026-10-01 |
| skill version | 0.7.0 |
| schema version | rwa-dd/2.2 |

> DRAFT -- not finalized

## 1. Executive summary and critical findings

Acme Yield offers two products: a note (P1) financing equipment leases through a credit fund and a warehouse SPV (T1), and a vault (P2) financing commodity purchase and resale (T2). Entities are mapped to layers; the security over the T1 loans is disputed between sources.

### T1 Acme equipment credit

| question | answer |
|---|---|
| Who holds investor capital? | E1 Acme Yield Issuer Ltd (L1) \[SELF\_REPORTED\] |
| Who deploys credit? | E5 Acme Credit Fund LP (L2) \[SELF\_REPORTED\] |
| Who receives financing? | E7 Example Equipment Lessors Ltd (L3) \[SELF\_REPORTED\]; E8 Example Receivables Originator (L3) \[SELF\_REPORTED\] |
| Who must repay? | E7 Example Equipment Lessors Ltd (L3) \[SELF\_REPORTED\]; E8 Example Receivables Originator (L3) \[SELF\_REPORTED\]; cash flows from: E10 (L3-O) \[SELF\_REPORTED\] |
| Who can enforce the claim? | E1 \[SELF\_REPORTED\]; Security agent E3 enforces on default \[SELF\_REPORTED\] |
| Is deployment verified? | DEPLOYED\_VERIFIED \[CONFIRMED\] |

### T2 Acme commodity trade finance

| question | answer |
|---|---|
| Who holds investor capital? | E1 Acme Yield Issuer Ltd (L1) \[INFERRED\] |
| Who deploys credit? | E1 Acme Yield Issuer Ltd (L1/L2) \[SELF\_REPORTED\]; E1 Acme Yield Issuer Ltd (L1/L2) \[SELF\_REPORTED; alt A1a\]; E1 Acme Yield Issuer Ltd (L1/L2) \[SELF\_REPORTED; alt A1b\] |
| Who receives financing? | E9 (L3) \[SELF\_REPORTED\]; E9 (L3) \[SELF\_REPORTED; alt A1a\]; E9 (L3) \[SELF\_REPORTED; alt A1b\] |
| Who must repay? | E9 (L3) \[SELF\_REPORTED\]; E9 (L3) \[SELF\_REPORTED; alt A1a\]; E9 (L3) \[SELF\_REPORTED; alt A1b\] |
| Who can enforce the claim? | UNRESOLVED |
| Is deployment verified? | DISCLOSED\_UNVERIFIED \[SELF\_REPORTED\] |

### Critical findings

- [MATERIAL] [ownership] **R1** (UNRECONCILED_TRANSACTION) The memorandum reports the X13 loans as sold to E13; the independent review still lists them on the E6 balance sheet. (S5, S8)
- [MATERIAL] [BLOCKING] [K1] [capital_control, ownership] **G1** Issuer financial statements and the custody agreement are not public. (S8)
- [BLOCKING] [K4] [security] **G3** The security agreement over the leased equipment is not public. (S8)
- [BLOCKING] [security] **U1** (SCOPE_UNRESOLVED) The memorandum and the independent review may describe different coverage periods of the credit insurance. (S5, S8)

4 critical findings shown (target 5-8; all material items are always shown). 2 further open findings in section 6.

## 2. Framework completeness and portfolio

### Completeness

| strategy | K1 L1 legal counterparty | K2 L1->L2 legal claim | K3 L2->L3 method | K4 L2->L3 security | K5 Loss waterfall | K6 Holder look-through | K7 L3 business |
|---|---|---|---|---|---|---|---|
| T1 Acme equipment credit | CONFIRMED | SELF_REPORTED | SELF_REPORTED | UNRESOLVED | SELF_REPORTED | SELF_REPORTED | SELF_REPORTED |
| T2 Acme commodity trade finance | CONFIRMED | UNRESOLVED | SELF_REPORTED | SELF_REPORTED | UNRESOLVED | INFERRED | SELF_REPORTED |

### Portfolio components

| strategy | component | deployment | products | business type | counted totals |
|---|---|---|---|---|---|
| T1 Acme equipment credit | CORE_CREDIT | DEPLOYED\_VERIFIED [CONFIRMED] (S4) -- Transfers from E1 into the E5 pool observed on-chain. | P1 | private\_credit [SELF_REPORTED] (S8) | 25000000 USDC CURRENT\_BALANCE @2026-09-30 |
| T2 Acme commodity trade finance | CORE_CREDIT | DISCLOSED\_UNVERIFIED [SELF_REPORTED] (S7) -- The vault docs describe the trade finance path; no settlement is shown. | P2 | trade\_finance\_pt [INFERRED] (S7) -- Vault docs describe purchase and resale of goods. | -- |
| T3 Acme treasury sleeve | LIQUIDITY_SLEEVE | -- [UNRESOLVED] | P2 | -- [UNRESOLVED] | 5000000 USDC CURRENT\_BALANCE @2026-10-01 |

### Allocation

| strategy | interface | entry | kind | value | unit | basis | as_of | scope | counted | reason |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 | X2 | 0 | L1_L2 | 25000000 | USDC | CURRENT_BALANCE | 2026-09-30T12:00:00Z | USDC supplied by E1 to the E5 credit pool, read at the block | yes | counted |
| T1 | X2 | 1 | L1_L2 | 25150000 | USD | POSITION_VALUE | 2026-09-30 | E1 units in Acme Credit Fund LP | no | other measure of X2[0] |
| T1 | X2 | 2 | L1_L2 | 18000000 | USD | CUMULATIVE_FUNDED | 2026-06-30 | AUP loan sample: 12 loans funded 2026-01-01 to 2026-06-30 (S9); management figure, not tested | no | basis CUMULATIVE_FUNDED not counted |
| T1 | X13 | 0 | asset_sale | 3000000 | USD | SALE_PROCEEDS | 2026-08-15 | Proceeds of the X13 loan sale to E13 | no | not a funding edge |
| T3 | X9 | 0 | sleeve_holding | 5000000 | USDC | CURRENT_BALANCE | 2026-10-01 | Stablecoin held by E1 in the treasury sleeve | yes | counted |
| T3 | X10 | 0 | reserve_lookthrough | 5000000 | USD | RESERVE_LOOKTHROUGH | 2026-09-30 | Reserve assets of E11 backing the sleeve stablecoin | no | not a funding edge |

### Totals by strategy, component and product

| level | name | counted totals |
|---|---|---|
| strategy | T1 | 25000000 USDC CURRENT\_BALANCE @2026-09-30 |
| strategy | T3 | 5000000 USDC CURRENT\_BALANCE @2026-10-01 |
| component | CORE_CREDIT | 25000000 USDC CURRENT\_BALANCE @2026-09-30 |
| component | LIQUIDITY_SLEEVE | 5000000 USDC CURRENT\_BALANCE @2026-10-01 |
| product | P1 | 25000000 USDC CURRENT\_BALANCE @2026-09-30 |
| product | P2 | 5000000 USDC CURRENT\_BALANCE @2026-10-01 |

Totals add only amounts with the same basis, unit and observation date; see Appendix N for the checks.

## 3. Three-layer business model

### T1 Acme equipment credit

- Component: CORE_CREDIT
- Products: P1
- Business type: private\_credit [SELF_REPORTED] (S8)
- Sublayers: L2a credit fund; L2b warehouse SPV
- Chains:
  - P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[DL; secured\] -\> E7 Example Equipment Lessors Ltd (L3) -\> \[OTHER\] -\> E10 (L3-O)
  - P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[AP; ?\] -\> E8 Example Receivables Originator (L3)
  - P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[sale; true sale; loan INFERRED\] -\> E13 Example Loan Buyer Fund (transferee)

### T2 Acme commodity trade finance

- Component: CORE_CREDIT
- Products: P2
- Business type: trade\_finance\_pt [INFERRED] (S7) -- Vault docs describe purchase and resale of goods.
- Sublayers: --
- Chains:
  - P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured\] -\> E9 (L3)
  - P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[REPO; secured; alt A1a\] -\> E9 (L3)
  - P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured; alt A1b\] -\> E9 (L3)

### T3 Acme treasury sleeve

- Component: LIQUIDITY_SLEEVE
- Products: P2
- Business type: -- [UNRESOLVED]
- Sublayers: --
- Chains:
  - E1 Acme Yield Issuer Ltd (L1) -\> \[OTHER\] -\> E11 Example Stablecoin Issuer Ltd (issuer) -\> \[look-through\] -\> E12 (reserve)

### Functions by entity

| entity | class | layer | role | strategy | evidence |
|---|---|---|---|---|---|
| E1 | legal_person | L1 | token_issuer | -- | S3, S8 |
| E1 | legal_person | L1 | holder_counterparty | -- | S8 |
| E1 | legal_person | L2 | lender_of_record | T2 | S7 |
| E2 | legal_person | L2 | credit_manager | T1 | S2, S8 |
| E3 | legal_person | L2 | security_agent | T1 | S8 |
| E4 | legal_person | L1 | protocol_operator | -- | S1 |
| E5 | legal_person | L2 | lender_of_record | T1 | S8 |
| E6 | legal_person | L2 | asset_holding_spv | T1 | S8 |
| E7 | legal_person | L3 | financing_recipient | T1 | S8 |
| E8 | legal_person | L3 | receivables_seller | T1 | S5 |
| E9 | unknown | L3 | financing_recipient | T2 | S7 |
| E10 | obligor_group | L3-O | contractual_obligor | T1 | S8 |
| E11 | legal_person | -- | issuer | T3 | S7 |
| E12 | unknown | -- | reserve_assets | T3 | S7 |
| E13 | legal_person | -- | loan_purchaser | T1 | S8 |
| E14 | legal_person | -- | protection_provider | T1 | S8 |

## 4. Capital allocation and credit deployment

### L1 -> L2

| id | strategy | from -> to | route | legal class | counterparty | instrument | claim holder | amounts | supply concentration | alternative | terms | governing law |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X1 | T1 | P1 -\> E1 (holder\_L1) | -- [UNRESOLVED] | DI [SELF_REPORTED] (S8) | -- [UNRESOLVED] | Senior notes [SELF_REPORTED] (S8) | Noteholders [SELF_REPORTED] (S8) | -- | -- [UNRESOLVED] | -- | Monthly redemption window [SELF_REPORTED] (S8) | Examplestan [SELF_REPORTED] (S8) |
| X2 | T1 | E1 -\> E5 (L1\_L2) | FUND [SELF_REPORTED] (S8) | FI [SELF_REPORTED] (S8) | E5 [SELF_REPORTED] (S8) | Limited partnership interests [SELF_REPORTED] (S8) | E1 [SELF_REPORTED] (S8) | 25000000 USDC CURRENT_BALANCE @2026-09-30T12:00:00Z [CONFIRMED] (S4); 25150000 USD POSITION_VALUE @2026-09-30 [SELF_REPORTED] (S8); 18000000 USD CUMULATIVE_FUNDED @2026-06-30 [SELF_REPORTED] (S9; origin issuer_management; assurance NOT_TESTED) | 0.5 [CONFIRMED] (Pool shares held by E1 / Total pool share supply @2026-09-30T12:00:00Z, 20871234, ethereum) (S4) | -- | -- [UNRESOLVED] | Examplestan [SELF_REPORTED] (S8) |
| X6 | T2 | P2 -\> E1 (holder\_L1) | -- [UNRESOLVED] | OTHER [INFERRED] (S7) -- Vault share is a contractual claim. | -- [UNRESOLVED] | Vault shares [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- | -- [UNRESOLVED] | -- | No vault fee charged to P2 holders [CONFLICTING] (S1) | -- [UNRESOLVED] |

Amount scopes:

- X2[0]: USDC supplied by E1 to the E5 credit pool, read at the block
- X2[1]: E1 units in Acme Credit Fund LP
- X2[2]: AUP loan sample: 12 loans funded 2026-01-01 to 2026-06-30 (S9); management figure, not tested

### L2 -> L3

| id | strategy | from -> to | method | legal class | counterparty | security | collateral | perfection | enforcement | recourse | amounts | alternative | terms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X3 | T1 | E5 -\> E6 (within\_L2) | -- [UNRESOLVED] | DI [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- | -- | -- [UNRESOLVED] |
| X4 | T1 | E6 -\> E7 (L2\_L3) | DL [SELF_REPORTED] (S8) | DL [SELF_REPORTED] (S8) | -- [UNRESOLVED] | secured [SELF_REPORTED] (S8) | Leased equipment [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S8) -- No lien filing cited. | Security agent E3 enforces on default [SELF_REPORTED] (S8) | Full recourse to the lessor [SELF_REPORTED] (S8) | 10000000 USD FACILITY_COMMITMENT @2026-09-30 [SELF_REPORTED] (S8); 4000000 USD UNDRAWN_COMMITMENT @2026-09-30 [SELF_REPORTED] (S8) | -- | 36-month amortising, 12 percent [SELF_REPORTED] (S8) |
| X5 | T1 | E6 -\> E8 (L2\_L3) | AP [SELF_REPORTED] (S8) | AP [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] (S8) -- No collateral beyond the receivables described. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] (S5) -- Recourse to the seller not stated. | -- | -- | -- [UNRESOLVED] |
| X7 | T2 | E1 -\> E9 (L2\_L3) | PT [SELF_REPORTED] (S7) | OTHER [SELF_REPORTED] (S7) | -- [UNRESOLVED] | unsecured [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- | -- | -- [UNRESOLVED] (S7) -- Trade terms not published. |
| X8 | T1 | E7 -\> E10 (L3\_L3O) | -- [UNRESOLVED] | OTHER [SELF_REPORTED] (S8) -- Equipment leases between the lessor and its lessees. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- | -- | -- [UNRESOLVED] |
| X11 | T2 | E1 -\> E9 (L2\_L3) | REPO [SELF_REPORTED] (S7) | OTHER [SELF_REPORTED] (S7) | -- [UNRESOLVED] | secured [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | 2000000 USDC CURRENT_BALANCE @2026-09-30 [SELF_REPORTED] (S7) | A1a | Historical repo terms [SELF_REPORTED] (S7) |
| X12 | T2 | E1 -\> E9 (L2\_L3) | PT [SELF_REPORTED] (S7) | OTHER [SELF_REPORTED] (S7) | -- [UNRESOLVED] | unsecured [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- | A1b | Current live-rate terms [SELF_REPORTED] (S7) |

Amount scopes:

- X4[0]: Equipment loan facility from E6 to E7
- X4[1]: Undrawn part of the E6 to E7 equipment loan facility
- X11[0]: Principal under repo option A1a

### Liquidity sleeves

| id | strategy | from -> to | legal class | instrument | amounts | terms |
|---|---|---|---|---|---|---|
| X9 | T3 | E1 -\> E11 (sleeve\_holding) | OTHER [SELF_REPORTED] (S7) | Stablecoin balances [SELF_REPORTED] (S7) | 5000000 USDC CURRENT_BALANCE @2026-10-01 [SELF_REPORTED] (S7) | -- [UNRESOLVED] |
| X10 | T3 | E11 -\> E12 (reserve\_lookthrough) | -- [UNRESOLVED] | Short-dated government bills [SELF_REPORTED] (S7) | 5000000 USD RESERVE_LOOKTHROUGH @2026-09-30 [SELF_REPORTED] (S7) | -- [UNRESOLVED] |

Amount scopes:

- X9[0]: Stablecoin held by E1 in the treasury sleeve
- X10[0]: Reserve assets of E11 backing the sleeve stablecoin

### Asset sales

| id | strategy | from -> to | loan identity | seller of record | buyer of record | legal transfer (title_transfer) | repayment source | servicer after exit (servicing) | recourse | retained exposure (residual_exposure) | amounts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X13 | T1 | E6 -\> E13 (asset\_sale) | Equipment loan pool EQ-2026-A [INFERRED] (S8) -- Inferred from the sale schedule reference in the memorandum. | E6 Acme Warehouse SPV Ltd [SELF_REPORTED] (S8) | E13 Example Loan Buyer Fund [SELF_REPORTED] (S8) | true sale [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S5) -- The independent review does not say who repays the buyer. | Retained by E2 [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] (S8) -- Not disclosed in the memorandum. | 3000000 USD SALE_PROCEEDS @2026-08-15 [SELF_REPORTED] (S8) |

Amount scopes:

- X13[0]: Proceeds of the X13 loan sale to E13

## 5. Holder rights, default and recovery

### Holder rights: P1 Acme Senior Note

- Instrument nature: Senior notes issued by E1 [SELF_REPORTED] (S8)
- Claim against: E1 [SELF_REPORTED] (S8)
- Look-through: via\_spv [SELF_REPORTED] (S8) -- Notes are limited to the issuer SPV's assets.
- Recourse: Limited recourse [SELF_REPORTED] (S8)
- Governing law: Examplestan [SELF_REPORTED] (S8)
- Forum: -- [UNRESOLVED] (S8) -- No forum clause quoted.
- Insolvency protection: -- [UNRESOLVED] (S8) -- Not described.
- Disclaimers: Noteholders have no direct claim on borrowers [SELF_REPORTED] (S8)

### Holder rights: P2 Acme Treasury Vault

- Instrument nature: Vault shares [SELF_REPORTED] (S7)
- Claim against: -- [UNRESOLVED] (S7) -- Not stated.
- Look-through: unresolved [INFERRED] (S7) -- Docs describe no claim beyond the vault.
- Recourse: -- [UNRESOLVED]
- Governing law: -- [UNRESOLVED]
- Forum: -- [UNRESOLVED]
- Insolvency protection: -- [UNRESOLVED]
- Disclaimers: -- [UNRESOLVED]

### Default and recovery: T1 Acme equipment credit

- Events of default: Payment default continuing for 30 days [SELF_REPORTED] (S8)
- Enforcement: Security agent E3 enforces over the leased equipment [SELF_REPORTED] (S8)
- Loss waterfall (1 absorbs first): [SELF_REPORTED] (S8)
  1. Borrower equity
  2. Credit fund junior tranche
  3. Senior noteholders
- Recovery history: -- [UNRESOLVED] (S8) -- No recoveries reported.

### Default and recovery: T2 Acme commodity trade finance

- Events of default: -- [UNRESOLVED] (S7) -- Vault docs describe no default events.
- Enforcement: -- [UNRESOLVED]
- Loss waterfall (1 absorbs first): -- [UNRESOLVED] (S7) -- Vault docs do not describe loss order.
- Recovery history: -- [UNRESOLVED]

### Supports

| id | type | strategies | provider | beneficiary | covered exposure | trigger | coverage | exclusions | priority | enforceability | governing law | holder recourse |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Z1 | CREDIT_ENHANCEMENT | T1 | E14 | E5 | Equipment loan principal [SELF_REPORTED] (S8) | Payment default continuing for 90 days [SELF_REPORTED] (S8) | Up to 20 percent of principal [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S8) -- Not disclosed in the memorandum. | -- [UNRESOLVED] | -- [UNRESOLVED] | Examplestan [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S8) -- Noteholders are not named as insured. |

## 6. Material gaps and issuer requests

### Material

- none

### Blocking

- none

### Conflicts

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7)
  - scope: Both state the vault fee charged to P2 holders; S7 is the March 2026 version.
  - scope match: matched
  - assertion S7 (2026-03-15): Vault fee: 0.30 percent of assets per year.
  - assertion S1 (2026-10-01): No fees are charged to vault holders.
  - subjects: X6.terms
  - resolution: open

### Scope unresolved

- none

### Unreconciled transactions

- none

### Other gaps

- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)
  - scope match: not_applicable
  - resolution: open

### Issuer requests

- **Q1** (priority 1) Security agreement and lien filings for the equipment loans -- Confirm whether the T1 loans are secured and the security interest is perfected (answers C2, C5)
- **Q2** (priority 2) Commodity purchase and offtake contracts for the trade vault -- Identify the T2 counterparties and how the L3 business generates cash (answers A4, E1, E2)

## Appendix A. Legal entity register

| entity | class | legal name | jurisdiction | type | registration | licence status |
|---|---|---|---|---|---|---|
| E1 | legal_person | Acme Yield Issuer Ltd [CONFIRMED] (S3) | Examplestan [CONFIRMED] (S3) | private limited company [CONFIRMED] (S3) | 100200 [CONFIRMED] (S3) | -- [UNRESOLVED] (S2) -- No licence entry found for the issuer. |
| E2 | legal_person | Acme Asset Management LLC [CONFIRMED] (S2) | Examplestan [INFERRED] (S2) -- Regulator only licenses local entities. | limited liability company [SELF_REPORTED] (S8) | -- [UNRESOLVED] | active [CONFIRMED] (S2) |
| E3 | legal_person | Example Custody Trust Co [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S8) -- Memorandum names the custodian but not its jurisdiction. | trust company [INFERRED] (S5) -- Name suggests a trust company. | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E4 | legal_person | Acme Labs Inc [SELF_REPORTED] (S1) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E5 | legal_person | Acme Credit Fund LP [SELF_REPORTED] (S8) | Examplestan [SELF_REPORTED] (S8) | limited partnership [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E6 | legal_person | Acme Warehouse SPV Ltd [SELF_REPORTED] (S8) | -- [UNRESOLVED] | private limited company [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E7 | legal_person | Example Equipment Lessors Ltd [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E8 | legal_person | Example Receivables Originator [INFERRED] (S5) -- Named as receivables seller in the review. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E9 | unknown | -- [UNRESOLVED] (S7) -- Vault docs do not name the commodity buyer. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E10 | obligor_group | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E11 | legal_person | Example Stablecoin Issuer Ltd [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E12 | unknown | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E13 | legal_person | Example Loan Buyer Fund [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E14 | legal_person | Example Credit Insurer plc [SELF_REPORTED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |

Licences:

| entity | regulator | licence type | licence id | licence status |
|---|---|---|---|---|
| E2 | Examplestan Financial Authority [CONFIRMED] (S2) | fund manager [CONFIRMED] (S2) | AAM-0042 [CONFIRMED] (S2) | active [CONFIRMED] (S2) |

## Appendix B. L3 business

### T1 Acme equipment credit

- Description: Equipment leasing to mid-size manufacturers [SELF_REPORTED] (S8)
- Revenue model: Monthly lease payments from lessees [SELF_REPORTED] (S8)
- Cash generation: Lease collections paid to the warehouse SPV [SELF_REPORTED] (S8)
- Collections control: Collection account controlled by the security agent [INFERRED] (S5) -- Review mentions a third-party custodian over the receivables.
- Concentration: Top ten lessees about 40 percent of the book [THIRD_PARTY_REPORTED] (S5)
- Performance: No payment default in the 12 sampled loans to 2026-06-30 [CONFIRMED] (S9; origin auditor_procedure; assurance TESTED) -- AUP sample only, not the portfolio.
- Operating history: Leasing since 2019 [SELF_REPORTED] (S1)

### T2 Acme commodity trade finance

- Description: Purchase and resale of agricultural commodities [SELF_REPORTED] (S7)
- Revenue model: -- [UNRESOLVED] (S7) -- Margin on resale not described.
- Cash generation: -- [UNRESOLVED]
- Collections control: -- [UNRESOLVED]
- Concentration: -- [UNRESOLVED]
- Performance: -- [UNRESOLVED]
- Operating history: -- [UNRESOLVED]

## Appendix C. Fund flows

Nodes:

| id | label | lane | layer | kind | chain | ref |
|---|---|---|---|---|---|---|
| n1 | Investor wallet | onchain | -- | investor | ethereum | -- |
| n2 | aSN token | onchain | L1 | contract | ethereum | 0x1111111111111111111111111111111111111111 |
| n3 | Treasury vault | onchain | L1 | pool | ethereum | P2 |
| n4 | Ops multisig | onchain | -- | multisig | ethereum | 0x2222222222222222222222222222222222222222 |
| n5 | Off-ramp desk | boundary | -- | entity | -- | E4 |
| n6 | Issuer bank account | offchain | L1 | bank_account | -- | E1 |
| n7 | Custodian | offchain | L2 | entity | -- | E3 |
| n8 | Receivables portfolio | offchain | L3 | asset | -- | -- |
| n9 | Manager | offchain | L2 | entity | -- | E2 |
| n10 | Credit fund | offchain | L2 | entity | -- | E5 |
| n11 | Warehouse SPV | offchain | L2 | entity | -- | E6 |
| n12 | Equipment lessor | offchain | L3 | entity | -- | E7 |
| n13 | Commodity buyer | offchain | L3 | entity | -- | E9 |

### T1 Acme equipment credit -- settlement

![Fund flow T1 settlement](acme.flow-T1-settlement.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n1 Investor wallet | n2 aSN token | subscription | deposit | stablecoin | X1 | USDC in, aSN minted | true [CONFIRMED] (S4) |
| n5 Off-ramp desk | n6 Issuer bank account | conversion | conversion | fiat_wire | -- | stablecoin to fiat | true [SELF_REPORTED] (S1) |
| n6 Issuer bank account | n10 Credit fund | subscription | purchase | fiat_wire | X2 | fund subscription | true [SELF_REPORTED] (S8) |
| n10 Credit fund | n11 Warehouse SPV | subscription | drawdown | fiat_wire | X3 | warehouse notes | true [SELF_REPORTED] (S8) |
| n11 Warehouse SPV | n12 Equipment lessor | subscription | drawdown | fiat_wire | X4 | equipment loans | true [SELF_REPORTED] (S8) |
| n11 Warehouse SPV | n8 Receivables portfolio | subscription | purchase | fiat_wire | X5 | receivables purchase | true [SELF_REPORTED] (S8) |

### T1 Acme equipment credit -- claim

![Fund flow T1 claim](acme.flow-T1-claim.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n12 Equipment lessor | n7 Custodian | collateral | pledge | internal | X4 | equipment pledged | true [SELF_REPORTED] (S8) |
| n8 Receivables portfolio | n7 Custodian | custody | title_transfer | internal | X5 | receivables held | true [INFERRED] (S5) -- Review mentions a custodian. |

### T1 Acme equipment credit -- repayment

![Fund flow T1 repayment](acme.flow-T1-repayment.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n12 Equipment lessor | n11 Warehouse SPV | yield | repayment | fiat_wire | X4 | lease collections | true [SELF_REPORTED] (S8) |
| n11 Warehouse SPV | n10 Credit fund | yield | repayment | fiat_wire | X3 | note repayments | -- [UNRESOLVED] (S8) -- Memorandum does not describe this hop. |
| n10 Credit fund | n6 Issuer bank account | yield | distribution | fiat_wire | X2 | fund distributions | true [SELF_REPORTED] (S8) |
| n6 Issuer bank account | n9 Manager | fee | fee_payment | fiat_wire | -- | management fee | true [SELF_REPORTED] (S8) |
| n2 aSN token | n1 Investor wallet | redemption | burn | burn | X1 | aSN burned on redemption | true [CONFIRMED] (S4) |

### T2 Acme commodity trade finance -- settlement

![Fund flow T2 settlement](acme.flow-T2-settlement.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n5 Off-ramp desk | n6 Issuer bank account | conversion | conversion | fiat_wire | -- | stablecoin to fiat | true [SELF_REPORTED] (S1) |
| n1 Investor wallet | n3 Treasury vault | subscription | deposit | stablecoin | X6 | vault deposit | true [SELF_REPORTED] (S7) |
| n3 Treasury vault | n4 Ops multisig | collateral | pledge | internal | -- | reserve pledge | -- [UNRESOLVED] (S4) -- No pledge transfer observed on-chain. |
| n6 Issuer bank account | n13 Commodity buyer | subscription | purchase | fiat_wire | X7 | goods purchased | -- [UNRESOLVED] |
| n3 Treasury vault | n1 Investor wallet | yield | distribution | stablecoin | X6 | daily yield | true [SELF_REPORTED] (S7) |

### T2 Acme commodity trade finance -- claim

- none

### T2 Acme commodity trade finance -- repayment

- none

### T3 Acme treasury sleeve -- settlement

- none

### T3 Acme treasury sleeve -- claim

- none

### T3 Acme treasury sleeve -- repayment

- none

## Appendix D. Yield, fees and redemption

### Yield P1 Acme Senior Note

- Mechanism: Interest on receivables purchased at a discount [SELF_REPORTED] (S8)
- Gross yield: 11.0 percent [SELF_REPORTED] (S1)
- Net yield to holder: 9.5 percent [SELF_REPORTED] (S1)
- Distribution method: rebasing [CONFIRMED] (S4)
- Distribution frequency: monthly [SELF_REPORTED] (S8)

Underlying:

| description | asset class | share pct | location |
|---|---|---|---|
| Short-dated trade receivables [SELF_REPORTED] (S8) | trade receivables [SELF_REPORTED] (S8) | 100 [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S8) -- Receivables jurisdiction not stated. |

Fees:

| type | rate | recipient |
|---|---|---|
| management [SELF_REPORTED] (S8) | 1.5 percent p.a. [SELF_REPORTED] (S8) | E2 [SELF_REPORTED] (S8) |

### Yield P2 Acme Treasury Vault

- Mechanism: Resale margin passed through the vault [SELF_REPORTED] (S7)
- Gross yield: -- [UNRESOLVED]
- Net yield to holder: 4.1 percent [SELF_REPORTED] (S1)
- Distribution method: claim [SELF_REPORTED] (S7)
- Distribution frequency: daily [SELF_REPORTED] (S7)

Underlying:

| description | asset class | share pct | location |
|---|---|---|---|
| Commodity purchase and resale contracts [SELF_REPORTED] (S7) | trade finance [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] |

Fees:

| type | rate | recipient |
|---|---|---|
| vault [SELF_REPORTED] (S7) | 0.30 percent [SELF_REPORTED] (S7) | -- [UNRESOLVED] |

### Redemption

| product | mechanism | queue | settlement time | gating | fees |
|---|---|---|---|---|---|
| P1 | redemption request to issuer [SELF_REPORTED] (S8) | monthly window [SELF_REPORTED] (S8) | 2 business days [INFERRED] (S6) -- Stated on an analyst call only. | issuer may suspend redemptions [SELF_REPORTED] (S8) | -- [UNRESOLVED] (S8) -- No redemption fee stated. |
| P2 | instant burn against vault liquidity [SELF_REPORTED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |

### Eligibility

| product | restrictions |
|---|---|
| P1 | professional investors only [SELF_REPORTED] (S8) |
| P2 | -- [UNRESOLVED] (S1) -- Site does not state restrictions. |

## Appendix E. On-chain contracts and control

| chain | address | role | source verified | proxy | upgrade admin | role admins | timelock delay s | multisig | threshold | signers |
|---|---|---|---|---|---|---|---|---|---|---|
| ethereum | 0x1111111111111111111111111111111111111111 | aSN token [CONFIRMED] (S4) | true [CONFIRMED] (S4) | TransparentUpgradeableProxy [CONFIRMED] (S4) | 0x2222222222222222222222222222222222222222 [CONFIRMED] (S4) | 0x2222222222222222222222222222222222222222 [CONFIRMED] (S4) | 0 [CONFIRMED] (S4) -- No timelock between admin and proxy. | 0x2222222222222222222222222222222222222222 [CONFIRMED] (S4) | 2 [CONFIRMED] (S4) | 3 [CONFIRMED] (S4) |

## Appendix F. All findings

### Finding register

| id | type | scope match | resolution | k_checks | impact | priority | carried from |
|---|---|---|---|---|---|---|---|
| C1 | structural_change | not_applicable | not_applicable | -- | -- | 3 | C1 |
| D1 | discrepancy | matched | open | -- | -- | 2 | D1 |
| D2 | discrepancy | matched | resolved | -- | -- | 2 | D2 |
| G1 | gap | not_applicable | open | K1 | capital_control, ownership | 1 | G1 |
| G2 | gap | not_applicable | open | -- | -- | 3 | G2 |
| G3 | gap | not_applicable | open | K4 | security | 1 | -- |
| R1 | unreconciled_transaction | matched | open | -- | ownership | 1 | G3 |
| U1 | scope_unresolved | not_matched | open | -- | security | 2 | U1 |

### Gaps

- **G1** [legal] [MATERIAL] [BLOCKING] Issuer financial statements and the custody agreement are not public. (S8)
  - **N1** Custody agreement and issuer accounts -- Company registry filings -- Confirm custody and financials (resolves G1; est 6 calls)
- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)
- **G3** [credit] [BLOCKING] The security agreement over the leased equipment is not public. (S8)
  - **N3** Lien filings over the leased equipment -- Examplestan collateral registry -- Resolve the secured/unsecured discrepancy (resolves G3, D2; est 3 calls)

### Discrepancies

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7) -- subjects: X6.terms -- scope: Both state the vault fee charged to P2 holders; S7 is the March 2026 version.
- **D2** [credit] The memorandum describes the equipment loans as secured; the independent review describes them as unsecured. (S5, S8) -- subjects: X4.security -- scope: Both describe the security of the X4 equipment loans as currently documented.

### Scope unresolved

- **U1** [credit] The memorandum and the independent review may describe different coverage periods of the credit insurance. (S5, S8) -- subjects: Z1.coverage -- scope: The memorandum covers the 2026 policy year; the review may describe the 2025 policy.

### Unreconciled transactions

- **R1** [credit] The memorandum reports the X13 loans as sold to E13; the independent review still lists them on the E6 balance sheet. (S5, S8) -- subjects: X13 -- scope: Both accounts concern the X13 sale of the equipment loan pool in August 2026.

### Structural changes

- **C1** [onchain] Upgrade admin changed from a single key to a 2-of-3 multisig. (S4)

### Open questions

- [legal] Which entity holds legal title to the receivables?
- [redemption] Can the issuer suspend redemptions without notice?

## Appendix G. History

| date | change | evidence |
|---|---|---|
| 2026-03-01 | Vault fee stated as 0.30 percent in archived docs. | S7 |
| 2026-09-15 | Upgrade admin moved to a 2-of-3 multisig. | S4 |

## Appendix H. Audits and size

### Audits

| auditor | scope | date | report |
|---|---|---|---|
| Example Audit Partners [SELF_REPORTED] (S1) | aSN token contract [SELF_REPORTED] (S1) | 2026-02-15 [SELF_REPORTED] (S1) | -- |

### Size

| product | metric | value | as of |
|---|---|---|---|
| P1 | supply | 12500000 [CONFIRMED] (S4) | 2026-10-01 |
| P2 | tvl | 3400000 [SELF_REPORTED] (S1) | 2026-10-01 |
| -- | originated | 48000000 [SELF_REPORTED] (S1) | -- |

## Appendix I. Sources

| id | type | origin | fetch | retrieved | title/url | note |
|---|---|---|---|---|---|---|
| S1 | project_site | first_party | ok | 2026-10-01T08:00:00Z | Acme Yield - Home -- https://acme-yield.example/ |  |
| S2 | regulator_registry | regulator | ok | 2026-10-01T08:05:00Z | Register entry: Acme Asset Management LLC -- https://regulator.example/register/AAM-0042 |  |
| S3 | company_registry | registry | ok | 2026-10-01T08:10:00Z | Company record: Acme Yield Issuer Ltd -- https://companies.example/entity/ACME-SPV-1 |  |
| S4 | onchain_explorer | onchain | ok | 2026-10-01T08:15:00Z | Explorer: aSN token contract -- https://explorer.example/address/0x00000000000000000000000000000000000000a1 |  |
| S5 | third_party_research | third_party | ok | 2026-10-01T08:20:00Z | Independent review of Acme Yield -- https://research.example/acme-yield-review |  |
| S6 | analyst_input | analyst | offline | -- | Analyst call with Acme team -- analyst-call-notes-r1 | Notes from a call; not independently checked. |
| S7 | project_docs | first_party | archived (version 2026-03-01) | 2026-10-01T08:30:00Z | Acme Treasury Vault docs (archived) -- https://web.archive.example/2026-03-01/https://docs.acme-yield.example/vault |  |
| S8 | legal_doc | first_party | pdf | 2026-10-01T08:40:00Z | Offering memorandum (Acme Senior Note) -- https://acme-yield.example/legal/offering-memorandum.pdf |  |
| S9 | audit_report | auditor | pdf | 2026-10-01T09:00:00Z | Agreed-upon procedures report on the Acme Credit Fund loan sample -- https://auditor.example/acme-credit-fund-aup-2026.pdf |  |

## Appendix J. Analyst interventions

- none

## Appendix K. Unmapped facts

- The team plans a second chain deployment in 2027. (S1) -- why unmapped: Forward-looking statement; no schema field.

## Appendix L. Legend

- Claim cell: `value [FLAG] (evidence) -- note`; `--` means no value.
- CONFIRMED: direct, sufficient evidence for the precise claim within its stated scope (legal facts: regulator, registry, auditor or on-chain sources only).
- SELF_REPORTED: stated by the issuer, protocol, borrower or another interested party.
- THIRD_PARTY_REPORTED: reported by a third party; its scope and authority still need assessing.
- INFERRED: the analyst's conclusion from cited facts; the note states the reasoning.
- UNRESOLVED: not found in the cited sources, or not searched when no source is cited.
- CONFLICTING: named by an open discrepancy finding whose scope was matched (same fact, timeframe and scope, with two recorded assertions; see Appendix F); scope-unresolved findings, unreconciled transactions and resolved discrepancies never make a claim CONFLICTING.
- Conflict statuses of findings: CONFLICTING (open matched discrepancy), RESOLVED (resolved discrepancy), SCOPE_UNRESOLVED (statements may cover different scopes), UNRECONCILED_TRANSACTION (accounts of one transaction not reconciled).
- Provenance (curator Q8): origin is who asserted the fact (issuer_management, issuer_documents, borrower, regulator, registry, onchain, independent_party, auditor_procedure, analyst); the cited sources are where it was published; assurance is what an auditor or reviewer tested for this precise claim (TESTED, NOT_TESTED, NOT_APPLICABLE). An issuer statement quoted in an auditor's publication stays SELF_REPORTED with assurance NOT_TESTED; a claim is CONFIRMED through an auditor only with origin auditor_procedure and assurance TESTED; a regulator, registry or on-chain verification keeps its origin, and assurance states whether a cited auditor also tested it.
- Layers are functions inside one strategy, by position in its financing chain: L1 on-chain capital vault; L2 credit financing layer; L3 underlying business layer.
- L3-O: optional sub-layer of parties downstream of L3 whose payments repay it; roles contractual_obligor (a document shows they legally owe L3), cash_flow_source (business cash flows) and offtaker_customer (buyers of goods, services or compute); linked by L3_L3O interfaces.
- Route (L1->L2): POOL supply to a shared lending pool; FUND subscription to a fund or vehicle; DIRECT financing of the credit counterparty itself; WRAPPER a position in another vault or token that holds the exposure.
- Method (L2->L3): DL direct loan; DI debt instrument (note, bond); AP purchase of receivables or other assets; PI participation interest; REPO repurchase agreement; PT principal purchase and resale (trade finance); OTHER other method.
- Legal class: DL loan claim; DI debt instrument claim; AP ownership of purchased assets; PI participation interest; FI fund interest; EI equity interest; PROTOCOL_ENTITLEMENT a pool receipt or other protocol-enforced entitlement; OTHER other or contractual claim.
- Components: CORE_CREDIT an underlying real-world financing business; LIQUIDITY_SLEEVE undeployed cash or stablecoin (issuer and reserves, no L3); DEFI_LENDING lending-market supply with protocol-enforced entitlements.
- Amount cell: `<value> <unit> <BASIS> @<observation time> [FLAG] (sources)`; the observation time is when the value was observed in the source, never the report date. Bases:
  - CURRENT_BALANCE: token or asset holdings at the observation time.
  - POSITION_VALUE: value of a position under a stated valuation basis.
  - OUTSTANDING_PRINCIPAL: loan principal unpaid at the observation time (recorded unbilled principal goes here with the scope saying so).
  - CUMULATIVE_FUNDED: actual disbursements over a stated period.
  - FACILITY_COMMITMENT: contractual ceiling.
  - UNDRAWN_COMMITMENT: unused part of a facility commitment.
  - SALE_PROCEEDS: proceeds actually received from a disposal.
  - RESERVE_LOOKTHROUGH: an issuer's reserve or collateral assets, never additive.
  - OTHER: only with a scope of at least 20 characters defining it.
- Counting rule: only CURRENT_BALANCE, POSITION_VALUE and OUTSTANDING_PRINCIPAL amounts on L1_L2 and sleeve_holding interfaces, with an observation time, outside alternative groups and not migration placeholders, are counted; totals add only amounts with the same basis, unit, valuation basis and observation date (label `<sum> <unit> <BASIS> @<date>`); everything else is linked, not summed.
- Deployment of a credit strategy: DEPLOYED_VERIFIED (transfers into the credit arrangement verified), DISCLOSED_UNVERIFIED (path disclosed, settlement not shown), NOT_DEPLOYED, UNRESOLVED.
- Alternative tag: `alt A1a` marks option a of alternative group A1, competing legal paths for one position; they are never parallel exposures and are not counted.
- Flow views: settlement (capital and asset movement); claim (legal rights and collateral); repayment (cash back to L2 and L1, fees, enforcement path).
- Lanes: offchain, boundary (conversion, bridge and custody hand-off points), onchain.
- Diagram suffixes: [C] CONFIRMED, [S] SELF_REPORTED, [T] THIRD_PARTY_REPORTED, [I] INFERRED, [U] UNRESOLVED ([U?] not searched), [X] CONFLICTING.
- Findings: G gap, D discrepancy, U scope unresolved, R unreconciled transaction, C structural change; issuer requests Q cite the research question codes they answer. No risk scores are given.

## Appendix N. Quantitative and provenance checks

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
| QA12 | onemeasure | pass | ok |

Rules:

- QA1 basis: No total mixes amount bases, units, valuation bases or observation dates (each total recomputed from the allocation rows has one total key and the same sum).
- QA2 lookthrough: No RESERVE_LOOKTHROUGH amount and no reserve_lookthrough interface is counted.
- QA3 alternative: No amount on an interface with an alternative group is counted.
- QA4 proceeds: No SALE_PROCEEDS amount is counted; SALE_PROCEEDS amounts whose value status is not verified are listed as unverified (informational).
- QA5 asof: No amount with as_of null is counted.
- QA6 stockflow: No CUMULATIVE_FUNDED, FACILITY_COMMITMENT or UNDRAWN_COMMITMENT amount is counted or labelled outstanding in totals.
- QA7 provenance: No claim citing an auditor source (outside audits[]) has origin null; no claim with an issuer origin has status other than self_reported or not_found; every origin, assurance and status combination follows the curator Q8 rules.
- QA8 conflicts: Every claim flagged CONFLICTING is a subject of an open discrepancy with scope_match matched and at least two assertions; no scope_unresolved or unreconciled_transaction subject is flagged CONFLICTING.
- QA9 placeholder: No finding scope note and no amount scope is a migration placeholder.
- QA10 section1: Every material finding and every blocking finding with k_checks is in section 1.
- QA11 deployment: No CORE_CREDIT or DEFI_LENDING strategy has deployment DEPLOYED_VERIFIED without status verified.
- QA12 onemeasure: No interface has more than one counted amount (entry 0 or the first countable entry is the position measure; later entries are other measures of the same position).

## Appendix O. Changes

No earlier run.
