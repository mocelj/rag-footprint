    # Footnote-Aware RAG — Summary Comparison Report

    | Field | Value |
    |---|---|
    | **Source Document** | `Exemplar_Corp_Q3_2025_Earnings.pdf` |
    | **Generated** | 2026-02-28 23:17:00 |
    | **SLM Model** | `gpt-5-mini` |
    | **LLM Model** | `gpt-5.2` |
    | **Chunk Size** | 800 chars |
    | **Retrieval** | Multi-query (5 sub-queries × k=4) |

    ---

    ## 1. Baseline Summary (Without SLM Footnote Stitching)

    > Standard RAG approach: raw text is chunked and summarized directly.
    > Footnotes may be separated from the text they qualify.

    ### Executive Summary — Exemplar Corp (Q3 2025)

**Revenue performance**
- **Consolidated net revenue:** **$2.4B** in Q3 2025 vs. $1.79B in Q3 2024 (**+34.1% YoY**). Growth included **$820M from the Meridian Capital acquisition**; **organic revenue growth was 3.2%** (ex‑Meridian and FX).
- **Segment mix and key drivers:**
  - **Wealth Management:** **$1,020M** (**+14.6%**) — largest segment (42.5% of revenue).
  - **Capital Markets:** **$680M** (**+467%**) — primarily the **first full quarter of Meridian** contribution.
  - **Insurance Solutions:** **$410M** (**-14.6%**) — decline driven by **$112M reserve strengthening** tied to updated actuarial assumptions; **additional $200–400M reserve increase is considered probable in Q4 2025** pending external review.
  - **Digital Banking:** **$290M** (**-3.3%**) — includes a **$65M contract termination fee**; **excluding this, organic revenue declined 25%**, indicating underlying pressure.
- **Outlook:** Management **raised FY2025 revenue guidance to $9.2–$9.5B** and **Adjusted EBITDA guidance to $2.5–$2.7B**, assuming stable markets, successful Meridian integration, no material regulatory action, and continued funding access.

**Profitability and cash flow**
- **Adjusted EBITDA:** **$680M** with **28.3% margin**, supported by **340 bps operating leverage improvement** from technology platform consolidation and **$95M lower compliance costs** following the DOJ settlement.
- **Adjusted EPS (diluted):** **$3.42**, up **28% YoY**; reported effective tax rate was **12.4%** (management notes normalized rate excluding discrete items is ~**24–26%**).
- **GAAP vs non-GAAP divergence:** Despite strong Adjusted EBITDA, the company reported a **GAAP operating loss of $145M** due to **$825M** in acquisition-related charges, restructuring, and goodwill impairment (materially affecting comparability and leverage metrics).
- **Cash generation:** **Operating cash flow $520M**, but included a **$210M one-time** benefit from early termination of legacy hedges; **adjusted operating cash flow was $310M (down 22% YoY)**. **Free cash flow was $340M** after **$180M capex**, including **$95M mandatory regulatory remediation** spending (discretionary growth capex down 40% YoY).

**Operational status and capital structure**
- **Meridian integration:** Reported as **on schedule**; **$350M annual run-rate cost synergies** targeted by **Q4 2026**; **94% client retention** through first 45 days. Combined footprint: **4,200+ institutional clients in 28 countries**.
- **Customer/brand indicators:** Customer acquisition costs down **18% QoQ**; net promoter score improved to **72**.
- **Liquidity and refinancing:** Total liquidity **$1.8B** (cash **$600M**, revolver availability **$900M** maturing **Jan 2026**, marketable securities **$300M**). **$410M of cash is held internationally** with repatriation restrictions. Covenant changes increased max leverage to **4.5x through Q2 2026**; the firm cites **3.4x leverage using Adjusted EBITDA**, but **~9.8x on a GAAP basis**, highlighting reliance on add-backs. Revolver extension/refinancing remains a key timeline item (maturity Jan 2026).

