BackScatter Factor (BSF) Calculation Tool
Developed at:
Radiological Physics & Advisory Division (RPAD)
Bhabha Atomic Research Centre (BARC), India




---------------------------------------------------------------------

If you are using this software in your Research, please give reference as:




---------------------------------------------------------------------

OVERVIEW
--------
The BackScatter Factor (BSF) Calculation Tool is a Python-based graphical
application developed to compute BSF values for photon beams using
Monte Carlo–derived spectral data and ISO-recommended phantom datasets.

The tool combines beam fluence spectra, phantom-specific BSF data,
and numerical interpolation (PCHIP) to estimate BSF accurately.

---------------------------------------------------------------------

FEATURES
--------
- Supports multiple beam series:
  • Narrow Series (N)
  • Wide Series (W)
  • High/Low Air Kerma Rate Series (H/L)
  • Diagnostic beams (RQA, RQR, etc.)
  • Therapy beams
  • Custom spectra input

- Supports ISO phantom geometries:
  • Slab Phantom
  • Cylindrical Phantom
  • Pillar Phantom
  • Rod Phantom

- Beam size selection (e.g., 10×10 cm², 20×20 cm², 30*30 cm²)

- Uses PCHIP interpolation for smooth BSF estimation

- Real-time plotting of normalized fluence

- Displays computed BSF value clearly

- Export options:
  • Save plots (PNG, PDF, SVG, TIFF)

---------------------------------------------------------------------

METHODOLOGY
-----------
The BSF is calculated using:

BSF = Σ [ Φ_norm(Ei) × BSF(Ei) ]

Where:
- Φ_norm(Ei) = normalized fluence at energy Ei
- BSF(Ei) = interpolated BSF value at energy Ei

Steps:
1. Normalize beam fluence spectrum
2. Interpolate BSF values using PCHIP
3. Compute weighted sum to obtain final BSF

---------------------------------------------------------------------

SYSTEM REQUIREMENTS
-------------------
Operating System: Ubuntu
- Tested on Ubuntu 24.04

Operating System : Windows






For source version:
- Python ≥ 3.8
- numpy
- pandas
- matplotlib
- scipy
- pillow
- tkinter



---------------------------------------------------------------------

INSTALLATION
------------

Option 1: Run Precompiled Executable -- Ubuntu
-----------------------------------
chmod +x claude
./claude

(No installation required)

Option 2: Run from Source Code
------------------------
pip install numpy pandas matplotlib scipy pillow
python claude.py

---------------------------------------------------------------------

DIRECTORY STRUCTURE
-------------------
BSF_GUI/

│-- claude.py
│-- beam_data/
│     ├── Narrow_Series/
│     ├── Wide_Series/
│     └── ...
│
│-- bsf_data/
│     ├── Slab_Phantom/
│     ├── Cylinderical_Phantom/
│     └── ...
│
│-- barc_logo.png
│-- README.txt

---------------------------------------------------------------------

USAGE INSTRUCTIONS
------------------
1. Select "Type of Beam"
2. Select "Beam"
3. Select "ISO Phantom"
4. Select "Beam Size"
5. (Optional) Load Custom Beam File
6. Click "Calculate BSF"

Output:
- BSF value displayed numerically
- Fluence spectrum plotted
- Results stored in session history

---------------------------------------------------------------------

OUTPUT FEATURES
---------------
- Plot of normalized fluence vs energy
- BSF value annotation on plot
- Export plot with options:
  • DPI
  • Background (dark/white/transparent)
  • Format (PNG/PDF/SVG/TIFF)

---------------------------------------------------------------------

DATA INPUT FORMAT
-----------------

Custom Beam File:
Energy (keV)    Fluence

---------------------------------------------------------------------

VALIDATION
----------
The tool has been validated against:
- ISO standard beam qualities
---------------------------------------------------------------------

LIMITATIONS
-----------
- Accuracy depends on input spectral resolution
- Extrapolation beyond data range may introduce uncertainty
- Applicable only to photon beams

---------------------------------------------------------------------

TROUBLESHOOTING
---------------

Issue: Application does not start
Solution:
chmod +x claude
./claude

Issue: Missing data or empty plot
Solution:
Ensure required folders/files exist:
beam_data/
bsf_data/
barc_logo.png

Issue: Slow startup (onefile build)
Solution:
This is expected due to runtime extraction

---------------------------------------------------------------------

CONTACT
-------
For queries or technical support:

rohityadav@barc.gov.in

---------------------------------------------------------------------

