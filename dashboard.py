
from flask import Flask, render_template, request, send_file
import threading
import webbrowser
import os
import re
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    pipeline,
    BitsAndBytesConfig
)
from huggingface_hub import login
import io
from fpdf import FPDF

app = Flask(__name__)

# Global variable to keep the last scenario report
last_scenario_report = None

# Load HF token securely
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise RuntimeError("❌ HF_TOKEN not set. Run `set HF_TOKEN=hf_xxx...` first.")
login(HF_TOKEN)

# Check CUDA availability
if torch.cuda.is_available():
    device_name = torch.cuda.get_device_name(0)
    print(f"✅ CUDA is available. Using GPU: {device_name}")
else:
    print("⚠️ CUDA not available. The model will run on CPU.")

# Load Gemma 2B quantized
model_name = "google/gemma-2b-it"
print("🔹 Loading Gemma 2B 4-bit quantized...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype="bfloat16"
)

gemma_model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map={"": "cuda:0"} if torch.cuda.is_available() else {"": "cpu"}
)
gemma_tokenizer = AutoTokenizer.from_pretrained(model_name)

gemma_generator = pipeline(
    "text-generation",
    model=gemma_model,
    tokenizer=gemma_tokenizer,
)

# Single log analysis prompt
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

# Scenario-level prompt for multi-log reports
SCENARIO_PROMPT = (
    "You are a cybersecurity expert specializing in incident analysis.\n"
    "Given a large collection of logs (e.g., 200 lines) describing a suspected crash or attack scenario:\n"
    "- Summarize the overall incident.\n"
    "- Identify the main causes and contributing factors.\n"
    "- Provide a clear narrative of the sequence of events.\n"
    "- Suggest recommended actions and mitigations.\n"
    "- Estimate the severity and potential impact.\n"
    "Write the response as a structured report in professional language, suitable for inclusion in an incident report document."
)

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        log_text = request.form.get("log_input")
        if not log_text:
            result = {"error": "⚠️ Please enter a log message."}
        else:
            prompt = (
                f"{SYSTEM_PROMPT}\n\n"
                f"Log or error message:\n{log_text}\n\n"
                "Response:"
            )
            print("\n🔹 Sending prompt for single log analysis...")
            outputs = gemma_generator(
                prompt,
                max_new_tokens=400,
                temperature=0.3,
                do_sample=True,
                top_p=0.9
            )
            raw_text = outputs[0]["generated_text"][len(prompt):].strip()
            print("🔹 Raw model output:")
            print(raw_text)
            if not raw_text:
                print("⚠️ WARNING: Empty response from model.")

            # Extract sections
            log_type = re.search(r"\*\*Log Type:\*\*\s*(.+)", raw_text)
            explanation = re.search(r"\*\*Explanation:\*\*\s*(.*?)\n\*\*", raw_text, re.DOTALL)
            causes = re.search(r"\*\*Possible Root Causes:\*\*\s*(.*?)\n\*\*", raw_text, re.DOTALL)
            steps = re.search(r"\*\*Troubleshooting Steps:\*\*\s*(.*)", raw_text, re.DOTALL)

            result = {
                "log_type": log_type.group(1).strip() if log_type else "UNKNOWN",
                "explanation": explanation.group(1).strip() if explanation else "",
                "possible_root_causes": causes.group(1).strip() if causes else "UNKNOWN",
                "troubleshooting_steps": steps.group(1).strip() if steps else ""
            }

    return render_template("index.html", result=result)

@app.route("/report", methods=["GET", "POST"])
def report():
    global last_scenario_report
    result = None
    if request.method == "POST":
        log_text = request.form.get("log_input")
        if not log_text:
            result = {"error": "⚠️ Please enter Network Crash logs."}
        else:
            prompt = (
                f"{SCENARIO_PROMPT}\n\n"
                f"Logs:\n{log_text}\n\n"
                "Response:"
            )
            print("\n🔹 Sending prompt for scenario report generation...")
            outputs = gemma_generator(
                prompt,
                max_new_tokens=700,
                temperature=0.3,
                do_sample=True,
                top_p=0.9
            )
            raw_report = outputs[0]["generated_text"][len(prompt):].strip()
            print("🔹 Raw scenario report:")
            print(raw_report)
            if not raw_report:
                print("⚠️ WARNING: Empty scenario report response from model.")

            # Save the report globally
            last_scenario_report = raw_report
            result = {"report": raw_report}

    return render_template("report.html", result=result)
import pandas as pd
from collections import Counter
@app.route("/visual", methods=["GET", "POST"])
def visualize():
    log_data = []
    total_logs = 0

    if request.method == "POST":
        log_file = request.files.get("logfile")
        if log_file:
            # Read CSV with expected column names
            df = pd.read_csv(log_file)

            required_columns = {"log", "log_type"}
            if not required_columns.issubset(df.columns):
                return "CSV must contain 'log' and 'log_type' columns.", 400

            # Drop empty logs
            df = df.dropna(subset=["log"])
            total_logs = len(df)

            # Count duplicates of the same log message
            grouped = df.groupby(["log", "log_type"]).size().reset_index(name="count")

            # Assign color based on log_type
            color_map = {
                "ERROR": "red",
                "WARN": "orange",
                "INFO": "green"
            }

            for _, row in grouped.iterrows():
                log_text = row["log"]
                log_type = row["log_type"].upper()
                color = color_map.get(log_type, "gray")  # fallback for unknown types

                log_data.append({
                    "log": log_text,
                    "count": int(row["count"]),
                    "type": log_type,
                    "color": color
                })

    return render_template("visual.html", log_data=log_data, total_logs=total_logs)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/report/pdf")
def report_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Network Crash Log Report", ln=True, align="C")
    
    if last_scenario_report:
        # Split into paragraphs
        paragraphs = last_scenario_report.split("\n\n")
        for para in paragraphs:
            pdf.multi_cell(0, 10, txt=para.strip())
            pdf.ln()
    else:
        pdf.multi_cell(0, 10, txt="No report available.\n\nPlease generate a report first.")

    # Use dest='S' to get PDF as bytes string
    pdf_bytes = pdf.output(dest="S").encode("latin1")
    pdf_output = io.BytesIO(pdf_bytes)

    return send_file(
        pdf_output,
        download_name="report.pdf",
        as_attachment=False,
        mimetype="application/pdf"
    )

def open_browser():
    try:
        webbrowser.get(using='windows-default').open("http://127.0.0.1:5000/")
    except:
        try:
            webbrowser.get("edge").open("http://127.0.0.1:5000/")
        except:
            print("⚠️ Could not open Edge. Please open http://127.0.0.1:5000/ manually.")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)
