# 1. Base Image
FROM python:3.10-slim

# 2. Install Dependencies (Include libgl1 for the installer GUI/headless checks)
RUN apt-get update && apt-get install -y \
    unzip \
    libx11-6 \
    libxext6 \
    libxt6 \
    libxrender1 \
    libxtst6 \
    libnss3 \
    libasound2 \
    libgl1 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libgtk-3-0 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Setup Install Directory
WORKDIR /tmp_install

# 4. Copy Runtime Zip AND the Config File
COPY MATLAB_Runtime_R2025b_Update_3_glnxa64.zip .
COPY installer_input.txt .

# 5. Unzip and Install
# We force the install script to read from the text file
RUN unzip -q MATLAB_Runtime_*.zip && \
    chmod -R +x . && \
    ./install -inputFile installer_input.txt && \
    cd / && \
    rm -rf /tmp_install

# 6. Set Environment Variables
# (Standard paths for Linux Runtime)
ENV LD_LIBRARY_PATH=/usr/local/MATLAB/MATLAB_Runtime/R2025b/runtime/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/bin/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/sys/os/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/sys/opengl/lib/glnxa64

# 7. Application Setup
WORKDIR /app
COPY SimPackage/ ./SimPackage/

# 8. Install Python Package
RUN pip install setuptools wheel && \
    cd SimPackage && \
    python -m pip install .

# 9. Final App Copy
COPY app.py .
RUN pip install numpy matlab streamlit matplotlib tifffile

# 10. Expose Streamlit Port
EXPOSE 8501

# 11. Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 12. Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
