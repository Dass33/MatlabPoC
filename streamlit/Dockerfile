FROM containers.mathworks.com/matlab-runtime:r2025b

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layers are ordered by change frequency (rarest first) so routine edits to
# env vars, requirements, or app code never invalidate the multi-GB MATLAB
# layers: a cache bust here means re-pushing ~8GB to every registry.

# Kept outside /app so a dev bind-mount of ./streamlit:/app doesn't shadow it.
COPY matlab/Compiled/PythonPackage/nsm_algorithms/ /opt/matlab_python/nsm_algorithms/

# Dark-signal calibration files. Paths to these are written into job configs and
# opened by MATLAB, so they live outside /app for the same bind-mount reason.
COPY streamlit/calibration/ /opt/calibration/
ENV CALIBRATION_DIR=/opt/calibration

RUN mkdir -p /opt/matlab_app
COPY matlab/Compiled/AnalyzeExperimentApp /opt/matlab_app/
COPY matlab/Compiled/run_AnalyzeExperimentApp.sh /opt/matlab_app/
RUN chmod +x /opt/matlab_app/run_AnalyzeExperimentApp.sh /opt/matlab_app/AnalyzeExperimentApp

COPY streamlit/requirements.txt .
RUN pip3 install  --break-system-packages --no-cache-dir -r requirements.txt

ENV AGREE_TO_MATLAB_RUNTIME_LICENSE=yes
# No global LD_LIBRARY_PATH: MATLAB runtime libs (own libstdc++, TBB) must not
# load into the Streamlit server process. The MCR worker (mcr_worker.py) and
# the compiled app's run script each set it for themselves.
ENV PYTHONPATH=/opt/matlab_python

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_ENABLE_STATIC_SERVING=true
ENV STREAMLIT_SERVER_HEADLESS=true

COPY streamlit/ .

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "main.py"]
