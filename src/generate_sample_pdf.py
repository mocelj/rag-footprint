"""
Generate a realistic ~8-page footnote-heavy earnings report PDF.
============================================================
This creates a **fictitious** document for testing the Footnote-Aware
RAG Pipeline.  All companies, persons, and figures are imaginary.

Usage:
    python src/generate_sample_pdf.py            # default output → data/
    python src/generate_sample_pdf.py out.pdf     # custom output path

Requires:  pip install fpdf2
"""

from fpdf import FPDF
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Company identity (entirely fictitious)
# ---------------------------------------------------------------------------
COMPANY   = "Exemplar Corp"
TICKER    = "EXMPL"
QUARTER   = "Q3 2025"
QTR_RANGE = "July -- September"
FILED     = "October 28, 2025"
ISIN      = "US0000000000"
ADDRESS   = "100 Innovation Drive, Suite 4200\nSan Francisco, CA 94105"


class EarningsReport(FPDF):
    """Custom PDF layout with header, footer, and helper methods."""

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0, 6,
            f"CONFIDENTIAL -- {COMPANY} -- {QUARTER} Earnings Report",
            align="C",
        )
        self.ln(8)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    # -- reusable content helpers ------------------------------------------

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(20, 50, 100)
        self.cell(0, 10, title)
        self.ln(8)
        self.set_draw_color(20, 50, 100)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(40, 40, 40)
        self.cell(0, 8, title)
        self.ln(7)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(0, 5.5, text)
        self.ln(3)

    def footnote_section(self, footnotes):
        self.ln(5)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(100, 100, 100)
        for fn in footnotes:
            self.multi_cell(0, 4, fn)
            self.ln(1)

    def table_row(self, cells, bold=False, header=False):
        if header:
            self.set_font("Helvetica", "B", 9)
            self.set_fill_color(230, 235, 245)
        elif bold:
            self.set_font("Helvetica", "B", 9)
            self.set_fill_color(255, 255, 255)
        else:
            self.set_font("Helvetica", "", 9)
            self.set_fill_color(255, 255, 255)
        self.set_text_color(30, 30, 30)
        widths = [70, 30, 30, 30, 30]
        for i, cell in enumerate(cells):
            align = "L" if i == 0 else "R"
            self.cell(widths[i], 6.5, cell, border=1, align=align, fill=True)
        self.ln()


# ===================================================================
# Build the PDF
# ===================================================================
pdf = EarningsReport()
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

# ===================== PAGE 1: COVER =====================
pdf.add_page()
pdf.ln(20)

# Bold disclaimer banner
pdf.set_fill_color(255, 235, 235)
pdf.set_draw_color(200, 50, 50)
pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(180, 0, 0)
pdf.cell(0, 10,
    "THIS IS A FICTITIOUS DOCUMENT FOR DEMONSTRATION PURPOSES ONLY",
    border=1, align="C", fill=True,
)
pdf.ln(4)
pdf.set_font("Helvetica", "", 8)
pdf.set_text_color(140, 40, 40)
pdf.cell(0, 6,
    f"{COMPANY}, all persons, and all financial data herein are entirely imaginary.",
    align="C",
)
pdf.ln(18)

pdf.set_font("Helvetica", "B", 28)
pdf.set_text_color(20, 50, 100)
pdf.cell(0, 15, COMPANY, align="C")
pdf.ln(18)
pdf.set_font("Helvetica", "", 16)
pdf.set_text_color(60, 60, 60)
pdf.cell(0, 10, "Quarterly Earnings Report", align="C")
pdf.ln(10)
pdf.cell(0, 10, f"{QUARTER} ({QTR_RANGE})", align="C")
pdf.ln(20)
pdf.set_font("Helvetica", "I", 11)
pdf.set_text_color(120, 120, 120)
pdf.cell(0, 8, f"Filed: {FILED}", align="C")
pdf.ln(8)
pdf.cell(0, 8, f"NYSE: {TICKER}  |  ISIN: {ISIN}", align="C")
pdf.ln(20)
pdf.set_draw_color(200, 200, 200)
pdf.line(60, pdf.get_y(), 150, pdf.get_y())
pdf.ln(8)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(140, 140, 140)
pdf.multi_cell(
    0, 5,
    "CONFIDENTIAL: This document contains forward-looking statements and "
    "non-GAAP financial measures. Investors should read this report in its "
    "entirety, including all footnotes and supplementary disclosures, before "
    "making investment decisions. Past performance is not indicative of "
    "future results.",
    align="C",
)

