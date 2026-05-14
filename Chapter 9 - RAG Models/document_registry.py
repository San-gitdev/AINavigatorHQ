# document_registry.py
# Central registry for all RAG lab documents.
#
# Each document has:
#   - id:           short key used throughout the codebase
#   - title:        display name
#   - filename:     local path under documents/
#   - url:          direct PDF download link
#   - topic:        audience interest tag
#   - description:  one-line summary for the menu
#   - questions:    3 questions calibrated to produce hallucination
#                   in Act 1 and grounded answers in Act 2
#
# Adding a new document: add a new entry to DOCUMENT_REGISTRY.
# The rest of the codebase reads from here — no other changes needed.

DOCUMENT_REGISTRY = {

    "boe_mpr": {
        "id":          "boe_mpr",
        "title":       "Bank of England — Monetary Policy Report, Feb 2025",
        "filename":    "documents/boe_mpr_feb2025.pdf",
        "url":         "https://www.bankofengland.co.uk/monetary-policy-report/2025/february-2025",
        "topic":       "Finance / Central Banking",
        "description": "UK interest rate decisions, GDP and inflation forecasts from the MPC",
        "questions": [
            {
                "id":    "Q1",
                "topic": "GDP Growth Forecast",
                "text":  "What exact percentage did the Bank of England forecast for UK GDP growth in 2025 in the February 2025 Monetary Policy Report?"
            },
            {
                "id":    "Q2",
                "topic": "Inflation Forecast",
                "text":  "What was the MPC's precise CPI inflation forecast for Q4 2025 published in the February 2025 report?"
            },
            {
                "id":    "Q3",
                "topic": "External Risk Factors",
                "text":  "Which specific external risk factor did the Bank of England's February 2025 report identify as the primary threat to the UK economic outlook?"
            }
        ]
    },

    "ipcc_ar6": {
        "id":          "ipcc_ar6",
        "title":       "IPCC — AR6 Synthesis Report: Climate Change 2023",
        "filename":    "documents/ipcc_ar6_syr_spm.pdf",
        "url":         "https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_SPM.pdf",
        "topic":       "Climate / Environment",
        "description": "The UN's definitive 2023 assessment of climate change science, risks, and responses",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Observed Warming",
                "text":  "According to the IPCC AR6 Synthesis Report, what was the exact global surface temperature increase above pre-industrial levels recorded for the period 2011-2020?"
            },
            {
                "id":    "Q2",
                "topic": "Emissions Threshold",
                "text":  "What specific remaining carbon budget in GtCO2 does the IPCC AR6 report state is left to limit warming to 1.5°C with a 50% probability?"
            },
            {
                "id":    "Q3",
                "topic": "Vulnerable Populations",
                "text":  "How many people does the IPCC AR6 Synthesis Report estimate currently live in contexts highly vulnerable to climate change?"
            }
        ]
    },

    "who_health_stats": {
        "id":          "who_health_stats",
        "title":       "WHO — World Health Statistics 2024",
        "filename":    "documents/who_health_stats_2024.pdf",
        "url":         "https://iris.who.int/bitstream/handle/10665/376869/9789240094703-eng.pdf",
        "topic":       "Healthcare / Global Health",
        "description": "WHO annual compilation of global health indicators and SDG progress",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Life Expectancy Impact",
                "text":  "According to the WHO World Health Statistics 2024, what was the specific reduction in global life expectancy caused by the COVID-19 pandemic between 2019 and 2021?"
            },
            {
                "id":    "Q2",
                "topic": "Malaria Vaccine Impact",
                "text":  "What percentage reduction in all-cause child mortality did the WHO report attribute to malaria vaccine introduction in the 2024 World Health Statistics report?"
            },
            {
                "id":    "Q3",
                "topic": "Maternal Mortality",
                "text":  "What was the exact global maternal mortality ratio (MMR) per 100,000 live births reported in the WHO World Health Statistics 2024?"
            }
        ]
    },

    "mckinsey_ai_2025": {
        "id":          "mckinsey_ai_2025",
        "title":       "McKinsey — State of AI 2025 (November)",
        "filename":    "documents/mckinsey_state_of_ai_2025.pdf",
        "url":         "https://www.mckinsey.com/~/media/mckinsey/business%20functions/quantumblack/our%20insights/the%20state%20of%20ai/november%202025/the-state-of-ai-2025-agents-innovation_cmyk-v1.pdf",
        "topic":       "Technology / AI Strategy",
        "description": "McKinsey's annual survey on enterprise AI adoption, agents, and value capture",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Enterprise AI Adoption",
                "text":  "According to McKinsey's State of AI November 2025 report, what exact percentage of organisations reported regular AI use in at least one business function?"
            },
            {
                "id":    "Q2",
                "topic": "EBIT Impact",
                "text":  "What specific percentage of survey respondents in McKinsey's November 2025 AI report said their organisation was reporting EBIT impact at the enterprise level from AI?"
            },
            {
                "id":    "Q3",
                "topic": "Agentic AI Scaling",
                "text":  "What percentage of respondents in McKinsey's November 2025 State of AI report said their organisations were scaling an agentic AI system in at least one business function?"
            }
        ]
    },

    "nist_ai_rmf": {
        "id":          "nist_ai_rmf",
        "title":       "NIST — AI Risk Management Framework 1.0 (2023)",
        "filename":    "documents/nist_ai_rmf_1_0.pdf",
        "url":         "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
        "topic":       "Governance / AI Risk",
        "description": "The US government's official framework for managing AI risks in enterprise contexts",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Core Functions",
                "text":  "What are the exact four core functions of the NIST AI Risk Management Framework 1.0, and what does each function address?"
            },
            {
                "id":    "Q2",
                "topic": "Trustworthy AI Properties",
                "text":  "According to NIST AI RMF 1.0, what are the specific characteristics listed as properties of trustworthy AI systems?"
            },
            {
                "id":    "Q3",
                "topic": "AI Risk Categories",
                "text":  "What specific categories of AI risk does NIST AI RMF 1.0 identify as primary dimensions of potential harm from AI systems?"
            }
        ]
    },

    "anthropic_rsp": {
        "id":          "anthropic_rsp",
        "title":       "Anthropic — Responsible Scaling Policy (2024)",
        "filename":    "documents/anthropic_rsp_2024.pdf",
        "url":         "https://www-cdn.anthropic.com/1adf000c8f675958c2ee23805d91aaade1cd4613/responsible-scaling-policy.pdf",
        "topic":       "AI Safety / Policy",
        "description": "Anthropic's framework for evaluating and deploying frontier AI models safely",
        "questions": [
            {
                "id":    "Q1",
                "topic": "AI Safety Levels",
                "text":  "What specific AI Safety Levels does Anthropic's Responsible Scaling Policy define, and what capability thresholds trigger each level?"
            },
            {
                "id":    "Q2",
                "topic": "Evaluation Commitments",
                "text":  "According to Anthropic's RSP, what specific evaluation commitments must be met before deploying a model at each safety level?"
            },
            {
                "id":    "Q3",
                "topic": "Containment Measures",
                "text":  "What exact containment and security measures does Anthropic's Responsible Scaling Policy require for models classified at ASL-3?"
            }
        ]
    },

    "imf_world_economic": {
        "id":          "imf_world_economic",
        "title":       "IMF — World Economic Outlook, October 2024",
        "filename":    "documents/imf_weo_oct2024.pdf",
        "url":         "https://www.imf.org/en/Publications/WEO/Issues/2024/10/22/world-economic-outlook-october-2024",
        "topic":       "Economics / Global Markets",
        "description": "IMF's bi-annual global economic growth forecasts and risk assessment",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Global Growth Forecast",
                "text":  "What exact global GDP growth rate did the IMF forecast for 2025 in its October 2024 World Economic Outlook report?"
            },
            {
                "id":    "Q2",
                "topic": "Inflation Projections",
                "text":  "What specific global inflation rate did the IMF project for 2025 in the October 2024 World Economic Outlook?"
            },
            {
                "id":    "Q3",
                "topic": "Downside Risks",
                "text":  "Which specific downside risks did the IMF identify as the most significant threats to the global economic outlook in October 2024?"
            }
        ]
    },

    "owasp_llm_top10": {
        "id":          "owasp_llm_top10",
        "title":       "OWASP — Top 10 for LLM Applications 2025",
        "filename":    "documents/owasp_llm_top10_2025.pdf",
        "url":         "https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-2025-v1.0.1.pdf",
        "topic":       "Cybersecurity / AI Risk",
        "description": "The definitive security vulnerability ranking for enterprise LLM deployments",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Top Vulnerability",
                "text":  "What is the number one ranked vulnerability in the OWASP Top 10 for LLM Applications 2025, and what specific attack vector does it describe?"
            },
            {
                "id":    "Q2",
                "topic": "Prompt Injection",
                "text":  "How does the OWASP LLM Top 10 2025 define and categorise prompt injection attacks, and what specific mitigation strategies does it recommend?"
            },
            {
                "id":    "Q3",
                "topic": "Supply Chain Risk",
                "text":  "What specific LLM supply chain vulnerabilities does OWASP identify in the 2025 edition, and what rank does this category hold?"
            }
        ]
    },

    "un_sdg_progress": {
        "id":          "un_sdg_progress",
        "title":       "UN — Sustainable Development Goals Report 2024",
        "filename":    "documents/un_sdg_report_2024.pdf",
        "url":         "https://unstats.un.org/sdgs/report/2024/The-Sustainable-Development-Goals-Report-2024.pdf",
        "topic":       "Policy / Global Development",
        "description": "Annual UN progress report across all 17 SDGs with country-level data",
        "questions": [
            {
                "id":    "Q1",
                "topic": "SDG Progress",
                "text":  "According to the UN SDG Report 2024, what percentage of SDG targets are currently on track to be achieved by 2030?"
            },
            {
                "id":    "Q2",
                "topic": "Poverty Figures",
                "text":  "What specific number of people does the UN SDG Report 2024 estimate are still living in extreme poverty globally?"
            },
            {
                "id":    "Q3",
                "topic": "Education Gap",
                "text":  "What exact figures does the UN SDG Report 2024 cite for the global learning poverty rate and how does this compare to pre-pandemic levels?"
            }
        ]
    },

    "bis_annual_report": {
        "id":          "bis_annual_report",
        "title":       "BIS — Annual Economic Report 2024",
        "filename":    "documents/bis_annual_report_2024.pdf",
        "url":         "https://www.bis.org/publ/arpdf/ar2024e.pdf",
        "topic":       "Finance / Banking Regulation",
        "description": "Bank for International Settlements annual assessment of global financial stability",
        "questions": [
            {
                "id":    "Q1",
                "topic": "Inflation Assessment",
                "text":  "What specific assessment does the BIS 2024 Annual Economic Report make about the progress of disinflation globally, and what risks does it highlight?"
            },
            {
                "id":    "Q2",
                "topic": "Financial Stability Risks",
                "text":  "What exact financial stability risks does the BIS 2024 Annual Report identify as most pressing for the global banking system?"
            },
            {
                "id":    "Q3",
                "topic": "Central Bank Policy",
                "text":  "What specific recommendations does the BIS 2024 Annual Report make regarding central bank policy frameworks in a post-pandemic environment?"
            }
        ]
    }

}

