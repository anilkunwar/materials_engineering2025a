import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace

# Streamlit page config
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")

st.title("📄 Elsevier LaTeX Compiler")

# Get script directory and manuscript dir
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

# Check manuscript folder
if not os.path.exists(manuscript_dir):
    st.error("❌ `manuscript/` directory not found.")
    st.stop()

# Find a .tex file
tex_file_path = None
for file in os.listdir(manuscript_dir):
    if file.endswith(".tex"):
        tex_file_path = os.path.join(manuscript_dir, file)
        break

if not tex_file_path:
    st.error("❌ No `.tex` file found in `manuscript/`.")
    st.stop()

# Read .tex content
with open(tex_file_path, "r", encoding="utf-8") as f:
    tex_content = f.read()

# Extract TOC
def extract_toc(content):
    toc = []
    pattern = re.compile(r'\\(section|subsection|subsubsection)\{([^}]*)\}')
    for match in pattern.finditer(content):
        level, title = match.group(1), match.group(2)
        indent = {"section": 0, "subsection": 20, "subsubsection": 40}[level]
        toc.append((title, indent))
    return toc

toc_items = extract_toc(tex_content)

# App layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ Edit LaTeX File")

    with st.expander("📚 Table of Contents", expanded=True):
        if toc_items:
            for title, indent in toc_items:
                st.markdown(f"<div style='margin-left: {indent}px'>{title}</div>", unsafe_allow_html=True)
        else:
            st.info("No sections found.")

    # Ace Editor (syntax-highlighted)
    edited_tex = st_ace(
        value=tex_content,
        language="latex",
        theme="monokai",
        key="tex_editor",
        height=600
    )

    auto_compile = st.checkbox("🔁 Auto-compile after saving", value=False)

    compile_triggered = False

    if st.button("💾 Save Changes"):
        with open(tex_file_path, "w", encoding="utf-8") as f:
            f.write(edited_tex)
        st.success("✅ Changes saved to file.")
        if auto_compile:
            compile_triggered = True

    if st.button("🛠 Compile LaTeX"):
        compile_triggered = True

    pdf_data = None
    pdf_filename = None

    if compile_triggered:
        try:
            result = subprocess.run(
                ["latexmk", "-pdf", "-interaction=nonstopmode", tex_file_path],
                cwd=manuscript_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"

            if result.returncode == 0 and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_filename = f"compiled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                st.success("✅ PDF compiled successfully.")
            else:
                st.error("❌ Compilation failed.")
                st.text_area("latexmk Output", result.stdout + result.stderr, height=200)
        except subprocess.TimeoutExpired:
            st.error("⏳ Compilation timed out.")
        except Exception as e:
            st.error(f"⚠️ Error: {e}")

with col2:
    st.subheader("📄 PDF Preview")

    if pdf_data:
        b64_pdf = base64.b64encode(pdf_data).decode("utf-8")
        pdf_view = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600"></iframe>'
        st.markdown(pdf_view, unsafe_allow_html=True)

        st.download_button(
            label="📥 Download PDF",
            data=pdf_data,
            file_name=pdf_filename,
            mime="application/pdf"
        )
    else:
        st.info("🛈 PDF not compiled yet. Click **Compile LaTeX** after saving.")

# Footer instructions
st.markdown("---")
st.markdown("""
**Instructions:**
1. Edit the LaTeX file in the left panel.
2. Click "Save Changes" to write edits to the file.
3. Click "Compile LaTeX" or enable auto-compile to generate the PDF.
4. PDF will appear in the right panel and can be downloaded.

📁 Make sure the `manuscript/` folder contains:
- Your `.tex` file
- `cas-sc.cls` file
- Any images (`\includegraphics`) or `.bib` file used
""")
