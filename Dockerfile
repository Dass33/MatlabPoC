# Stage 1: MATLAB Runtime Installer
FROM python:3.10-slim AS runtime-installer

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

WORKDIR /tmp_install

# Copy Runtime Zip AND the Config File (only if they exist locally)
# If you want to download instead, use:
# ADD https://ssd.mathworks.com/supportfiles/downloads/R2025b/Release/3/deployment_files/installer/glnxa64/MATLAB_Runtime_R2025b_Update_3_glnxa64.zip .
COPY MATLAB_Runtime_R2025b_Update_3_glnxa64.zip .
COPY installer_input.txt .

RUN unzip -q MATLAB_Runtime_*.zip && \
    chmod -R +x . && \
    ./install -inputFile installer_input.txt && \
    rm -rf /tmp_install

# Stage 2: Final Application Image
FROM python:3.10-slim

# Install system dependencies needed for runtime execution
RUN apt-get update && apt-get install -y \
    libx11-6 libxext6 libxt6 libxrender1 libxtst6 libnss3 libasound2 \
    libgl1 libxcomposite1 libxcursor1 libxi6 libxrandr2 libxss1 \
    libgtk-3-0 libglib2.0-0 libpango-1.0-0 libatk1.0-0 libatk-bridge2.0-0 \
    libgdk-pixbuf-2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy MATLAB Runtime from installer stage
COPY --from=runtime-installer /usr/local/MATLAB/MATLAB_Runtime /usr/local/MATLAB/MATLAB_Runtime

# Set Environment Variables
ENV LD_LIBRARY_PATH=/usr/local/MATLAB/MATLAB_Runtime/R2025b/runtime/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/bin/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/sys/os/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/sys/opengl/lib/glnxa64
ENV PYTHONPATH=/workspace:/usr/local/MATLAB/MATLAB_Runtime/R2025b/toolbox/compiler_sdk/pysdk_py/matlab_mod_dist:/usr/local/MATLAB/MATLAB_Runtime/R2025b/toolbox/compiler_sdk/pysdk_py:/usr/local/MATLAB/MATLAB_Runtime/R2025b/bin/glnxa64:/usr/local/MATLAB/MATLAB_Runtime/R2025b/extern/bin/glnxa64
ENV XAPPLRESDIR=/usr/local/MATLAB/MATLAB_Runtime/R2025b/X11/app-defaults

WORKDIR /workspace



# Install Python dependencies first (to leverage cache)

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt



# Copy and install the SimPackage (binding)

COPY SimPackage/ ./SimPackage/

RUN pip install --no-cache-dir ./SimPackage



# Copy application source

COPY app/ ./app/



# Expose Streamlit Port

EXPOSE 8501



# Healthcheck

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1



# Run Streamlit

CMD ["streamlit", "run", "app/main.py", "--server.address=0.0.0.0"]