# ── Helper Functions ───────────────────────────────────────────────────────────

def list_documents():
    """Print the document menu for user selection."""
    print("\n" + "=" * 65)
    print("AVAILABLE DOCUMENTS")
    print("=" * 65)
    for i, (key, doc) in enumerate(DOCUMENT_REGISTRY.items(), 1):
        print(f"\n  [{i}] {doc['title']}")
        print(f"       Topic: {doc['topic']}")
        print(f"       {doc['description']}")
    print("\n" + "=" * 65)


def select_document() -> dict:
    """
    Interactive document selector.
    Returns the selected document config dict.
    """
    list_documents()
    keys = list(DOCUMENT_REGISTRY.keys())

    while True:
        try:
            choice = input("\nSelect a document [1-10]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(keys):
                selected = DOCUMENT_REGISTRY[keys[idx]]
                print(f"\nSelected: {selected['title']}")
                print(f"File:     {selected['filename']}")
                print(f"Topic:    {selected['topic']}")
                return selected
            else:
                print(f"Please enter a number between 1 and {len(keys)}.")
        except ValueError:
            print("Please enter a valid number.")


def get_document_by_id(doc_id: str) -> dict:
    """
    Get document config by ID string.
    Useful for non-interactive runs and testing.
    Example: get_document_by_id('boe_mpr')
    """
    if doc_id not in DOCUMENT_REGISTRY:
        raise ValueError(
            f"Document '{doc_id}' not found. "
            f"Available: {list(DOCUMENT_REGISTRY.keys())}"
        )
    return DOCUMENT_REGISTRY[doc_id]


def get_download_instructions():
    """Print download instructions for all documents."""
    print("\n" + "=" * 65)
    print("DOCUMENT DOWNLOAD INSTRUCTIONS")
    print("Save all files to the documents/ folder before running the lab.")
    print("=" * 65)
    for doc in DOCUMENT_REGISTRY.values():
        print(f"\n{doc['title']}")
        print(f"  Save as: {doc['filename']}")
        print(f"  URL:     {doc['url']}")
    print()


if __name__ == "__main__":
    # Run directly to see the full registry and download links
    get_download_instructions()