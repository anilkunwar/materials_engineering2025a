import streamlit as st
import os
import subprocess
from datetime import datetime, timedelta
import re
import base64
from streamlit_ace import st_ace
from streamlit_tree_select import tree_select

# Streamlit page configuration
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")

# Title and description
st.title("📄 Elsevier LaTeX Compiler")
st.write("Edit and compile a `.tex` file from the `manuscript` directory. The LaTeX editor and hierarchical table of contents are on the left, with an interactive PDF preview on the right.")

# Initialize session state
if "highlight_line" not in st.session_state:
    st.session_state["highlight_line"] = None
if "last_compile" not in st.session_state:
    st.session_state["last_compile"] = None
if "last_edited_tex" not in st.session_state:
    st.session_state["last_edited_tex"] = ""

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

# Extract TOC for tree structure
def extract_toc_tree(content):
    toc = []
    pattern = re.compile(r'\\(section|subsection|subsubsection)\{([^}]*)\}')
    current_section = None
    current_subsection = None
    for i, line in enumerate(content.splitlines()):
        match = pattern.search(line)
        if match:
            level, title = match.group(1), match.group(2)
            node = {"label": title, "value": f"{level}_{i}", "line": i}
            if level == "section":
                current_section = node
                current_section["children"] = []
                toc.append(current_section)
            elif level == "subsection" and current_section:
                current_subsection = node
                current_subsection["children"] = []
                current_section["children"].append(current_subsection)
            elif level == "subsubsection" and current_subsection:
                current_subsection["children"].append(node)
    return toc

toc_tree = extract_toc_tree(tex_content)

# Create two-column layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ Edit LaTeX File")
    
    # Table of Contents
    with st.expander("📚 Table of Contents", expanded=True):
        if toc_tree:
            selected_nodes = tree_select(
                toc_tree,
                key="toc_tree",
                expand_on_click=True,
                show_expand_all=True
            )
            if selected_nodes["checked"]:
                selected_value = selected_nodes["checked"][0]
                selected_line = next((node["line"] for node in toc_tree if node["value"] == selected_value or any(child["value"] == selected_value for child in node.get("children", []) or any(grandchild["value"] == selected_value for child in node.get("children", []) for grandchild in child.get("children", [])))), None)
                if selected_line is not None:
                    st.session_state["highlight_line"] = selected_line
        else:
            st.info("🛈 No sections found in LaTeX.")

    # Go to Line dropdown
    st.write("Go to Line:")
    line_numbers = list(range(1, len(tex_content.splitlines()) + 1))
    selected_line = st.selectbox("Select line number", line_numbers, index=0, key="goto_line")
    if st.button("Go"):
        st.session_state["highlight_line"] = selected_line - 1

    # LaTeX editor with error annotations
    annotations = []
    if edited_tex := st.session_state.get("last_edited_tex", tex_content):
        # Basic syntax check for unmatched braces
        open_braces = edited_tex.count("{")
        close_braces = edited_tex.count("}")
        if open_braces != close_braces:
            annotations.append({
                "row": 0,
                "column": 0,
                "type": "error",
                "text": f"Unmatched braces: {open_braces} '{{' vs {close_braces} '}}'"
            })

    edited_tex = st_ace(
        value=tex_content,
        language="latex",
        theme="monokai",
        key="tex_editor",
        height=600,
        auto_update=True,
        annotations=annotations,
        highlight_lines=[st.session_state["highlight_line"]] if st.session_state["highlight_line"] is not None else []
    )

    # Save and compile options
    auto_compile = st.checkbox("🔁 Auto-compile after edits (500ms delay)", value=False)
    compile_triggered = False

    if st.button("💾 Save Changes"):
        with open(tex_file_path, "w", encoding="utf-8") as f:
            f.write(edited_tex)
        st.success("✅ Changes saved.")
        if auto_compile:
            compile_triggered = True

    if st.button("🛠 Compile LaTeX"):
        compile_triggered = True

    # Debounced auto-compilation
    if auto_compile and edited_tex != st.session_state["last_edited_tex"]:
        if st.session_state["last_compile"] is None or (datetime.now() - st.session_state["last_compile"]).total_seconds() > 0.5:
            compile_triggered = True
            st.session_state["last_edited_tex"] = edited_tex
            st.session_state["last_compile"] = datetime.now()

    pdf_data = None
    pdf_filename = None

    if compile_triggered:
        try:
            # Save edited content
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
        viewer_html = f"""
        <iframe src="https://mozilla.github.io/pdf.js/web/viewer.html?file=data:application/pdf;base64,{b64_pdf}"
                width="100%" height="600px"></iframe>
        """
        st.components.v1.html(viewer_html, height=600)
        st.download_button("📥 Download PDF", pdf_data, file_name=pdf_filename, mime="application/pdf")
    else:
        st.info("🛈 PDF not compiled yet. Click **Compile LaTeX** or enable auto-compile.")

# Instructions
st.markdown("---")
st.markdown("""
**Instructions:**
1. Edit the LaTeX file in the left panel.
2. Expand/collapse the Table of Contents to navigate sections; click to highlight lines.
3. Use "Go to Line" to jump to specific lines.
4. Save changes and compile (auto-compile optional with 500ms debounce).
5. View/download the interactive PDF on the right (supports zoom, thumbnails).

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
  streamlit_tree_select
  ```
- `packages.txt`:
  ```
  texlive-full
  latexmk
  ```
""")