# ===================== PAGE 2: EXECUTIVE SUMMARY =====================
pdf.add_page()
pdf.section_title("1. Executive Summary")

pdf.body_text(
    f"{COMPANY} delivered what management describes as a \"transformational "
    "quarter,\" reporting consolidated revenue of $2.4 billion, representing "
    "34% year-over-year growth [1]. The company achieved EBITDA of $680 "
    "million, a 28.3% margin that exceeds prior guidance [2]."
)
pdf.body_text(
    "Total shareholder return for the trailing twelve months reached 47%, "
    "outperforming the S&P 500 Financial Services Index by 22 percentage "
    "points [3]. The Board of Directors authorized a new $500 million share "
    "repurchase program [4], reflecting confidence in the company's "
    "long-term strategic positioning."
)
pdf.body_text(
    "Customer acquisition costs decreased by 18% quarter-over-quarter [5], "
    "while the net promoter score improved to an industry-leading 72 [6]. "
    "Management raised full-year revenue guidance to $9.2--9.5 billion [7]."
)

pdf.footnote_section([
    "[1] Revenue growth includes $820M from the Meridian Capital acquisition "
    "completed Aug 15, 2025. Organic revenue growth, excluding Meridian and "
    "currency effects, was 3.2%.",

    "[2] EBITDA is presented on a non-GAAP basis. Under GAAP, the company "
    "reported an operating loss of $145M due to $825M in acquisition-related "
    "charges, restructuring costs, and goodwill impairment. See Appendix B "
    "for reconciliation.",

    "[3] Total shareholder return calculation begins from the October 2024 "
    "low of $12.30/share, which followed a 67% drawdown from previous highs. "
    "Three-year TSR is -31%.",

    "[4] The repurchase program replaces an existing $1.2B authorization of "
    "which only $45M was executed due to covenant restrictions. The new "
    "program is similarly subject to credit facility limitations and may "
    "not be executed.",

    "[5] CAC decrease is measured on a per-unit basis. Total customer "
    "acquisition spending increased by $94M (41%) due to expansion into 12 "
    "new markets, and payback period extended from 14 to 29 months.",

    "[6] NPS of 72 is based on a survey of 340 enterprise clients "
    "(representing 8% of total customer base). SMB segment NPS, representing "
    "76% of revenue, declined to 31 from 45 in the prior quarter.",

    "[7] Guidance assumes successful integration of Meridian Capital, no "
    "further regulatory actions in the EU market (which generated $380M of "
    "2024 revenue), and continued access to the company's $3.1B revolving "
    "credit facility which matures January 2026.",
])

# ===================== PAGE 3: FINANCIAL PERFORMANCE =====================
pdf.add_page()
pdf.section_title("2. Financial Performance")

pdf.sub_title("2.1 Revenue Breakdown")
pdf.body_text(
    "Consolidated net revenue reached $2.4 billion in Q3 2025, compared to "
    "$1.79 billion in Q3 2024 [8]. Revenue by segment:"
)

pdf.table_row(["Segment", "Q3 2025", "Q3 2024", "Change", "% Rev"], header=True)
pdf.table_row(["Wealth Management",  "$1,020M", "$890M",  "+14.6%", "42.5%"])
pdf.table_row(["Capital Markets [9]", "$680M",   "$120M",  "+467%",  "28.3%"])
pdf.table_row(["Insurance Solutions", "$410M",   "$480M",  "-14.6%", "17.1%"])
pdf.table_row(["Digital Banking [10]","$290M",   "$300M",  "-3.3%",  "12.1%"])
pdf.table_row(["Total Consolidated",  "$2,400M", "$1,790M","+34.1%", "100%"], bold=True)
pdf.ln(5)

pdf.body_text(
    "Capital Markets revenue growth of 467% reflects the full quarter "
    "contribution from Meridian Capital [9]. The Insurance Solutions decline "
    "of 14.6% was primarily driven by reserve strengthening of $112M [11] "
    "following updated actuarial assumptions."
)
pdf.body_text(
    "International revenue represented 38% of total revenue [12], with "
    "particular strength in the Asia-Pacific region where revenue grew "
    "52% year-over-year [13]."
)

