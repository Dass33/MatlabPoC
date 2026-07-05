FROM containers.mathworks.com/matlab-runtime:r2025b

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV AGREE_TO_MATLAB_RUNTIME_LICENSE=yes
ENV LD_LIBRARY_PATH=/opt/matlabruntime/R2025b/runtime/glnxa64:/opt/matlabruntime/R2025b/bin/glnxa64:/opt/matlabruntime/R2025b/sys/os/glnxa64:/opt/matlabruntime/R2025b/extern/bin/glnxa64

COPY streamlit/requirements.txt .
RUN pip3 install  --break-system-packages --no-cache-dir -r requirements.txt

# Kept outside /app so a dev bind-mount of ./streamlit:/app doesn't shadow it.
ENV PYTHONPATH=/opt/matlab_python
COPY matlab/Compiled/PythonPackage/nsm_algorithms/ /opt/matlab_python/nsm_algorithms/

RUN mkdir -p /opt/matlab_app
COPY matlab/Compiled/AnalyzeExperimentApp /opt/matlab_app/
COPY matlab/Compiled/run_AnalyzeExperimentApp.sh /opt/matlab_app/
RUN chmod +x /opt/matlab_app/run_AnalyzeExperimentApp.sh /opt/matlab_app/AnalyzeExperimentApp

COPY streamlit/ .

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "main.py", "--server.address", "0.0.0.0"]
