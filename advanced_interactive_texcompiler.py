import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace

# Streamlit page configuration
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")

# Title and description
st.title("📄 Elsevier LaTeX Compiler")
st.write("Edit and compile a `.tex` file from the `manuscript` directory. The LaTeX content and table of contents are on the left, and the PDF preview (empty initially) is on the right.")

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

# Read initial .tex content
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
            indent = {"section": 0, "subsection": 20, "subsubsection": 40}[level]
            toc.append({"title": title, "line": i, "indent": indent})
    return toc

toc_items = extract_toc_lines(tex_content)

# Create two-column layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ Edit LaTeX File")
    
    # Table of Contents
    with st.expander("📚 Table of Contents", expanded=True):
        if toc_items:
            st.markdown("**Table of Contents**")
            for i, item in enumerate(toc_items):
                st.markdown(
                    f"<div style='margin-left: {item['indent']}px; font-weight: {'bold' if item['indent'] == 0 else 'normal'}'>"
                    f"<a href='javascript:void(0);' onclick='window.scrollTo(0, document.getElementById(\"ace_tex_editor\").offsetTop + {item['line'] * 20});'>"
                    f"{item['title']}</a></div>",
                    unsafe_allow_html=True
                )
        else:
            st.info("🛈 No sections found in LaTeX.")

    # LaTeX editor
    edited_tex = st_ace(
        value=tex_content,
        language="latex",
        theme="monokai",
        key="tex_editor",
        height=600,
        auto_update=True
    )

    # Save and compile options
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
            # Save edited content before compiling
            with open(tex_file_path, "w", encoding="utf-8") as f:
                f.write(edited_tex)
            
            # Compile with latexmk
            result = subprocess.run(
                ["latexmk", "-pdf", "-pdflatex=pdflatex", "-interaction=nonstopmode", tex_file_path],
                cwd=manuscript_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"
            if result.returncode == 0 and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                pdf_filename = f"compiled_{os.path.basename(os.path.splitext(tex_file_path)[0])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
        pdf_view = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600px"></iframe>'
        st.markdown(pdf_view, unsafe_allow_html=True)
        st.download_button("📥 Download PDF", pdf_data, file_name=pdf_filename, mime="application/pdf")
    else:
        st.info("🛈 PDF not compiled yet. Click **Compile LaTeX** or save with auto-compile.")

# Instructions
st.markdown("---")
st.markdown("""
**Instructions:**
1. Edit the LaTeX file in the left panel.
2. Click a section in the Table of Contents to scroll to it.
3. Save changes and compile (auto-compile optional).
4. View/download the PDF on the right.

📁 **Repository structure:**
```
latex_typesetting/
├── texcompiler.py
├── manuscript/
│   ├── paper.tex
│   ├── cas-sc.cls
│   └── references.bib  (optional)
├── figures/
│   └── graphical_abstract.png  (optional)
```

**Streamlit Cloud Setup:**
- `requirements.txt`:
  ```
  streamlit
  streamlit_ace
  ```
- `packages.txt`:
  ```
  texlive-full
  latexmk
  ```
""")
