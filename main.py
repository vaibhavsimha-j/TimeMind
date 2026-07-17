# -------------------------
# TimeMind
# -------------------------

from google import genai
import os
import pandas as pd
from fpdf import FPDF

# -------------------------
# Groq API Setup
# -------------------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-flash-latest"

# -------------------------
# Memory
# -------------------------
memory = {
    "last_generated": None,
    "timetable_details": ""
}

# -------------------------
# Timetable Generator
# -------------------------
def generate_timetable(single_line_input):
    prompt = f"""
You are a smart timetable generator. Generate a weekly timetable in Markdown table format.

Details:
{single_line_input}

Rules:
1. Respect professor-subject associations.
2. Respect breaks.
3. One subject per room per slot.

Output: Markdown tables only.
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    timetable_md = response.choices[0].message.content
    memory["last_generated"] = timetable_md
    memory["timetable_details"] = single_line_input
    return timetable_md

# -------------------------
# Timetable Editor
# -------------------------
def update_timetable(edit_instruction):
    if memory["last_generated"] is None:
        return "No timetable in memory. Generate one first."

    prompt = f"""
You are a smart timetable editor. Current timetable:

{memory['last_generated']}

Apply this edit:

{edit_instruction}

Rules:
- Respect breaks.
- One subject per room per slot.

Output Markdown tables only.
"""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    updated_md = response.choices[0].message.content
    memory["last_generated"] = updated_md
    return updated_md

# -------------------------
# Markdown to Excel
# -------------------------
def markdown_to_excel(md_content, filename="timetable.xlsx"):
    lines = md_content.splitlines()
    
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        day_name = None
        table_lines = []

        for line in lines:
            line = line.strip()
            
            # Detect day headings
            if line.startswith("####"):
                # Save previous table if exists
                if day_name and table_lines:
                    header = [cell.strip() for cell in table_lines[0].split("|")[1:-1]]
                    rows = [[cell.strip() for cell in r.split("|")[1:-1]] for r in table_lines[2:]]
                    df = pd.DataFrame(rows, columns=header)
                    df.to_excel(writer, sheet_name=day_name[:31], index=False)
                    table_lines = []

                day_name = line.replace("####", "").strip()
            
            # Detect table lines
            elif line.startswith("|") and day_name:
                table_lines.append(line)
        
        # Save last table
        if day_name and table_lines:
            header = [cell.strip() for cell in table_lines[0].split("|")[1:-1]]
            rows = [[cell.strip() for cell in r.split("|")[1:-1]] for r in table_lines[2:]]
            df = pd.DataFrame(rows, columns=header)
            df.to_excel(writer, sheet_name=day_name[:31], index=False)

    print(f"Timetable saved as {filename}")
  
# -------------------------
# Markdown to PDF
# -------------------------
def markdown_to_pdf(markdown_text, filename="timetable.pdf"):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.set_font("Helvetica", size=8)
    
    line_height = pdf.font_size * 2.5
    col_widths = [30, 65, 65, 65, 65]  

    page_exists = False
    lines = markdown_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Day heading
        if line.startswith("###"):
            if not page_exists:
                pdf.add_page()
                page_exists = True
            else:
                pdf.add_page()

            pdf.set_font("Helvetica", 'B', 10)
            pdf.cell(0, line_height, line.replace("### ", ""), ln=True, align='C')
            pdf.ln(2)
            pdf.set_font("Helvetica", size=8)
            continue

        # Header row
        if line.startswith("| Time"):
            headers = [h.strip() for h in line.split("|")[1:-1]]
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], line_height, h, border=1, align='C')
            pdf.ln(line_height)
            continue

        # Table rows
        if line.startswith("|"):
            if not page_exists:
                pdf.add_page()
                page_exists = True

            cells = [c.strip() for c in line.split("|")[1:-1]]
            for i, cell in enumerate(cells):
                if len(cell) > 20:
                    cell = cell[:17] + "..."
                pdf.cell(col_widths[i], line_height, cell, border=1, align='C')
            pdf.ln(line_height)

    pdf.output(filename)
    print(f"PDF saved as {filename}")

# -------------------------
# Interactive Loop
# -------------------------
def interactive_agent():
    print("Welcome to TimeMind! Type 'exit' to quit.\n")
    
    while True:
        action = input("Do you want to [generate] a new timetable or [edit] the existing one?  or [exit] ?").strip().lower()
        if action == "exit":
            print("Thank you for using TimeMind, let your day be productive! ")
            break
        elif action == "generate":
            single_line_input = input(
                "Enter timetable details (Subjects-Professors, Days, Slots(xx:xx - yy:yy), Rooms, Breaks(xx:xx - yy:yy), Constraints) in simple format:\n"
            ).strip()
            timetable_md = generate_timetable(single_line_input)
            print("\nGenerated Timetable:\n")
            print(timetable_md)
        elif action == "edit":
            edit_instruction = input("Enter your edit instruction (natural language): ").strip()
            timetable_md = update_timetable(edit_instruction)
            print("\nUpdated Timetable:\n")
            print(timetable_md)
        else:
            print("Invalid option. Please type 'generate', 'edit', or 'exit'.")
            continue

        download = input(" Do you want to download the generated timetable? [excel/pdf/both/no]: ").strip().lower()
        if download in ("excel", "both"):
            markdown_to_excel(memory["last_generated"])
        if download in ("pdf", "both"):
            markdown_to_pdf(memory["last_generated"])

# -------------------------
# Run Agent
# -------------------------
if __name__ == "__main__":
    interactive_agent()