**Key risks**
- **Regulatory and accounting risk (high):** The **SEC opened a formal investigation** into **revenue recognition (2022–2024)**; the company received a **Wells Notice**. The investigation focuses on whether **$140M of Meridian-related pre-acquisition consulting fees** were improperly classified as **organic revenue**—potentially requiring **restatement** and indicating a possible **material weakness in internal controls**.
- **Litigation risk:** A **securities class action** (Johnson v. Exemplar Corp, filed Sept. 15, 2025) alleges misstatements related to organic growth metrics.
- **Insurance reserve risk:** Ongoing headwinds in the **commercial real estate insurance portfolio**, with **additional reserve strengthening ($200–$400M) considered probable** in Q4 2025.
- **Credit risk:** **$2.1B leveraged loan portfolio** showing deterioration; **non-performing assets at 8.4%**.
- **Cybersecurity risk:** An **unauthorized access event** (Aug. 22, 2025) affected certain client data systems; remediation ongoing.
- **Funding/covenant risk:** Dependence on continued access to revolving credit facilities and covenant compliance; GAAP leverage would have breached prior limits absent covenant relief and non-GAAP adjustments.

Overall, Q3 shows headline growth and improved adjusted profitability largely driven by Meridian and cost actions, but the investment case is constrained by significant **non-GAAP/GAAP divergence**, **pending SEC action and potential restatement**, **reserve and credit deterioration**, and **near-term refinancing/covenant sensitivity**.

    ---

    ## 2. Enriched Summary (With SLM Footnote Stitching)

    > Hybrid approach: an SLM first inlines footnote text next to citing
    > sentences, then the enriched text is chunked and summarized.

    ### Executive Summary (Q3 2025) — Exemplar Corp

**Revenue performance**
- **Consolidated net revenue was $2.4B (+34% YoY)** versus **Q3 2024 revenue restated to $1.79B** (from $1.94B) due to a revenue-recognition timing correction found during the Meridian integration audit; the restatement reduced previously reported FY2024 revenue by **$340M**. Reported growth was **heavily acquisition-driven**: **$820M** came from the **Meridian Capital acquisition**, while **organic revenue growth was 3.2%** (ex-Meridian and currency).
- **Segment mix and key quality items**
  - **Wealth Management:** **$1.02B (+14.6%)**, 42.5% of revenue.
  - **Capital Markets:** **$680M (+467%)**, 28.3% of revenue, driven by Meridian. Only **47 days** of Meridian operations are included; Meridian’s **$1.1B annualized run-rate** at acquisition included **$380M of one-time advisory fees from a single client restructuring**, tempering run-rate quality.
  - **Insurance Solutions:** **$410M (-14.6%)**.
  - **Digital Banking:** **$290M (-3.3%)**, but includes a **$65M contract termination fee**; **excluding this, organic revenue declined 25%**.

**Profitability and earnings quality**
- The company reported **Adjusted EBITDA of $680M (28.3% margin)** and **Adjusted diluted EPS of $3.42 (+28% YoY)**.
- These are **non-GAAP results** and exclude substantial items: **Adjusted EPS excludes $4.18/share** of acquisition costs, restructuring, litigation settlements, and goodwill impairment. On a **GAAP basis, diluted EPS was $(0.76)** and the company reported a **net loss of $198M**; GAAP also reflected an **operating loss of $145M** tied to **$825M** of acquisition-related charges/restructuring/goodwill impairment.
- **Effective tax rate was 12.4%**, boosting EPS by about **$0.45** versus statutory, but this was driven by **$156M of one-time tax benefits** (Meridian acquisition structure, including use of NOLs). **Normalized tax rate is ~24–26%**, implying less favorable tax support going forward.

**Cash flow, liquidity, and capital allocation**
- **Operating cash flow was $520M**, but included **$210M** from early termination of legacy hedges; **adjusted OCF was $310M**, a **22% decline YoY**.
- **Free cash flow was $340M** after **$180M capex**, of which **$95M was mandatory regulatory remediation** (FINRA-identified compliance deficiencies). **Discretionary growth capex was $85M**, **down 40% YoY**, indicating constrained growth investment.
- **Total liquidity ended at $1.8B**, comprised of **$600M cash**, **$900M undrawn revolver** (matures **Jan 2026**), and **$300M marketable securities.** However, **$410M of cash is held in international subsidiaries with repatriation restrictions**, reducing near-term flexibility.
- While management cites capital return priorities, disclosures indicate **92% of free cash flow over the last 8 quarters went to debt service and acquisition financing**; **no common dividends since Q1 2024**, and the **repurchase program is subject to lender consent/covenant limits** (prior $1.2B authorization saw only $45M executed for this reason; the new program may likewise not be executable).

