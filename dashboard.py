from flask import Flask, render_template, request, send_file, jsonify
import os
import re
from huggingface_hub import InferenceClient
import io
from fpdf import FPDF
import pandas as pd

app = Flask(__name__)

# ─────────────────────────────────────────────
# HF Inference API Client Setup
# ─────────────────────────────────────────────
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("❌ HF_TOKEN not set. Add it in Render → Environment tab.")

# Using Mistral 7B Instruct — free, reliable, great at structured instructions
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"

client = InferenceClient(
    model=MODEL_ID,
    token=HF_TOKEN
)
print(f"✅ Connected to Hugging Face Inference API ({MODEL_ID})")

# Global variable to keep the last scenario report
last_scenario_report = None

# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a helpful technical log analysis and troubleshooting expert.\n"
    "When given a log or error message, you:\n"
    "1) Classify the log type (INFO, WARN, ERROR). Sometimes it is present in the log itself.\n"
    "2) Provide an explanation.\n"
    "3) List possible root causes.\n"
    "4) List troubleshooting steps.\n"
    "Use clear markdown sections:\n"
    "**Log Type:**\n"
    "**Explanation:**\n"
    "**Possible Root Causes:**\n"
    "**Troubleshooting Steps:**\n"
)

SCENARIO_PROMPT = (
    "You are a cybersecurity expert specializing in incident analysis.\n"
    "Given a large collection of logs (e.g., 200 lines) describing a suspected crash or attack scenario:\n"
    "- Summarize the overall incident.\n"
    "- Identify the main causes and contributing factors.\n"
    "- Provide a clear narrative of the sequence of events.\n"
    "- Suggest recommended actions and mitigations.\n"
    "- Estimate the severity and potential impact.\n"
    "Write the response as a structured report in professional language, "
    "suitable for inclusion in an incident report document."
)

# ─────────────────────────────────────────────
# Helper: Call HF Inference API
# ─────────────────────────────────────────────
def call_llm(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    """
    Sends a chat completion request to HF Inference API (Mistral 7B).
    Uses proper system/user roles for best instruction-following.
    Retries once on 503 cold-start.
    """
    import time
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_message}
    ]
    for attempt in range(2):
        try:
            response = client.chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.3,
                top_p=0.9
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e)
            if "503" in error_str and attempt == 0:
                print("⚠️ Model cold-starting. Retrying in 20s...")
                time.sleep(20)
            else:
                print(f"❌ API Error: {error_str}")
                return f"⚠️ API Error: {error_str}"
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
                user_message=f"Log or error message:\n{log_text}",
                max_tokens=400
            )
            print("🔹 Model output:", raw_text)

            log_type    = re.search(r"\*\*Log Type:\*\*\s*(.+)", raw_text)
            explanation = re.search(r"\*\*Explanation:\*\*\s*(.*?)\n\*\*", raw_text, re.DOTALL)
            causes      = re.search(r"\*\*Possible Root Causes:\*\*\s*(.*?)\n\*\*", raw_text, re.DOTALL)
            steps       = re.search(r"\*\*Troubleshooting Steps:\*\*\s*(.*)", raw_text, re.DOTALL)

            result = {
                "log_type":              log_type.group(1).strip()    if log_type    else "UNKNOWN",
                "explanation":           explanation.group(1).strip() if explanation else "",
                "possible_root_causes":  causes.group(1).strip()      if causes      else "UNKNOWN",
                "troubleshooting_steps": steps.group(1).strip()       if steps       else ""
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
                max_tokens=700
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