pdf.footnote_section([
    "[8] Q3 2024 revenue has been restated from the originally reported "
    "$1.94B to $1.79B due to a correction in revenue recognition timing "
    "identified during the Meridian integration audit. The restatement "
    "reduced previously reported 2024 full-year revenue by $340M.",

    "[9] Meridian Capital was acquired on August 15, 2025 for $4.2B (17x "
    "trailing revenue). Only 47 days of Meridian operations are included "
    "in Q3. Meridian's annualized revenue run-rate at acquisition was "
    "$1.1B, but this included $380M in one-time advisory fees from a "
    "single client restructuring.",

    "[10] Digital Banking revenue includes a $65M contract termination "
    "fee received from a departing enterprise client. Excluding this, "
    "Digital Banking organic revenue declined 25%.",

    "[11] Reserve strengthening relates to a portfolio of commercial real "
    "estate insurance contracts. An additional $200--400M reserve increase "
    "is considered probable in Q4 2025 pending the completion of external "
    "actuarial review.",

    "[12] International revenue includes intercompany transfer pricing "
    "adjustments of $190M. Revenue from unaffiliated international "
    "customers was 29% of total.",

    "[13] Asia-Pacific growth is calculated in local currency. On a USD "
    "basis, APAC revenue grew 11% due to significant currency headwinds. "
    "Additionally, 60% of APAC growth came from a single government "
    "contract with a 2-year non-renewable term.",
])

# ===================== PAGE 4: PROFITABILITY & CASH =====================
pdf.add_page()
pdf.sub_title("2.2 Profitability Analysis")

pdf.body_text(
    "Adjusted EBITDA reached $680 million with a margin of 28.3% [2]. Key "
    "margin drivers included a 340 basis point improvement in operating "
    "leverage from technology platform consolidation [14] and a $95 million "
    "reduction in compliance costs following the settlement of the DOJ "
    "inquiry [15]."
)
pdf.body_text(
    "Earnings per share (diluted) on an adjusted basis were $3.42, up 28% "
    "from $2.67 in Q3 2024 [16]. The effective tax rate was 12.4% [17], "
    "contributing approximately $0.45 to EPS relative to the statutory rate."
)

pdf.sub_title("2.3 Cash Flow and Liquidity")

pdf.body_text(
    "Operating cash flow was $520 million for the quarter [18]. Free cash "
    "flow reached $340 million after capital expenditures of $180 million "
    "[19]. The company ended the quarter with $1.8 billion in total "
    "liquidity [20]."
)
pdf.body_text(
    "The company successfully refinanced $750 million of its term loan "
    "facility at SOFR + 275 bps [21], representing a 50 basis point "
    "improvement from the prior facility. Total debt stood at $5.3 "
    "billion with a net leverage ratio of 3.4x adjusted EBITDA [22]."
)

pdf.footnote_section([
    "[14] Technology platform consolidation savings of $82M are partially "
    "offset by $45M in severance charges (excluded from Adjusted EBITDA) "
    "and ongoing annual maintenance costs of $38M for legacy systems that "
    "cannot be decommissioned until 2027 due to regulatory data retention "
    "requirements.",

    "[15] The DOJ settlement of $280M (paid in Q2 2025) resolved "
    "allegations of anti-competitive practices in the Wealth Management "
    "division. As part of the settlement, the company agreed to divest "
    "its municipal advisory business (contributing $120M annual revenue) "
    "by June 2026. An additional SEC investigation related to the same "
    "conduct remains ongoing.",

    "[16] Adjusted EPS excludes $4.18/share in charges for acquisition "
    "costs, restructuring, litigation settlements, and goodwill "
    "impairment. GAAP EPS (diluted) was $(0.76), representing a net "
    "loss of $198M.",

    "[17] The 12.4% effective tax rate reflects $156M in one-time tax "
    "benefits from the Meridian acquisition structure, including "
    "utilization of Meridian's accumulated NOLs. Normalized effective "
    "tax rate excluding discrete items is approximately 24--26%.",

    "[18] Operating cash flow includes $210M received from the early "
    "termination of legacy hedging positions. Excluding this one-time "
    "item, adjusted operating cash flow was $310M, a 22% decline from "
    "Q3 2024.",

    "[19] Capital expenditures of $180M include $95M in mandatory "
    "remediation spending for regulatory compliance deficiencies "
    "identified by FINRA. Discretionary growth capex was $85M, down "
    "40% from Q3 2024.",

    "[20] Total liquidity of $1.8B includes $600M in unrestricted cash, "
    "$900M undrawn on the revolving credit facility (maturing Jan 2026), "
    "and $300M in marketable securities. Of the cash balance, $410M is "
    "held in international subsidiaries subject to repatriation "
    "restrictions.",

    "[21] The refinancing includes a covenant modification that increased "
    "the maximum permitted leverage ratio from 3.5x to 4.5x through Q2 "
    "2026. The facility includes a springing covenant that reduces "
    "permitted leverage to 3.0x if the company fails to extend or "
    "replace the revolver by October 2025.",

    "[22] The 3.4x leverage ratio uses Adjusted EBITDA which adds back "
    "$825M in non-recurring charges. On a GAAP basis, the leverage ratio "
    "is approximately 9.8x, which would be in breach of the original "
    "covenant threshold.",
])

