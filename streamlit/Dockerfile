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

COPY matlab/Compiled/PythonPackage/nsm_algorithms/ ./nsm_algorithms/

COPY streamlit/ .

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "main.py", "--server.address", "0.0.0.0"]
