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
| skill version | 0.5.0 |
| schema version | rwa-dd/2.0 |

> DRAFT -- not finalized

## 1. Executive summary

Acme Yield offers two products: a note (P1) financing equipment leases through a credit fund and a warehouse SPV (T1), and a vault (P2) financing commodity purchase and resale (T2). Entities are mapped to layers; the security over the T1 loans is disputed between sources.

## 2. Framework completeness

| strategy | K1 L1 legal counterparty | K2 L1->L2 legal claim | K3 L2->L3 method | K4 L2->L3 security | K5 Loss waterfall | K6 Holder look-through | K7 L3 business |
|---|---|---|---|---|---|---|---|
| T1 Acme equipment credit | CONFIRMED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | CONFLICTING | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED |
| T2 Acme commodity trade finance | CONFIRMED | UNRESOLVED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED | UNRESOLVED | PARTIALLY_VERIFIED | PARTIALLY_VERIFIED |

## 3. Three-layer functional map

### T1 Acme equipment credit

- Products: P1
- Business type: private\_credit [PARTIALLY_VERIFIED] (S8)
- Sublayers: L2a credit fund; L2b warehouse SPV
- Chains:
  - P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[DL; secured\] -\> E7 Example Equipment Lessors Ltd (L3) -\> \[OTHER\] -\> E10 (L3-O)
  - P1 holders -\> \[DI\] -\> E1 Acme Yield Issuer Ltd (L1) -\> \[FUND; FI\] -\> E5 Acme Credit Fund LP (L2) -\> \[DI\] -\> E6 Acme Warehouse SPV Ltd (L2) -\> \[AP; ?\] -\> E8 Example Receivables Originator (L3)

### T2 Acme commodity trade finance

- Products: P2
- Business type: trade\_finance\_pt [PARTIALLY_VERIFIED] (S7) -- Vault docs describe purchase and resale of goods.
- Sublayers: --
- Chains:
  - P2 holders -\> \[OTHER\] -\> E1 Acme Yield Issuer Ltd (L1/L2) -\> \[PT; unsecured\] -\> E9 (L3)

### Functions by entity

| entity | layer | role | strategy | evidence |
|---|---|---|---|---|
| E1 | L1 | token_issuer | -- | S3, S8 |
| E1 | L1 | holder_counterparty | -- | S8 |
| E1 | L2 | lender_of_record | T2 | S7 |
| E2 | L2 | credit_manager | T1 | S2, S8 |
| E3 | L2 | security_agent | T1 | S8 |
| E4 | L1 | protocol_operator | -- | S1 |
| E5 | L2 | lender_of_record | T1 | S8 |
| E6 | L2 | asset_holding_spv | T1 | S8 |
| E7 | L3 | financing_recipient | T1 | S8 |
| E7 | L3 | ultimate_obligor | T1 | S8 |
| E8 | L3 | receivables_seller | T1 | S5 |
| E9 | L3 | ultimate_obligor | T2 | S7 |
| E10 | L3 | ultimate_obligor | T1 | S8 |

## 4. Legal entity register