# ===================== PAGE 5: STRATEGIC INITIATIVES =====================
pdf.add_page()
pdf.section_title("3. Strategic Initiatives & Outlook")

pdf.sub_title("3.1 Meridian Capital Integration")

pdf.body_text(
    "The integration of Meridian Capital is proceeding on schedule [23]. "
    "Management has identified $350 million in annual run-rate cost "
    "synergies expected to be fully realized by Q4 2026 [24]. Client "
    "retention through the first 45 days post-close stands at 94% [25]."
)
pdf.body_text(
    f"The combined entity now serves over 4,200 institutional clients "
    f"across 28 countries [26], positioning {COMPANY} as the third-largest "
    "independent capital markets firm globally by assets under "
    "management [27]."
)

pdf.sub_title("3.2 ESG & Sustainability")

pdf.body_text(
    f"{COMPANY}'s ESG-aligned investment products attracted $8.2 billion "
    "in net inflows during Q3, bringing total ESG AUM to $42 billion "
    "[28]. The company was ranked #4 among financial services firms in "
    "the Dow Jones Sustainability Index [29]."
)

pdf.sub_title("3.3 Forward Guidance")

pdf.body_text(
    "Management raised full-year 2025 revenue guidance to $9.2--9.5 "
    "billion [7] and Adjusted EBITDA guidance to $2.5--2.7 billion. The "
    "company expects to achieve positive GAAP net income by Q2 2026 [30]."
)
pdf.body_text(
    "Key assumptions underlying guidance include: (i) stable or improving "
    "market conditions, (ii) successful Meridian integration, (iii) no "
    "material adverse regulatory actions, and (iv) continued access to "
    "current funding facilities. Capital allocation priorities remain "
    "organic growth investments, strategic M&A, and returning capital "
    "to shareholders [31]."
)

pdf.footnote_section([
    "[23] \"On schedule\" refers to the 18-month integration timeline. "
    "However, technology system integration (representing 65% of "
    "projected synergies) has not yet commenced and is dependent on "
    "regulatory approval of data migration plans, which the company "
    "has not yet applied for.",

    "[24] Synergy estimates are management projections and have not "
    "been independently validated. Comparable transactions in the "
    "sector have historically achieved 40--60% of initially projected "
    "synergies. Restructuring costs to achieve synergies are estimated "
    "at $280--350M (not included in synergy calculations).",

    "[25] Client retention is measured by number of accounts, not by "
    "revenue or AUM. Seven of Meridian's top 20 clients (representing "
    "38% of Meridian revenue) have initiated RFP processes with "
    "competing firms. Retention measured by AUM is 71%.",

    "[26] Client count includes dormant accounts with no activity in "
    "the trailing 12 months. Active client relationships (at least one "
    "transaction in TTM) total approximately 2,800.",

    "[27] Ranking based on combined pro forma AUM as of August 31, "
    "2025 using management's methodology. Under the standard industry "
    "methodology (GIPS-compliant), the company would rank seventh.",

    "[28] $3.4B of ESG inflows came from a single sovereign wealth "
    "fund mandate that has a 90-day liquidity option. Additionally, "
    "the SEC has issued a proposed rule that would reclassify $18B of "
    "the company's current ESG-labeled products as non-qualifying "
    "under new disclosure requirements (comment period closes "
    "December 2025).",

    "[29] The DJSI ranking is based on 2024 data. The company received "
    "a warning from the DJSI committee in September 2025 regarding "
    "potential score reduction following the DOJ settlement "
    "disclosure [15].",

    "[30] The path to positive GAAP net income assumes no additional "
    "impairment charges on the $4.2B Meridian goodwill. Current fair "
    "value analysis suggests Meridian's equity value has declined by "
    "approximately 20--30% since close due to the departure of key "
    "revenue-generating professionals.",

    "[31] During the last 8 quarters, 92% of free cash flow has been "
    "directed to debt service and acquisition financing. No common "
    "dividends have been paid since Q1 2024, and the repurchase "
    "program [4] remains subject to lender consent.",
])

