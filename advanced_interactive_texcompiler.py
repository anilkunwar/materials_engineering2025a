import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace

st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")
st.title("📄 Elsevier LaTeX Compiler")

# Get paths
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

# Validate manuscript folder
if not os.path.exists(manuscript_dir):
    st.error("❌ `manuscript/` directory not found.")
    st.stop()

# Locate .tex file
tex_file_path = None
for file in os.listdir(manuscript_dir):
    if file.endswith(".tex"):
        tex_file_path = os.path.join(manuscript_dir, file)
        break

if not tex_file_path:
    st.error("❌ No `.tex` file found in `manuscript/`.")
    st.stop()

# Load .tex content
with open(tex_file_path, "r", encoding="utf-8") as f:
    tex_content = f.read()

# Extract TOC entries with line numbers
def extract_toc_lines(content):
    toc = []
    lines = content.splitlines()
    pattern = re.compile(r'\\(section|subsection|subsubsection)\{([^}]*)\}')
    for i, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            level, title = match.group(1), match.group(2)
            indent = {"section": 0, "subsection": 1, "subsubsection": 2}[level]
            toc.append({"title": title, "line": i, "indent": indent})
    return toc

toc_entries = extract_toc_lines(tex_content)

# Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ Edit LaTeX File")

    # Sidebar-style TOC
    if toc_entries:
        toc_display = [f"{'  ' * t['indent']}{t['title']}" for t in toc_entries]
        toc_choice = st.radio("📚 Table of Contents", toc_display, index=0, key="toc_select")
        selected_line = toc_entries[toc_display.index(toc_choice)]['line']
    else:
        st.info("No sections found.")
        toc_choice = None
        selected_line = 0

    # Ace Editor
    edited_tex = st_ace(
        value=tex_content,
        language="latex",
        theme="monokai",
        key="tex_editor",
        height=600,
        show_gutter=True,
        wrap=True,
        annotations=[],
        readonly=False,
        font_size=14,
        tab_size=2,
        placeholder="Edit your LaTeX here...",
        cursor_position={"row": selected_line, "column": 0},  # jump to line
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

# Footer
st.markdown("---")
st.markdown("""
**Instructions:**
1. Edit the LaTeX file in the left panel.
2. Use the clickable Table of Contents to jump to sections.
3. Click "Save Changes" to write edits to the file.
4. Click "Compile LaTeX" or enable auto-compile to generate the PDF.
5. PDF will appear in the right panel and can be downloaded.

📁 Make sure the `manuscript/` folder contains:
- Your `.tex` file
- `cas-sc.cls` file
- Any images (`\\includegraphics`) or `.bib` file used
""")
