FROM containers.mathworks.com/matlab-runtime:r2025b

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY streamlit/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install the compiled MATLAB Python package (produced by compile_matlab.sh)
COPY matlab/Compiled/PythonPackage/nsm_algorithms/ ./nsm_algorithms/
RUN pip3 install --no-cache-dir ./nsm_algorithms/

COPY streamlit/ .

EXPOSE 8501

CMD ["python3", "-m", "streamlit", "run", "main.py", "--server.address", "0.0.0.0"]