# ===================== PAGE 6: RISK FACTORS =====================
pdf.add_page()
pdf.section_title("4. Risk Factors & Legal Proceedings")

pdf.body_text(
    "The company is subject to various legal and regulatory proceedings "
    "in the ordinary course of business. Material developments during "
    "Q3 2025 include:"
)
pdf.body_text(
    "Regulatory Matters: Following the DOJ settlement [15], the SEC has "
    "opened a formal investigation into the company's revenue recognition "
    "practices for the periods 2022--2024 [32]. The company has received "
    "a Wells Notice and is evaluating its response options."
)
pdf.body_text(
    "Litigation: A securities class action lawsuit was filed on "
    "September 15, 2025 (Johnson v. Exemplar Corp, S.D.N.Y.) alleging "
    "material misstatements in prior earnings releases related to "
    "organic growth metrics [33]. The company believes the claims are "
    "without merit and intends to vigorously defend."
)
pdf.body_text(
    "Cybersecurity: On August 22, 2025, the company detected and "
    "contained an unauthorized access event affecting certain client "
    "data systems [34]. Remediation is ongoing."
)
pdf.body_text(
    "Credit Risk: The commercial real estate insurance portfolio "
    "continues to face headwinds [11]. Additionally, the company's "
    "leveraged loan portfolio of $2.1 billion has experienced credit "
    "deterioration, with non-performing assets rising to 8.4% [35]."
)

pdf.footnote_section([
    "[32] The SEC investigation specifically concerns whether the "
    "company improperly classified Meridian-related pre-acquisition "
    "consulting fees ($140M over 2022--2024) as organic revenue. If "
    "substantiated, this may require restatement of historical "
    "financials and could constitute a material weakness in internal "
    "controls.",

    "[33] The class action seeks damages of up to $2.8B. The complaint "
    "alleges that management inflated organic growth figures by 8--12 "
    "percentage points in public filings over six consecutive quarters. "
    "Discovery has been initiated and lead plaintiff certification "
    "is pending.",

    "[34] The cybersecurity incident affected an estimated 2.3 million "
    "client records including SSNs, account numbers, and transaction "
    "histories. Notification letters were sent on October 1, 2025. "
    "Estimated remediation and liability costs range from $120M to "
    "$340M. Three state attorneys general have opened investigations.",

    "[35] Non-performing assets of 8.4% compare to an industry average "
    "of 2.1% and are concentrated in office and retail real estate "
    "sectors. The company's allowance for credit losses covers 45% of "
    "non-performing assets, compared to the regulatory recommended "
    "minimum of 60%. An additional $180M provision may be required.",
])

# ===================== PAGE 7: GOVERNANCE =====================
pdf.add_page()
pdf.section_title("5. Corporate Governance Updates")

pdf.body_text(
    "The Board of Directors approved several governance enhancements "
    f"during Q3 2025, reinforcing {COMPANY}'s commitment to "
    "best-in-class corporate governance [36]:"
)
pdf.body_text(
    "Executive Compensation: The Compensation Committee awarded "
    "CEO Robert Chen a performance-based equity grant valued at "
    "$28 million [37], tied to achievement of 2025--2027 strategic "
    "plan milestones including revenue growth, margin expansion, "
    "and TSR targets."
)
pdf.body_text(
    "Board Composition: The Board appointed Dr. Maria Santos as "
    "Lead Independent Director effective October 1, 2025 [38]. "
    "Two new independent directors with fintech expertise were "
    "added, bringing independent representation to 75% [39]."
)
pdf.body_text(
    "Internal Controls: In response to the revenue recognition "
    "review [32], the Audit Committee has engaged an independent "
    "accounting firm to conduct a comprehensive internal controls "
    "assessment [40]. Results are expected in Q1 2026."
)

