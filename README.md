# Green-Efficiency-Calculator

    Use the .env file shared in the group. Keep it in the main folder.
    If you make any additions to the .env file, please let everyone know.
    Please don't commit the .env file. 
    If you are installing any additional libraries, please let the group know and put the library in the requirements.txt file.
    Commit your work to the main. Let the team know for errors
    Use your own branch and commit to the working-dev branch.
    Please commit regularly.

First Time Run :

Enter the following commands on Windows Shell

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

After first time Run :

Make sure to that your virtual environment is running.


# Agentic AI-based Green Energy Calculation System Overview

This agentic AI system revolves around a workflow that uses multiple agents to process and provide insights into green energy solutions. The agents handle different tasks like data normalization, efficiency auditing, recommendation composition, and impact estimation. Here's a breakdown of how each file works and how the flow happens between them:

## 1. **`intake_agent.py`**
   - **Purpose**: Normalizes input data, ensuring values are within reasonable ranges (e.g., wattage, hours of operation for appliances, tariff rates).
   - **Key Functions**:
     - `normalize(input_payload)`: 
       - Normalizes the input data.
       - Clamps values (like wattage, hours, etc.) using `guardrails.py`.
       - Reads default values from a YAML file.
       - Uses the `call_json()` function from `llm.py` to further process the data based on system prompts.
   - **Flow**: 
     - Normalized data is output and passed to other agents for further processing.

## 2. **`recommendation_composer.py`**
   - **Purpose**: Composes actionable recommendations based on normalized data and findings.
   - **Key Functions**:
     - `compose_recs(normalized, findings)`:
       - Generates up to 5 practical, low-cost actions based on normalized data and inefficiency findings.
       - Uses the `call_json()` function to interact with an LLM model to generate recommendations.
   - **Flow**:
     - Takes normalized data and inefficiency findings as input.
     - Outputs a set of actionable recommendations for implementation.

## 3. **`efficiency_auditor.py`**
   - **Purpose**: Audits the normalized data to identify inefficiencies and provides insights on areas for improvement.
   - **Key Functions**:
     - `audit(normalized)`:
       - Analyzes the normalized data for inefficiencies using an LLM.
       - Returns inefficiency findings in JSON format.
   - **Flow**: 
     - Receives normalized data as input.
     - Outputs inefficiency findings, which are sent to the `recommendation_composer.py` agent.

## 4. **`impact_estimator.py`**
   - **Purpose**: Estimates the impact of the recommendations (e.g., energy savings, cost reductions, payback periods).
   - **Key Functions**:
     - `estimate_impact(normalized, recs)`:
       - Calculates energy savings, cost savings, and payback periods for recommendations.
       - Sorts actions by payback period (quickest first).
   - **Flow**:
     - Takes normalized data and recommendations as input.
     - Outputs a detailed impact analysis, including savings, costs, and a plan for action.

## 5. **`llm.py`**
   - **Purpose**: Manages interactions with the OpenAI API for processing system and user prompts.
   - **Key Functions**:
     - `call_json()` and `call_text()`:
       - Used by other agents to send system and user prompts to the LLM.
       - Retrieves JSON responses or text-based summaries from the LLM, which are used for further processing.
   - **Flow**:
     - Acts as a bridge between system prompts and LLM, enabling agents to interact with the model.

## 6. **`guardrails.py`**
   - **Purpose**: Contains functions to clamp and validate input values, ensuring they are within sensible bounds.
   - **Key Functions**:
     - `clamp()`, `clamp_hours()`, `clamp_watts()`, etc.:
       - Ensures values like wattage, hours, and costs are within valid ranges before being processed by other agents.
   - **Flow**:
     - Used throughout the agents, especially in `intake_agent.py`, to clean and validate input data.

## 7. **`workflow.py`**
   - **Purpose**: Orchestrates the workflow by initiating the process with normalized data.
   - **Key Functions**:
     - `run_workflow(input_payload)`:
       - Starts the process by normalizing the input data using `intake_agent.py`.
   - **Flow**:
     - The workflow begins by normalizing the input data.
     - The processed data is then passed to other agents for auditing, recommendation composition, and impact estimation.

## Overall Flow:
1. **Input Payload**: The workflow begins by sending the raw input data (`input_payload`) to the `run_workflow()` function in `workflow.py`.
2. **Normalization**: The input data is normalized by `intake_agent.py` to ensure it is consistent and within reasonable ranges.
3. **Efficiency Audit**: The normalized data is analyzed for inefficiencies by `efficiency_auditor.py`.
4. **Recommendation Composition**: Based on inefficiency findings, `recommendation_composer.py` generates low-cost, practical actions for implementation.
5. **Impact Estimation**: The impact of the recommendations (e.g., energy savings, cost reductions, payback periods) is calculated by `impact_estimator.py`.
6. **Final Output**: The system outputs actionable insights, savings estimates, and a clear action plan.

---

This flow ensures that each step is handled in an organized manner, with each agent performing a specific task and interacting with the others to produce valuable results for the user.
