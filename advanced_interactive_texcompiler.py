import streamlit as st
import os
import subprocess
from datetime import datetime
import re
import base64
from streamlit_ace import st_ace
import tempfile

# Page config
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")
st.title("📄 Elsevier LaTeX Compiler")

# File path setup
script_dir = os.path.dirname(os.path.abspath(__file__))
manuscript_dir = os.path.join(script_dir, "manuscript")

if not os.path.exists(manuscript_dir):
    os.makedirs(manuscript_dir)
    st.error("❌ Created manuscript directory as it didn't exist. Please add your .tex file.")
    st.stop()

# Load first .tex file found
tex_files = [f for f in os.listdir(manuscript_dir) if f.endswith(".tex")]
if not tex_files:
    st.error("❌ No `.tex` file found in `manuscript/`. Please add your main .tex file.")
    st.stop()

tex_file_path = os.path.join(manuscript_dir, tex_files[0])

# Initialize session state
if 'tex_content' not in st.session_state:
    with open(tex_file_path, "r", encoding="utf-8") as f:
        st.session_state.tex_content = f.read()
if 'selected_line' not in st.session_state:
    st.session_state.selected_line = 0
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None
if 'compilation_log' not in st.session_state:
    st.session_state.compilation_log = ""

# Extract TOC from LaTeX with line numbers
def extract_toc_with_lines(content):
    toc = []
    lines = content.split('\n')
    pattern = re.compile(r'\\(section|subsection|subsubsection|chapter|part)\*?\s*{([^}]*)}')
    
    for line_num, line in enumerate(lines):
        match = pattern.search(line)
        if match:
            level = match.group(1)
            title = match.group(2)
            indent = {
                "part": 0,
                "chapter": 1,
                "section": 2,
                "subsection": 3,
                "subsubsection": 4
            }.get(level, 2)
            toc.append({
                "title": title,
                "line": line_num,
                "indent": indent,
                "level": level
            })
    return toc

# Compile LaTeX function
def compile_latex():
    try:
        with st.spinner("⏳ Compiling LaTeX..."):
            result = subprocess.run(
                ["latexmk", "-pdf", "-interaction=nonstopmode", tex_file_path],
                cwd=manuscript_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            st.session_state.compilation_log = result.stdout + result.stderr
            
            if result.returncode == 0:
                pdf_path = os.path.splitext(tex_file_path)[0] + ".pdf"
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.session_state.pdf_data = f.read()
                    return True
            return False
    except Exception as e:
        st.session_state.compilation_log = str(e)
        return False

# Main layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("✍️ LaTeX Editor")
    
    # Table of Contents
    toc_items = extract_toc_with_lines(st.session_state.tex_content)
    with st.expander("📚 Table of Contents", expanded=True):
        if toc_items:
            for item in toc_items:
                indent = "&nbsp;" * 4 * item["indent"]
                if st.button(f"{indent}▸ {item['title']}", key=f"toc_{item['line']}"):
                    st.session_state.selected_line = item["line"]
        else:
            st.info("No sections found in the document.")
    
    # Editor with line highlighting
    editor_args = {
        "value": st.session_state.tex_content,
        "language": "latex",
        "theme": "monokai",
        "key": "tex_editor",
        "height": 600,
        "font_size": 14,
        "wrap": True
    }
    
    edited_tex = st_ace(**editor_args)
    
    # Update content if changed
    if edited_tex != st.session_state.tex_content:
        st.session_state.tex_content = edited_tex
        with open(tex_file_path, "w", encoding="utf-8") as f:
            f.write(edited_tex)
    
    # Compilation controls
    if st.button("🛠 Compile LaTeX"):
        if compile_latex():
            st.success("✅ Compilation successful!")
        else:
            st.error("❌ Compilation failed. Check logs below.")
        
        with st.expander("Compilation Log"):
            st.text(st.session_state.compilation_log)

with col2:
    st.subheader("📄 PDF Preview")
    
    if st.session_state.pdf_data:
        b64_pdf = base64.b64encode(st.session_state.pdf_data).decode("utf-8")
        pdf_display = f"""
        <iframe src="data:application/pdf;base64,{b64_pdf}#toolbar=1&navpanes=1&scrollbar=1" 
                width="100%" height="600" type="application/pdf"></iframe>
        """
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        st.download_button(
            "📥 Download PDF",
            st.session_state.pdf_data,
            file_name="document.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Compile the document to view PDF preview.")

# JavaScript for cursor positioning
if st.session_state.selected_line > 0:
    js_code = f"""
    <script>
        setTimeout(() => {{
            const editor = document.querySelector('.ace_editor').env.editor;
            editor.gotoLine({st.session_state.selected_line + 1});
            editor.focus();
        }}, 100);
    </script>
    """
    st.components.v1.html(js_code, height=0)

st.markdown("---")
st.markdown("""
**Instructions:**
1. Click any section in the Table of Contents to jump to it in the editor
2. Edit your LaTeX content
3. Click "Compile LaTeX" to generate PDF
4. View the PDF preview on the right

**Requirements:**
- `latexmk` must be installed on your system
- All LaTeX dependencies must be available
- Main .tex file must be in the `manuscript/` directory
""")