pdf.footnote_section([
    "[36] ISS Governance QualityScore for the company declined from "
    "3 (mid-range) to 8 (high concern) in October 2025 due to "
    "executive compensation concerns and the pending SEC "
    "investigation. Glass Lewis issued a recommendation against "
    "the re-election of three incumbent directors.",

    "[37] The $28M equity grant vests 100% upon achievement of any "
    "one of the following: (i) revenue of $10B (achievable via "
    "acquisition), (ii) stock price of $45 (currently $38, "
    "representing only 18% upside), or (iii) continued employment "
    "through December 2027 regardless of performance. The grant "
    "was not submitted for shareholder advisory vote.",

    "[38] Dr. Santos also serves as a board member of Meridian's "
    "largest client, representing a potential conflict of interest "
    "that has not been reviewed by the Governance Committee. "
    "Additionally, she was previously employed by the company from "
    "2018--2021, which may affect her classification as "
    "'independent' under certain governance frameworks.",

    "[39] The 75% independence calculation excludes one director "
    "whose consulting firm received $4.2M from the company in "
    "2025. Under the NYSE listing standard's stricter "
    "interpretation, independent representation may be as low "
    "as 58%.",

    "[40] The company's current external auditor, Grant & Sullivan "
    "LLP, was simultaneously engaged for the internal controls "
    "review and continues to serve as the company's statutory "
    "auditor, representing a potential independence conflict. Two "
    "audit committee members have raised concerns about this "
    "arrangement.",
])

# ===================== PAGE 8: DISCLAIMER =====================
pdf.add_page()
pdf.section_title("Legal Disclaimer & Forward-Looking Statements")

pdf.set_font("Helvetica", "", 8.5)
pdf.set_text_color(80, 80, 80)
pdf.multi_cell(
    0, 4.5,
    "This report contains forward-looking statements within the meaning "
    "of Section 27A of the Securities Act of 1933 and Section 21E of the "
    "Securities Exchange Act of 1934. These statements involve known and "
    "unknown risks, uncertainties and other factors which may cause actual "
    "results, performance or achievements to be materially different from "
    "any future results, performances or achievements expressed or implied "
    "by the forward-looking statements. Such factors include, but are not "
    "limited to: changes in general economic conditions; the effects of "
    "competition; regulatory developments; the company's ability to "
    "successfully integrate acquisitions; cybersecurity risks; and other "
    "risks detailed in the company's filings with the SEC.\n\n"
    "Non-GAAP Financial Measures: This report includes non-GAAP financial "
    "measures including Adjusted EBITDA, Adjusted EPS, organic revenue "
    "growth, and free cash flow. These measures should not be considered "
    "as alternatives to GAAP measures. Management believes these non-GAAP "
    "measures provide useful information about the company's operating "
    "performance, but investors should review the GAAP-to-non-GAAP "
    "reconciliations in Appendix B.\n\n"
    f"The information contained herein is as of {FILED} and is subject "
    f"to change without notice. {COMPANY} undertakes no obligation to "
    "update any forward-looking statements.\n\n"
    "This document is intended for institutional investors and qualified "
    "purchasers only. It does not constitute an offer to sell or a "
    "solicitation of an offer to buy any securities.",
)

pdf.ln(8)

# Repeat fictitious disclaimer
pdf.set_fill_color(255, 235, 235)
pdf.set_draw_color(200, 50, 50)
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(180, 0, 0)
pdf.cell(0, 9,
    "THIS IS A FICTITIOUS DOCUMENT FOR DEMONSTRATION PURPOSES ONLY",
    border=1, align="C", fill=True,
)
pdf.ln(4)
pdf.set_font("Helvetica", "", 8)
pdf.set_text_color(140, 40, 40)
pdf.cell(0, 5,
    f"{COMPANY}, all persons, and all financial data herein are entirely "
    "imaginary. No real entity is depicted or intended.",
    align="C",
)

pdf.ln(12)
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(20, 50, 100)
pdf.cell(0, 8, "Contact Information")
pdf.ln(8)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(60, 60, 60)
pdf.multi_cell(
    0, 5,
    "Investor Relations: Sarah Kim, SVP Investor Relations\n"
    f"Email: ir@exemplarcorp.com | Phone: (415) 555-0142\n"
    f"Media: press@exemplarcorp.com\n\n"
    f"{COMPANY}\n"
    f"{ADDRESS}",
)


# ===================================================================
# Save
# ===================================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        out = Path(sys.argv[1])
    else:
        out = Path(__file__).parent.parent / "data" / "Exemplar_Corp_Q3_2025_Earnings.pdf"

    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"Generated {pdf.pages_count} pages -> {out}")