| entity | legal name | jurisdiction | type | registration | licence status |
|---|---|---|---|---|---|
| E1 | Acme Yield Issuer Ltd [CONFIRMED] (S3) | Examplestan [CONFIRMED] (S3) | private limited company [CONFIRMED] (S3) | 100200 [CONFIRMED] (S3) | -- [UNRESOLVED] (S2) -- No licence entry found for the issuer. |
| E2 | Acme Asset Management LLC [CONFIRMED] (S2) | Examplestan [PARTIALLY_VERIFIED] (S2) -- Regulator only licenses local entities. | limited liability company [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | active [CONFIRMED] (S2) |
| E3 | Example Custody Trust Co [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] (S8) -- Memorandum names the custodian but not its jurisdiction. | trust company [PARTIALLY_VERIFIED] (S5) -- Name suggests a trust company. | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E4 | Acme Labs Inc [PARTIALLY_VERIFIED] (S1) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E5 | Acme Credit Fund LP [PARTIALLY_VERIFIED] (S8) | Examplestan [PARTIALLY_VERIFIED] (S8) | limited partnership [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E6 | Acme Warehouse SPV Ltd [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | private limited company [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E7 | Example Equipment Lessors Ltd [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E8 | Example Receivables Originator [PARTIALLY_VERIFIED] (S5) -- Named as receivables seller in the review. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E9 | -- [UNRESOLVED] (S7) -- Vault docs do not name the commodity buyer. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| E10 | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |

Licences:

| entity | regulator | licence type | licence id | licence status |
|---|---|---|---|---|
| E2 | Examplestan Financial Authority [CONFIRMED] (S2) | fund manager [CONFIRMED] (S2) | AAM-0042 [CONFIRMED] (S2) | active [CONFIRMED] (S2) |

## 5. L1 -> L2 capital allocation

| id | strategy | from -> to | route | legal class | counterparty | instrument | claim holder | terms | governing law |
|---|---|---|---|---|---|---|---|---|---|
| X1 | T1 | P1 -\> E1 (holder\_L1) | -- [UNRESOLVED] | DI [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | Senior notes [PARTIALLY_VERIFIED] (S8) | Noteholders [PARTIALLY_VERIFIED] (S8) | Monthly redemption window [PARTIALLY_VERIFIED] (S8) | Examplestan [PARTIALLY_VERIFIED] (S8) |
| X2 | T1 | E1 -\> E5 (L1\_L2) | FUND [PARTIALLY_VERIFIED] (S8) | FI [PARTIALLY_VERIFIED] (S8) | E5 [PARTIALLY_VERIFIED] (S8) | Limited partnership interests [PARTIALLY_VERIFIED] (S8) | E1 [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | Examplestan [PARTIALLY_VERIFIED] (S8) |
| X6 | T2 | P2 -\> E1 (holder\_L1) | -- [UNRESOLVED] | OTHER [PARTIALLY_VERIFIED] (S7) -- Vault share is a contractual claim. | -- [UNRESOLVED] | Vault shares [PARTIALLY_VERIFIED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |

## 6. L2 -> L3 underlying transactions

| id | strategy | from -> to | method | legal class | counterparty | security | collateral | perfection | enforcement | recourse | terms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| X3 | T1 | E5 -\> E6 (within\_L2) | -- [UNRESOLVED] | DI [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |
| X4 | T1 | E6 -\> E7 (L2\_L3) | DL [PARTIALLY_VERIFIED] (S8) | DL [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | secured [CONFLICTING] (S8) | Leased equipment [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] (S8) -- No lien filing cited. | Security agent E3 enforces on default [PARTIALLY_VERIFIED] (S8) | Full recourse to the lessor [PARTIALLY_VERIFIED] (S8) | 36-month amortising, 12 percent [PARTIALLY_VERIFIED] (S8) |
| X5 | T1 | E6 -\> E8 (L2\_L3) | AP [PARTIALLY_VERIFIED] (S8) | AP [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] (S8) -- No collateral beyond the receivables described. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] (S5) -- Recourse to the seller not stated. | -- [UNRESOLVED] |
| X7 | T2 | E1 -\> E9 (L2\_L3) | PT [PARTIALLY_VERIFIED] (S7) | OTHER [PARTIALLY_VERIFIED] (S7) | -- [UNRESOLVED] | unsecured [PARTIALLY_VERIFIED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] (S7) -- Trade terms not published. |
| X8 | T1 | E7 -\> E10 (within\_L3) | -- [UNRESOLVED] | OTHER [PARTIALLY_VERIFIED] (S8) -- Equipment leases between the lessor and its lessees. | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |

## 7. Holder legal rights

### P1 Acme Senior Note

- Instrument nature: Senior notes issued by E1 [PARTIALLY_VERIFIED] (S8)
- Claim against: E1 [PARTIALLY_VERIFIED] (S8)
- Look-through: via\_spv [PARTIALLY_VERIFIED] (S8) -- Notes are limited to the issuer SPV's assets.
- Recourse: Limited recourse [PARTIALLY_VERIFIED] (S8)
- Governing law: Examplestan [PARTIALLY_VERIFIED] (S8)
- Forum: -- [UNRESOLVED] (S8) -- No forum clause quoted.
- Insolvency protection: -- [UNRESOLVED] (S8) -- Not described.
- Disclaimers: Noteholders have no direct claim on borrowers [PARTIALLY_VERIFIED] (S8)

### P2 Acme Treasury Vault

- Instrument nature: Vault shares [PARTIALLY_VERIFIED] (S7)
- Claim against: -- [UNRESOLVED] (S7) -- Not stated.
- Look-through: unresolved [PARTIALLY_VERIFIED] (S7) -- Docs describe no claim beyond the vault.
- Recourse: -- [UNRESOLVED]
- Governing law: -- [UNRESOLVED]
- Forum: -- [UNRESOLVED]
- Insolvency protection: -- [UNRESOLVED]
- Disclaimers: -- [UNRESOLVED]

## 8. Default and recovery path

### T1 Acme equipment credit

- Events of default: Payment default continuing for 30 days [PARTIALLY_VERIFIED] (S8)
- Enforcement: Security agent E3 enforces over the leased equipment [PARTIALLY_VERIFIED] (S8)
- Loss waterfall (1 absorbs first): [PARTIALLY_VERIFIED] (S8)
  1. Borrower equity
  2. Credit fund junior tranche
  3. Senior noteholders
- Recovery history: -- [UNRESOLVED] (S8) -- No recoveries reported.

### T2 Acme commodity trade finance

- Events of default: -- [UNRESOLVED] (S7) -- Vault docs describe no default events.
- Enforcement: -- [UNRESOLVED]
- Loss waterfall (1 absorbs first): -- [UNRESOLVED] (S7) -- Vault docs do not describe loss order.
- Recovery history: -- [UNRESOLVED]

## 9. L3 business

### T1 Acme equipment credit

- Description: Equipment leasing to mid-size manufacturers [PARTIALLY_VERIFIED] (S8)
- Revenue model: Monthly lease payments from lessees [PARTIALLY_VERIFIED] (S8)
- Cash generation: Lease collections paid to the warehouse SPV [PARTIALLY_VERIFIED] (S8)
- Collections control: Collection account controlled by the security agent [PARTIALLY_VERIFIED] (S5) -- Review mentions a third-party custodian over the receivables.
- Concentration: -- [UNRESOLVED] (S8) -- Memorandum gives no obligor concentration.
- Performance: -- [UNRESOLVED] (S8) -- No delinquency or default data published.
- Operating history: Leasing since 2019 [PARTIALLY_VERIFIED] (S1)

### T2 Acme commodity trade finance

- Description: Purchase and resale of agricultural commodities [PARTIALLY_VERIFIED] (S7)
- Revenue model: -- [UNRESOLVED] (S7) -- Margin on resale not described.
- Cash generation: -- [UNRESOLVED]
- Collections control: -- [UNRESOLVED]
- Concentration: -- [UNRESOLVED]
- Performance: -- [UNRESOLVED]
- Operating history: -- [UNRESOLVED]

## 10. Yield, fees and redemption

### Yield P1 Acme Senior Note

- Mechanism: Interest on receivables purchased at a discount [PARTIALLY_VERIFIED] (S8)
- Gross yield: 11.0 percent [PARTIALLY_VERIFIED] (S1)
- Net yield to holder: 9.5 percent [PARTIALLY_VERIFIED] (S1)
- Distribution method: rebasing [CONFIRMED] (S4)
- Distribution frequency: monthly [PARTIALLY_VERIFIED] (S8)

Underlying:

| description | asset class | share pct | location |
|---|---|---|---|
| Short-dated trade receivables [PARTIALLY_VERIFIED] (S8) | trade receivables [PARTIALLY_VERIFIED] (S8) | 100 [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] (S8) -- Receivables jurisdiction not stated. |

Fees:

| type | rate | recipient |
|---|---|---|
| management [PARTIALLY_VERIFIED] (S8) | 1.5 percent p.a. [PARTIALLY_VERIFIED] (S8) | E2 [PARTIALLY_VERIFIED] (S8) |

### Yield P2 Acme Treasury Vault

- Mechanism: Resale margin passed through the vault [PARTIALLY_VERIFIED] (S7)
- Gross yield: -- [UNRESOLVED]
- Net yield to holder: 4.1 percent [PARTIALLY_VERIFIED] (S1)
- Distribution method: claim [PARTIALLY_VERIFIED] (S7)
- Distribution frequency: daily [PARTIALLY_VERIFIED] (S7)

Underlying:

| description | asset class | share pct | location |
|---|---|---|---|
| Commodity purchase and resale contracts [PARTIALLY_VERIFIED] (S7) | trade finance [PARTIALLY_VERIFIED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] |

Fees:

| type | rate | recipient |
|---|---|---|
| vault [PARTIALLY_VERIFIED] (S7) | 0.30 percent [PARTIALLY_VERIFIED] (S7) | -- [UNRESOLVED] |

### Redemption

| product | mechanism | queue | settlement time | gating | fees |
|---|---|---|---|---|---|
| P1 | redemption request to issuer [PARTIALLY_VERIFIED] (S8) | monthly window [PARTIALLY_VERIFIED] (S8) | 2 business days [PARTIALLY_VERIFIED] (S6) -- Stated on an analyst call only. | issuer may suspend redemptions [PARTIALLY_VERIFIED] (S8) | -- [UNRESOLVED] (S8) -- No redemption fee stated. |
| P2 | instant burn against vault liquidity [PARTIALLY_VERIFIED] (S7) | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] | -- [UNRESOLVED] |

### Eligibility

| product | restrictions |
|---|---|
| P1 | professional investors only [PARTIALLY_VERIFIED] (S8) |
| P2 | -- [UNRESOLVED] (S1) -- Site does not state restrictions. |

## 11. Fund flows

Nodes:

| id | label | lane | layer | kind | chain | ref |
|---|---|---|---|---|---|---|
| n1 | Investor wallet | onchain | -- | investor | ethereum | -- |
| n2 | aSN token | onchain | L1 | contract | ethereum | 0x00000000000000000000000000000000000000a1 |
| n3 | Treasury vault | onchain | L1 | pool | ethereum | P2 |
| n4 | Ops multisig | onchain | -- | multisig | ethereum | 0x00000000000000000000000000000000000000b2 |
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
| n5 Off-ramp desk | n6 Issuer bank account | conversion | conversion | fiat_wire | -- | stablecoin to fiat | true [PARTIALLY_VERIFIED] (S1) |
| n6 Issuer bank account | n10 Credit fund | subscription | purchase | fiat_wire | X2 | fund subscription | true [PARTIALLY_VERIFIED] (S8) |
| n10 Credit fund | n11 Warehouse SPV | subscription | drawdown | fiat_wire | X3 | warehouse notes | true [PARTIALLY_VERIFIED] (S8) |
| n11 Warehouse SPV | n12 Equipment lessor | subscription | drawdown | fiat_wire | X4 | equipment loans | true [PARTIALLY_VERIFIED] (S8) |
| n11 Warehouse SPV | n8 Receivables portfolio | subscription | purchase | fiat_wire | X5 | receivables purchase | true [PARTIALLY_VERIFIED] (S8) |

### T1 Acme equipment credit -- claim

![Fund flow T1 claim](acme.flow-T1-claim.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n12 Equipment lessor | n7 Custodian | collateral | pledge | internal | X4 | equipment pledged | true [PARTIALLY_VERIFIED] (S8) |
| n8 Receivables portfolio | n7 Custodian | custody | title_transfer | internal | X5 | receivables held | true [PARTIALLY_VERIFIED] (S5) -- Review mentions a custodian. |

### T1 Acme equipment credit -- repayment

![Fund flow T1 repayment](acme.flow-T1-repayment.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n12 Equipment lessor | n11 Warehouse SPV | yield | repayment | fiat_wire | X4 | lease collections | true [PARTIALLY_VERIFIED] (S8) |
| n11 Warehouse SPV | n10 Credit fund | yield | repayment | fiat_wire | X3 | note repayments | -- [UNRESOLVED] (S8) -- Memorandum does not describe this hop. |
| n10 Credit fund | n6 Issuer bank account | yield | distribution | fiat_wire | X2 | fund distributions | true [PARTIALLY_VERIFIED] (S8) |
| n6 Issuer bank account | n9 Manager | fee | fee_payment | fiat_wire | -- | management fee | true [PARTIALLY_VERIFIED] (S8) |
| n2 aSN token | n1 Investor wallet | redemption | burn | burn | X1 | aSN burned on redemption | true [CONFIRMED] (S4) |

### T2 Acme commodity trade finance -- settlement

![Fund flow T2 settlement](acme.flow-T2-settlement.svg)

| from | to | kind | mechanism | rail | interface | label | claim |
|---|---|---|---|---|---|---|---|
| n5 Off-ramp desk | n6 Issuer bank account | conversion | conversion | fiat_wire | -- | stablecoin to fiat | true [PARTIALLY_VERIFIED] (S1) |
| n1 Investor wallet | n3 Treasury vault | subscription | deposit | stablecoin | X6 | vault deposit | true [PARTIALLY_VERIFIED] (S7) |
| n3 Treasury vault | n4 Ops multisig | collateral | pledge | internal | -- | reserve pledge | -- [UNRESOLVED] (S4) -- No pledge transfer observed on-chain. |
| n6 Issuer bank account | n13 Commodity buyer | subscription | purchase | fiat_wire | X7 | goods purchased | -- [UNRESOLVED] |
| n3 Treasury vault | n1 Investor wallet | yield | distribution | stablecoin | X6 | daily yield | true [PARTIALLY_VERIFIED] (S7) |

### T2 Acme commodity trade finance -- claim

- none

### T2 Acme commodity trade finance -- repayment

- none

## 12. On-chain contracts and control

| chain | address | role | source verified | proxy | upgrade admin | role admins | timelock delay s | multisig | threshold | signers |
|---|---|---|---|---|---|---|---|---|---|---|
| ethereum | 0x00000000000000000000000000000000000000a1 | aSN token [CONFIRMED] (S4) | true [CONFIRMED] (S4) | TransparentUpgradeableProxy [CONFIRMED] (S4) | 0x00000000000000000000000000000000000000b2 [CONFIRMED] (S4) | 0x00000000000000000000000000000000000000b2 [CONFIRMED] (S4) | 0 [CONFIRMED] (S4) -- No timelock between admin and proxy. | 0x00000000000000000000000000000000000000b2 [CONFIRMED] (S4) | 2 [CONFIRMED] (S4) | 3 [CONFIRMED] (S4) |

## 13. Findings

### Gaps

- **G1** [legal] [BLOCKING] Issuer financial statements and the custody agreement are not public. (S8)
  - **N1** Custody agreement and issuer accounts -- Company registry filings -- Confirm custody and financials (resolves G1; est 6 calls)
- **G2** [yield] Gross yield of the Treasury Vault is not disclosed. (S1, S7)
- **G3** [credit] [BLOCKING] Perfection of the security interest over the leased equipment is not evidenced. (S8)
  - **N3** Lien filings over the leased equipment -- Examplestan collateral registry -- Resolve the secured/unsecured discrepancy (resolves G3, D2; est 3 calls)

### Discrepancies

- **D1** [yield] Archived docs state a 0.30 percent vault fee; the current site states no fee. (S1, S7)
- **D2** [credit] The memorandum describes the equipment loans as secured; the independent review describes them as unsecured. (S5, S8) -- subjects: X4.security

### Structural changes

- **C1** [onchain] Upgrade admin changed from a single key to a 2-of-3 multisig. (S4)

### Open questions

- [legal] Which entity holds legal title to the receivables?
- [redemption] Can the issuer suspend redemptions without notice?

## 14. Issuer requests

- **Q1** (priority 1) Security agreement and lien filings for the equipment loans -- Confirm whether the T1 loans are secured and the security interest is perfected (answers C2, C5)
- **Q2** (priority 2) Commodity purchase and offtake contracts for the trade vault -- Identify the T2 counterparties and how the L3 business generates cash (answers A4, E1, E2)

## 15. Audits and size

### Audits

| auditor | scope | date | report |
|---|---|---|---|
| Example Audit Partners [PARTIALLY_VERIFIED] (S1) | aSN token contract [PARTIALLY_VERIFIED] (S1) | 2026-02-15 [PARTIALLY_VERIFIED] (S1) | -- |

### Size

| product | metric | value | as of |
|---|---|---|---|
| P1 | supply | 12500000 [CONFIRMED] (S4) | 2026-10-01 |
| P2 | tvl | 3400000 [PARTIALLY_VERIFIED] (S1) | 2026-10-01 |
| -- | originated | 48000000 [PARTIALLY_VERIFIED] (S1) | -- |

## 16. History

| date | change | evidence |
|---|---|---|
| 2026-03-01 | Vault fee stated as 0.30 percent in archived docs. | S7 |
| 2026-09-15 | Upgrade admin moved to a 2-of-3 multisig. | S4 |

## 17. Sources

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

## Appendix A. Analyst interventions

- none

## Appendix B. Unmapped facts

- The team plans a second chain deployment in 2027. (S1) -- why unmapped: Forward-looking statement; no schema field.

## Appendix C. Legend

- Claim cell: `value [FLAG] (evidence) -- note`; `--` means no value.
- CONFIRMED: verified by an independent source (legal facts: regulator, registry, auditor or on-chain).
- PARTIALLY_VERIFIED: self-reported by the project or the subject, or inferred from the cited evidence.
- UNRESOLVED: not found in the cited sources, or not searched when no source is cited.
- CONFLICTING: named by a discrepancy finding (see section 13).
- Layers: L1 on-chain capital vault; L2 credit financing layer; L3 underlying business layer.
- L3-O: the L3 business's paying customers or end borrowers (ultimate obligors), recorded as layer L3 with role ultimate_obligor and linked by within_L3 interfaces.
- Route (L1->L2): POOL supply to a shared lending pool; FUND subscription to a fund or vehicle; DIRECT financing of the credit counterparty itself; WRAPPER a position in another vault or token that holds the exposure.
- Method (L2->L3): DL direct loan; DI debt instrument (note, bond); AP purchase of receivables or other assets; PI participation interest; REPO repurchase agreement; PT principal purchase and resale (trade finance).
- Legal class: DL loan claim; DI debt instrument claim; AP ownership of purchased assets; PI participation interest; FI fund interest; EI equity interest; OTHER other or contractual claim.
- Flow views: settlement (capital and asset movement); claim (legal rights and collateral); repayment (cash back to L2 and L1, fees, enforcement path).
- Lanes: offchain, boundary (conversion, bridge and custody hand-off points), onchain.
- Diagram suffixes: [C] CONFIRMED, [P] PARTIALLY_VERIFIED, [U] UNRESOLVED ([U?] not searched), [X] CONFLICTING.
- Findings: G gap, D discrepancy, C structural change; issuer requests Q cite the research question codes they answer. No risk scores are given.