**Operational status / integration**
- Management states Meridian integration is “on schedule” within an **18-month timeline**, but **technology system integration (65% of projected synergies) has not started** and depends on **regulatory approval of data migration plans that have not yet been applied for**, creating execution and timing risk.
- Full-year revenue guidance was raised to **$9.2–$9.5B**, but it is **conditional** on successful Meridian integration, **no additional EU regulatory actions** (EU generated **$380M of 2024 revenue**), and **continued access to the $3.1B revolver** (also maturing **Jan 2026**).

**Key risks and uncertainties**
- **Cybersecurity / data breach:** Incident impacted an estimated **2.3M client records** (including SSNs, account numbers, transaction histories). Notifications were sent Oct 1, 2025. **Estimated remediation/liability: $120M–$340M**, with **three state AG investigations** underway; remediation is ongoing.
- **Regulatory/legal:** Following a DOJ settlement, the **SEC opened a formal investigation** into certain client data systems, adding regulatory overhang and potential incremental costs/constraints.
- **Credit/reserve risk (Insurance):** Commercial real estate insurance portfolio pressures continue; an **additional $200M–$400M reserve increase is considered probable in Q4 2025**, pending an external actuarial review.
- **Governance / shareholder risk:** Governance perception deteriorated (ISS QualityScore worsened from **3 to 8**, “high concern,” tied to executive comp and the pending SEC investigation; Glass Lewis recommended against re-electing three directors). CEO received a **$28M equity grant** with **low performance hurdles** (can vest on revenue achievable via acquisition, modest stock appreciation, or simply continued employment), and it was **not submitted for a shareholder advisory vote**.
- **Financing/refinancing risk:** Material reliance on revolving credit facilities with near-term maturity (Jan 2026) and capital return limitations due to covenants.

    ---

    ## 3. Key Differences

    The baseline summary likely presents headline figures at face value,
    while the enriched summary incorporates footnote qualifications that
    may materially change interpretation. Compare how each version handles:

    - **Revenue composition** — Does the summary flag one-time items or acquisition effects?
    - **Forward guidance** — Does it note conditions, risks, or contingencies in the footnotes?
    - **Reported metrics** — Does it surface GAAP vs. non-GAAP discrepancies?
    - **Cash flow & liquidity** — Does it include capex context and debt detail?
    - **Operational highlights** — Does it cover market position and competitive landscape?

    > **Tip — HTML Audit Report colour coding:**
    > Open the companion `audit_report_*.html` for a visual, sentence-level
    > semantic diff.  Sentences with an **amber left-border** appear only in
    > the baseline summary (information lost or absent in the enriched version).
    > Sentences with a **green left-border** appear only in the enriched
    > summary (new insights surfaced by footnote stitching).  Sentences with
    > no border are semantically shared by both summaries.

    ---

    ## 4. Discovered Footnotes

    | Marker | Footnote Text | Status |
    |---|---|---|
    | [1] | Revenue growth includes $820M from the Meridian Capital acquisition completed Aug 15, 2025. Organic revenue growth, excluding Meridian and currency effects, was 3.2%. | linked |
