import streamlit as st
import os
import subprocess
from datetime import datetime

# Streamlit page configuration
st.set_page_config(page_title="Elsevier LaTeX Compiler", layout="wide")

# Title and description
st.title("Elsevier LaTeX Compiler")
st.write("Compiles a `.tex` file from the `manuscript` directory (located in the same directory as this script) using latexmk. Ensure the `manuscript` directory contains a `.tex` file (e.g., `paper.tex`), `cas-sc.cls`, and optionally a `.bib` file and a `figures` directory with images (e.g., `figures/graphical_abstract.png`).")

# Get the directory of the current .py file
script_dir = os.path.dirname(os.path.abspath(__file__))

# Initialize variables
pdf_data = None
pdf_filename = None

# Compile button and processing logic
if st.button("Compile LaTeX"):
    try:
        # Locate the manuscript directory
        manuscript_dir = os.path.join(script_dir, "manuscript")
        if not os.path.exists(manuscript_dir):
            st.error("`manuscript` directory not found in the same directory as this script.")
        else:
            # Log files in manuscript directory for debugging
            manuscript_files = []
            for root, _, files in os.walk(manuscript_dir):
                for file in files:
                    manuscript_files.append(os.path.join(root, file))
            if manuscript_files:
                st.write("Files in manuscript directory:", manuscript_files)
            else:
                st.error("No files found in the `manuscript` directory.")

            # Search for a .tex file in the manuscript directory
            tex_file_path = None
            for file in os.listdir(manuscript_dir):
                if file.endswith(".tex"):
                    tex_file_path = os.path.join(manuscript_dir, file)
                    break
            if not tex_file_path:
                st.error("No `.tex` file found in the `manuscript` directory.")
            else:
                # Read .tex content for debugging
                with open(tex_file_path, "r", encoding="utf-8") as f:
                    tex_content = f.read()
                st.write(f"Content of {os.path.basename(tex_file_path)}:", tex_content)

                # Compile with latexmk
                try:
                    result = subprocess.run(
                        ["latexmk", "-pdf", "-pdflatex=pdflatex", "-interaction=nonstopmode", tex_file_path],
                        cwd=manuscript_dir,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    pdf_file_path = os.path.splitext(tex_file_path)[0] + ".pdf"
                    if result.returncode == 0 and os.path.exists(pdf_file_path):
                        # Read the PDF file
                        with open(pdf_file_path, "rb") as f:
                            pdf_data = f.read()
                        pdf_filename = f"compiled_{os.path.basename(os.path.splitext(tex_file_path)[0])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

                        # Display success message
                        st.success("LaTeX compiled successfully with latexmk!")

                        # Provide download button for the PDF
                        st.download_button(
                            label="Download PDF",
                            data=pdf_data,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )

                        # Embed PDF for preview
                        st.write("### PDF Preview")
                        st.components.v1.html(
                            f"""
                            <object data="data:application/pdf;base64,{pdf_data.hex()}" type="application/pdf" width="100%" height="600px">
                                <p>Your browser does not support PDF preview. Please download the PDF.</p>
                            </object>
                            """,
                            height=600
                        )
                    else:
                        st.error("PDF generation failed. Check the latexmk log below:")
                        st.text_area("latexmk Log", value=result.stdout + result.stderr, height=200, disabled=True)

                except subprocess.TimeoutExpired:
                    st.error("LaTeX compilation timed out. Please simplify your document or check for errors.")
                except Exception as latexmk_error:
                    st.error(f"latexmk compilation failed: {str(latexmk_error)}")
                    st.write("Please ensure all required files (e.g., cas-sc.cls, .bib, figures) are included in the `manuscript` and `figures` directories.")

    except PermissionError:
        st.error("Permission denied while accessing files in the `manuscript` directory. Check file permissions.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Instructions for the user
st.markdown("""
### Instructions
1. Ensure the `manuscript` directory is in the same directory as this script (`texcompiler.py`), with the structure:
   ```
   latex_typesetting/
   ├── texcompiler.py
   ├── manuscript/
   │   ├── paper.tex  (or anyname.tex)
   │   ├── cas-sc.cls
   │   └── references.bib  (optional)
   ├── figures/
   │   └── graphical_abstract.png  (optional)
   ```
2. Click "Compile LaTeX" to generate the PDF using latexmk.
3. Download the PDF or view it in the preview section.
4. For Streamlit Cloud deployment, include:
   - `requirements.txt`:
     ```
     streamlit
     ```
   - `packages.txt`:
     ```
     texlive-full
     latexmk
     ```
5. Example `paper.tex`:
   ```latex
   \\documentclass[a4paper,fleqn]{cas-sc}
   \\usepackage[version=4]{mhchem}
   \\usepackage{amsmath}
   \\usepackage{siunitx}
   \\sisetup{range-phrase = \\text{--}, range-units = single, per-mode = fraction, separate-uncertainty = true}
   \\DeclareSIUnit{\\dec}{dec}
   \\DeclareSIUnit{\\cycle}{cycles}
   \\usepackage[numbers,sort&compress]{natbib}
   \\usepackage{graphics}
   \\graphicspath{{figures/}}
   \\begin{document}
   \\shorttitle{Test}
   \\title[mode = title]{Test Manuscript}
   \\author[a]{Author}[]
   \\address[a]{Institute, City, Country}
   \\begin{abstract}
   This is a test.
   \\end{abstract}
   \\begin{keywords}
   test
   \\end{keywords}
   \\maketitle
   \\section{Introduction}
   Test document.
   \\end{document}
   ```
6. Ensure `cas-sc.cls` is in the `manuscript` directory (download from https://ctan.org/pkg/els-cas).
7. For local testing:
   ```bash
   conda activate stenv
   pip install streamlit
   sudo apt-get install texlive-full latexmk
   streamlit run texcompiler.py
   ```
8. For Streamlit Cloud, push to `anilkunwar/latex_typesetting` with the above structure.
""")
