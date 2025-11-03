# Green-Efficiency-Calculator

## Agentic AI-based Green Energy Calculation System Overview

This agentic AI system revolves around a workflow that uses multiple agents to process and provide insights into green energy solutions. The agents handle different tasks like data normalization, efficiency auditing, recommendation composition, impact estimation and policy management. This demonstrates a multi-agentic workflow with the association of an LLM, multiple utitlies and validation schema to generate a viable output for the user to act upon.

## Quick Start
    -Requirements
    Python 3.10+
    
    -Setup virtual environment
    python -m venv .venv
    source .venv/bin/activate   # or .venv\Scripts\activate on Windows

    -Install dependencies
    pip install -r requirements.txt

    -Configurations
    Create a .env file on the root and set the following keys using your private 
    OPENAI_API_KEY=
    MODEL_NAME=gpt-4o-mini
    FIREBASE_API_KEY=
    FIREBASE_AUTH_DOMAIN=
    FIREBASE_PROJECT_ID=
    FIREBASE_DATABASE_URL=
    FIREBASE_STORAGE_BUCKET=
    GOOGLE_CLIENT_ID=
    GOOGLE_CLIENT_SECRET=

    -Run
    streamlit run app.py

## Core Workflow of this Project

Intake Agent - Normalizes and validates input data.
Efficiency Auditor - Identifies inefficiencies via benchmarks + AI reasoning.
Recommendation Composer - Suggests practical, low-cost green improvements.
Impact Estimator - Quantifies savings and sustainability gains.
Policy Agent - Provides the ability for the user to set required policies like budget and payback periods

The workflow orchestrates five specialized agents working in sequence to analyze and optimize energy efficiency. The Intake Agent first validates and normalizes user data such as usage hours, wattage, and tariffs ensuring consistent inputs. The Efficiency Auditor benchmarks this data and identifies inefficiencies using analytical rules and LLM reasoning. The Recommendation Composer then generates prioritized, actionable improvements, while the Impact Estimator quantifies potential savings and payback periods. The Policy Agent enforces user-defined constraints such as budget limits and desired ROI windows. The central workflow coordinates these agents to deliver a structured, actionable output via the user interface.

## Key Features
Multi-agent orchestration with AI-assisted reasoning.
Real-time efficiency auditing and recommendation synthesis.
Configurable policy agent for budget/payback thresholds.
Streamlit front-end for interactive user analysis.