| [2] | EBITDA is presented on a non-GAAP basis. Under GAAP, the company reported an operating loss of $145M due to $825M in acquisition-related charges, restructuring costs, and goodwill impairment. See Appendix B for reconciliation. | linked |
| [3] | Total shareholder return calculation begins from the October 2024 low of $12.30/share, which followed a 67% drawdown from previous highs. Three-year TSR is -31%. | linked |
| [4] | The repurchase program replaces an existing $1.2B authorization of which only $45M was executed due to covenant restrictions. The new program is similarly subject to credit facility limitations and may not be executed. | linked |
| [5] | CAC decrease is measured on a per-unit basis. Total customer acquisition spending increased by $94M (41%) due to expansion into 12 new markets, and payback period extended from 14 to 29 months. | linked |
| [6] | NPS of 72 is based on a survey of 340 enterprise clients (representing 8% of total customer base). SMB segment NPS, representing 76% of revenue, declined to 31 from 45 in the prior quarter. | linked |
| [7] | Guidance assumes successful integration of Meridian Capital, no further regulatory actions in the EU market (which generated $380M of 2024 revenue), and continued access to the company's $3.1B revolving credit facility which matures January 2026. | linked |
| [8] | Q3 2024 revenue has been restated from the originally reported $1.94B to $1.79B due to a correction in revenue recognition timing identified during the Meridian integration audit. The restatement reduced previously reported 2024 full-year revenue by $340M | linked |
| [9] | Meridian Capital was acquired on August 15, 2025 for $4.2B (17x trailing revenue). Only 47 days of Meridian operations are included in Q3. Meridian's annualized revenue run-rate at acquisition was $1.1B, but this included $380M in one-time advisory fees from a single client restructuring. | linked |
| [10] | Digital Banking revenue includes a $65M contract termination fee received from a departing enterprise client. Excluding this, Digital Banking organic revenue declined 25%. | linked |
| [11] | Reserve strengthening relates to a portfolio of commercial real estate insurance contracts. An additional $200--400M reserve increase is considered probable in Q4 2025 pending the completion of external actuarial review. | linked |
| [12] | International revenue includes intercompany transfer pricing adjustments of $190M. Revenue from unaffiliated international customers was 29% of total. | linked |
| [13] | Asia-Pacific growth is calculated in local currency. On a USD basis, APAC revenue grew 11% due to significant currency headwinds. Additionally, 60% of APAC growth came from a single government contract with a 2-year non-renewable term. | linked |
| [14] | Technology platform consolidation savings of $82M are partially offset by $45M in severance charges (excluded from Adjusted EBITDA) and ongoing annual maintenance costs of $38M for legacy systems that cannot be decommissioned until 2027 due to regulatory data retention requirements. | linked |
| [15] | The DOJ settlement of $280M (paid in Q2 2025) resolved allegations of anti-competitive practices in the Wealth Management division. As part of the settlement, the company agreed to divest its municipal advisory business (contributing $120M annual revenue) by June 2026. An additional SEC investigation related to the same conduct remains ongoing. | linked |
| [16] | Adjusted EPS excludes $4.18/share in charges for acquisition costs, restructuring, litigation settlements, and goodwill impairment. GAAP EPS (diluted) was $(0.76), representing a net loss of $198M. | linked |
| [17] | The 12.4% effective tax rate reflects $156M in one-time tax benefits from the Meridian acquisition structure, including utilization of Meridian's accumulated NOLs. Normalized effective tax rate excluding discrete items is approximately 24--26%. | linked |
| [18] | Operating cash flow includes $210M received from the early termination of legacy hedging positions. Excluding this one-time item, adjusted operating cash flow was $310M, a 22% decline from Q3 2024. | linked |
| [19] | Capital expenditures of $180M include $95M in mandatory remediation spending for regulatory compliance deficiencies identified by FINRA. Discretionary growth capex was $85M, down 40% from Q3 2024. | linked |
| [20] | Total liquidity of $1.8B includes $600M in unrestricted cash, $900M undrawn on the revolving credit facility (maturing Jan 2026), and $300M in marketable securities. Of the cash balance, $410M is held in international subsidiaries subject to repatriation restrictions. | linked |
| [21] | The refinancing includes a covenant modification that increased the maximum permitted leverage ratio from 3.5x to 4.5x through Q2 2026. The facility includes a springing covenant that reduces permitted leverage to 3.0x if the company fails to extend or replace the revolver by October 2025. | linked |
| [22] | The 3.4x leverage ratio uses Adjusted EBITDA which adds back $825M in non-recurring charges. On a GAAP basis, the leverage ratio is approximately 9.8x, which would be in breach of the original covenant threshold. | linked |
| [23] | "On schedule" refers to the 18-month integration timeline. However, technology system integration (representing 65% of projected synergies) has not yet commenced and is dependent on regulatory approval of data migration plans, which the company has not yet applied for. | linked |
| [24] | Synergy estimates are management projections and have not been independently validated. Comparable transactions in the sector have historically achieved 40--60% of initially projected synergies. Restructuring costs to achieve synergies are estimated at $280--350M (not included in synergy calculations). | linked |
| [25] | Client retention is measured by number of accounts, not by revenue or AUM. Seven of Meridian's top 20 clients (representing 38% of Meridian revenue)
have initiated RFP processes with competing firms. Retention measured by AUM is 71%. | linked |
| [26] | Client count includes dormant accounts with no activity in the trailing 12 months. Active client relationships (at least one transaction in TTM) total
approximately 2,800. | linked |
| [27] | Ranking based on combined pro forma AUM as of August 31, 2025 using management's methodology. Under the standard industry methodology
(GIPS-compliant), the company would rank seventh. | linked |
| [28] | $3.4B of ESG inflows came from a single sovereign wealth fund mandate that has a 90-day liquidity option. Additionally, the SEC has issued a proposed
rule that would reclassify $18B of the company's current ESG-labeled products as non-qualifying under new disclosure requirements (comment period closes
December 2025). | linked |
| [29] | The DJSI ranking is based on 2024 data. The company received a warning from the DJSI committee in September 2025 regarding potential score reduction
following the DOJ settlement disclosure [15]. | linked |
| [30] | The path to positive GAAP net income assumes no additional impairment charges on the $4.2B Meridian goodwill. Current fair value analysis suggests
Meridian's equity value has declined by approximately 20--30% since close due to the departure of key revenue-generating professionals. | linked |
| [31] | During the last 8 quarters, 92% of free cash flow has been directed to debt service and acquisition financing. No common dividends have been paid since Q1 2024, and the repurchase program [4] remains subject to lender consent. | linked |
| [32] | The SEC investigation specifically concerns whether the company improperly classified Meridian-related pre-acquisition consulting fees ($140M over 2022--2024) as organic revenue. If substantiated, this may require restatement of historical financials and could constitute a material weakness in internal controls. | linked |
| [33] | The class action seeks damages of up to $2.8B. The complaint alleges that management inflated organic growth figures by 8--12 percentage points in public filings over six consecutive quarters. Discovery has been initiated and lead plaintiff certification is pending. | linked |
| [34] | The cybersecurity incident affected an estimated 2.3 million client records including SSNs, account numbers, and transaction histories. Notification letters were sent on October 1, 2025. Estimated remediation and liability costs range from $120M to $340M. Three state attorneys general have opened investigations. | linked |
| [35] | Non-performing assets of 8.4% compare to an industry average of 2.1% and are concentrated in office and retail real estate sectors. The company's allowance for credit losses covers 45% of non-performing assets, compared to the regulatory recommended minimum of 60%. An additional $180M provision may be required. | linked |
| [36] | ISS Governance QualityScore for the company declined from 3 (mid-range) to 8 (high concern) in October 2025 due to executive compensation concerns and the pending SEC investigation. Glass Lewis issued a recommendation against the re-election of three incumbent directors. | linked |
| [37] | The $28M equity grant vests 100% upon achievement of any one of the following: (i) revenue of $10B (achievable via acquisition), (ii) stock price of $45 (currently $38, representing only 18% upside), or (iii) continued employment through December 2027 regardless of performance. The grant was not submitted for shareholder advisory vote. | linked |
| [38] | Dr. Santos also serves as a board member of Meridian's largest client, representing a potential conflict of interest that has not been reviewed by the Governance Committee. Additionally, she was previously employed by the company from 2018--2021, which may affect her classification as 'independent' under certain governance frameworks. | linked |
| [39] | The 75% independence calculation excludes one director whose consulting firm received $4.2M from the company in 2025. Under the NYSE listing standard's stricter interpretation, independent representation may be as low as 58%. | linked |
| [40] | The company's current external auditor, Grant & Sullivan LLP, was simultaneously engaged for the internal controls review and continues to serve as the company's statutory auditor, representing a potential independence conflict. Two audit committee members have raised concerns about this arrangement. | linked |

    ---

    ## 5. Architecture

    ```
    ┌─────────────┐
    │ Load Doc    │
    └──────┬──────┘
           │
     ┌─────┴─────┐
     │            │
     ▼            ▼
    ┌──────┐  ┌───────────┐
    │Naive │  │SLM Stitch │  ← GPT-5.2-mini inlines footnotes
    │Chunk │  └─────┬─────┘
    └──┬───┘        │
       │        ┌───┴───┐
       │        │Enrich │
       │        │Chunk  │
       │        └───┬───┘
       ▼            ▼
    ┌──────┐  ┌──────────┐
    │FAISS │  │  FAISS   │
    │(raw) │  │(enriched)│
    └──┬───┘  └────┬─────┘
       │           │
       ▼           ▼
    ┌──────┐  ┌──────────┐
    │ LLM  │  │   LLM    │  ← GPT-5.2 summarizes
    │ Sum  │  │   Sum    │
    └──┬───┘  └────┬─────┘
       │           │
       └─────┬─────┘
             ▼
       ┌───────────┐
       │  Report   │  → summary_report_*.md
       └───────────┘
    ```

    *Generated by LangGraph Footnote RAG Pipeline*
