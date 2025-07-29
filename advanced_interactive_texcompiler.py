import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace

# Page config
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")
st.title("📄 Elsevier LaTeX Compiler")

# File path setup
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

if not os.path.exists(manuscript_dir):
    st.error("❌ `manuscript/` directory not found.")
    st.stop()

# Load first .tex file found
tex_file_path = next((os.path.join(manuscript_dir, f) for f in os.listdir(manuscript_dir) if f.endswith(".tex")), None)
if not tex_file_path:
    st.error("❌ No `.tex` file found in `manuscript/`.")
    st.stop()

with open(tex_file_path, "r", encoding="utf-8") as f:
    tex_content = f.read()

# Extract TOC from LaTeX
def extract_toc_lines(content):
    toc = []
    pattern = re.compile(r'\\(section|subsection|subsubsection)\{([^}]*)\}')
    for i, line in enumerate(content.splitlines()):
        match = pattern.search(line)
        if match:
            level, title = match.group(1), match.group(2)
            indent = {"section": 0, "subsection": 1, "subsubsection": 2}[level]
            toc.append({"title": title, "line": i, "indent": indent})
    return toc

toc_items = extract_toc_lines(tex_content)

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ Edit LaTeX File")

    selected_line = 0
    with st.expander("📚 Table of Contents", expanded=True):
        if toc_items:
            for i, item in enumerate(toc_items):
                if st.button(item["title"], key=f"toc_{i}"):
                    selected_line = item["line"]
        else:
            st.info("No sections found in LaTeX.")

    # Safe cursor_position handling
    try:
        editor_args = {
            "value": tex_content,
            "language": "latex",
            "theme": "monokai",
            "key": "tex_editor",
            "height": 600,
            "cursor_position": (selected_line, 0)
        }
    except Exception:
        editor_args = {
            "value": tex_content,
            "language": "latex",
            "theme": "monokai",
            "key": "tex_editor",
            "height": 600
        }

    edited_tex = st_ace(**editor_args)

    auto_compile = st.checkbox("🔁 Auto-compile after saving", value=False)
    compile_triggered = False

    if st.button("💾 Save Changes"):
        with open(tex_file_path, "w", encoding="utf-8") as f:
            f.write(edited_tex)
        st.success("✅ Changes saved.")
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
        st.download_button("📥 Download PDF", pdf_data, file_name=pdf_filename, mime="application/pdf")
    else:
        st.info("🛈 PDF not compiled yet. Click **Compile LaTeX** after saving.")

st.markdown("---")
st.markdown("""
**Instructions:**
1. Click a section in the Table of Contents to jump to it.
2. Edit your LaTeX file in the left panel.
3. Save and compile LaTeX.
4. View and download the PDF in the right panel.

📁 `manuscript/` should include:
- `.tex` file
- `cas-sc.cls` (or journal class)
- Images and `.bib` files
""")
