flowchart TB
    U[User (Streamlit UI)] --> A[app.py]
    D[data/defaults.yaml] --> A
    ENV[(.env OPENAI_API_KEY)] --> A
    A -->|payload| W[workflow.run_workflow()]

    subgraph Agents
        N[intake_agent.normalize()]
        AU[efficiency_auditor.audit()]
        C[recommendation_composer.compose_recs()]
        E[impact_estimator.estimate_impact()]
    end

    W --> N
    N --> AU
    AU --> C
    N --> C
    C --> E
    N --> E

    subgraph Utils & Data
        GR[utils/guardrails.py<br/>clamp_*]
        LLM[utils/llm.py<br/>call_json/call_text]
        P1[prompts/intake_system.txt]
        P2[prompts/auditor_system.txt]
        P3[prompts/composer_system.txt]
        P4[prompts/impact_system.txt]
        DEF[data/defaults.yaml]
    end

    DEF --> N
    GR --> N
    LLM --> N
    LLM --> AU
    LLM --> C
    LLM --> E
    P1 --> N
    P2 --> AU
    P3 --> C
    P4 --> E

    E -->|plan:{ quick_wins, all_actions, totals, plan_text }| A
    W -->|{ input, findings, plan }| A

    A -->|render| QW[[Top 3 Quick Wins]]
    A -->|render| TAB[[All Actions Table]]
    A -->|render| TOT[[Totals (kWh/LKR per month)]]
    A -->|render & download| PLAN[[Action Plan (.md)]]
