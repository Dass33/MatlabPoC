FROM containers.mathworks.com/matlab-runtime:r2025b

ENV AGREE_TO_MATLAB_RUNTIME_LICENSE=yes

RUN mkdir -p /opt/matlab_app

COPY Compiled/AnalyzeExperimentApp /opt/matlab_app/
COPY Compiled/run_AnalyzeExperimentApp.sh /opt/matlab_app/
COPY Compiled/*.ctf /opt/matlab_app/

RUN chmod +x /opt/matlab_app/run_AnalyzeExperimentApp.sh

RUN mkdir -p /data/input /data/output

WORKDIR /opt/matlab_app

ENV LD_LIBRARY_PATH=/opt/matlabruntime/R2025b/runtime/glnxa64:/opt/matlabruntime/R2025b/bin/glnxa64:/opt/matlabruntime/R2025b/sys/os/glnxa64:/opt/matlabruntime/R2025b/extern/bin/glnxa64

ENTRYPOINT ["/opt/matlab_app/run_AnalyzeExperimentApp.sh"]
