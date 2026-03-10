from flask import Flask, render_template, request, send_file, jsonify
import os
import re
import requests
import io
from fpdf import FPDF
import pandas as pd

app = Flask(__name__)

# ─────────────────────────────────────────────
# OpenRouter API Setup
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("❌ OPENROUTER_API_KEY not set. Add it in Render → Environment tab.")

# Free models on OpenRouter — no approval, no gating, no credits needed
# mistralai/mistral-7b-instruct:free is reliable and fast
MODEL_ID = "openrouter/auto"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

print(f"✅ Using OpenRouter (model={MODEL_ID})")

# Global variable to keep the last scenario report
last_scenario_report = None

# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a helpful technical log analysis and troubleshooting expert.\n"
    "When given a log or error message, you:\n"
    "1) Classify the log type (INFO, WARN, or ERROR).\n"
    "2) Provide a clear explanation of what the log means.\n"
    "3) List the most likely root causes.\n"
    "4) List actionable troubleshooting steps.\n\n"
    "IMPORTANT: Always respond using EXACTLY these four section headers, "
    "each on its own line with no extra text before the first one:\n"
    "**Log Type:**\n"
    "**Explanation:**\n"
    "**Possible Root Causes:**\n"
    "**Troubleshooting Steps:**\n"
)

SCENARIO_PROMPT = (
    "You are a cybersecurity expert specializing in incident analysis.\n"
    "Given a large collection of logs describing a suspected crash or attack scenario:\n"
    "- Summarize the overall incident.\n"
    "- Identify the main causes and contributing factors.\n"
    "- Provide a clear narrative of the sequence of events.\n"
    "- Suggest recommended actions and mitigations.\n"
    "- Estimate the severity and potential impact.\n"
    "Write the response as a structured report in professional language, "
    "suitable for inclusion in an incident report document."
)

# ─────────────────────────────────────────────
# Helper: Robust section extractor
# ─────────────────────────────────────────────
def extract_section(pattern, text, default=""):
    """Extract a section using lookahead regex — handles blank lines and varied spacing."""
    m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else default


# ─────────────────────────────────────────────
# Helper: Call OpenRouter API
# ─────────────────────────────────────────────
def call_llm(system_prompt: str, user_message: str, max_tokens: int = 600) -> str:
    """
    Sends a chat completion request to OpenRouter.
    Retries once on 503 / rate-limit errors.
    """
    import time

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://loganalyzer.onrender.com",  # optional but recommended by OpenRouter
        "X-Title": "Log Analyzer"                            # shows up in OpenRouter dashboard
    }

    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "top_p": 0.9
    }

    for attempt in range(2):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.exceptions.HTTPError as e:
            status = response.status_code
            if status in (429, 503) and attempt == 0:
                print(f"⚠️ Rate limit / server busy (HTTP {status}). Retrying in 15s...")
                time.sleep(15)
            else:
                err_body = ""
                try:
                    err_body = response.json().get("error", {}).get("message", str(e))
                except Exception:
                    err_body = str(e)
                print(f"❌ API Error {status}: {err_body}")
                return f"⚠️ API Error {status}: {err_body}"
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return f"⚠️ Unexpected error: {str(e)}"

    return "⚠️ Model unavailable after retry. Please try again shortly."


# ─────────────────────────────────────────────
# Health check — Render pings this to confirm app is alive
# ─────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        log_text = request.form.get("log_input", "").strip()
        if not log_text:
            result = {"error": "⚠️ Please enter a log message."}
        else:
            print("\n🔹 Single log analysis...")
            raw_text = call_llm(
                system_prompt=SYSTEM_PROMPT,
                user_message=f"Analyse this log or error message:\n{log_text}",
                max_tokens=600
            )
            print("🔹 Model output:", raw_text)

            log_type    = extract_section(
                r"\*\*Log Type:\*\*\s*(.+?)(?=\n\*\*|\Z)",
                raw_text, "UNKNOWN"
            )
            explanation = extract_section(
                r"\*\*Explanation:\*\*\s*(.*?)(?=\n\*\*Possible Root Causes:|\Z)",
                raw_text, "No explanation available."
            )
            causes      = extract_section(
                r"\*\*Possible Root Causes:\*\*\s*(.*?)(?=\n\*\*Troubleshooting Steps:|\Z)",
                raw_text, "No root causes identified."
            )
            steps       = extract_section(
                r"\*\*Troubleshooting Steps:\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
                raw_text, "No troubleshooting steps available."
            )

            result = {
                "log_type":              log_type,
                "explanation":           explanation,
                "possible_root_causes":  causes,
                "troubleshooting_steps": steps,
                "raw":                   raw_text
            }

    return render_template("index.html", result=result)


@app.route("/report", methods=["GET", "POST"])
def report():
    global last_scenario_report
    result = None
    if request.method == "POST":
        log_text = request.form.get("log_input", "").strip()
        if not log_text:
            result = {"error": "⚠️ Please enter Network Crash logs."}
        else:
            print("\n🔹 Scenario report generation...")
            raw_report = call_llm(
                system_prompt=SCENARIO_PROMPT,
                user_message=f"Logs:\n{log_text}",
                max_tokens=800
            )
            print("🔹 Scenario report:", raw_report)
            last_scenario_report = raw_report
            result = {"report": raw_report}

    return render_template("report.html", result=result)


@app.route("/visual", methods=["GET", "POST"])
def visualize():
    log_data   = []
    total_logs = 0
    error      = None

    if request.method == "POST":
        log_file = request.files.get("logfile")
        if not log_file or log_file.filename == "":
            error = "⚠️ Please upload a CSV file."
        else:
            try:
                df = pd.read_csv(log_file)
                if not {"log", "log_type"}.issubset(df.columns):
                    error = "CSV must contain 'log' and 'log_type' columns."
                else:
                    df = df.dropna(subset=["log"])
                    total_logs = len(df)
                    grouped = df.groupby(["log", "log_type"]).size().reset_index(name="count")
                    color_map = {"ERROR": "red", "WARN": "orange", "INFO": "green"}
                    for _, row in grouped.iterrows():
                        log_type = row["log_type"].upper()
                        log_data.append({
                            "log":   row["log"],
                            "count": int(row["count"]),
                            "type":  log_type,
                            "color": color_map.get(log_type, "gray")
                        })
            except Exception as e:
                error = f"⚠️ Failed to read CSV: {str(e)}"

    return render_template("visual.html", log_data=log_data, total_logs=total_logs, error=error)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/report/pdf")
def report_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Network Crash Log Report", ln=True, align="C")
    pdf.ln(5)

    if last_scenario_report:
        for para in last_scenario_report.split("\n\n"):
            clean = para.strip()
            if clean:
                pdf.multi_cell(0, 10, txt=clean)
                pdf.ln(3)
    else:
        pdf.multi_cell(0, 10, txt="No report available.\n\nPlease generate a report first.")

    pdf_bytes  = pdf.output(dest="S").encode("latin1")
    pdf_output = io.BytesIO(pdf_bytes)

    return send_file(
        pdf_output,
        download_name="report.pdf",
        as_attachment=False,
        mimetype="application/pdf"
    )


# ─────────────────────────────────────────────
# Entry point — for local testing only
# Render uses gunicorn defined in Procfile/Dockerfile
# ─────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)