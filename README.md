# NSM Data Processing App

We have a algorithm for processing data, it is written in Matlab we have quite stable api for the inputs and outputs.
Researcers which are working on the project have physics or chemistry background and they often are not familiar with Matlab.
We want for the researchers to have very easy onboarding and have least amount of friction for their work.

So we decided in create a web app whith graphical interface, which will call the Matlab code
At this moment we are using Compiler SDK and bundle the Matlab runtime with our app

Other benefit is that in the future we would like to use algorithm that is hevier on resources
and we want for the code to be able to run on cluster (the heavy computing part).

We need for the solution to be as simple as possible.

At this moment on consumer grade hardware we run experiments for about 10-20 minutes,
but in the future we will have larger data sets (more microscope images),
and hevier algorithm (because if we relax this constraint we would be able to track particles which are smaller)


There are like 4-6 users which run experiments, and they use the microscope in sequential order,
it would be nice to support paraller usage, but it could be potentially arranged to have sequential order.

## How to run

### Prerequisites
- MATLAB Runtime R2025b
- Python 3.10+

### Local Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install the MATLAB-Python binding:
   ```bash
   cd SimPackage
   python -m pip install .
   ```
3. Run the application:
   Using the helper script (recommended):
   ```bash
   ./scripts/run_app.sh
   ```

### Running with Docker
```bash
docker build -t nsm-app .
docker run -p 8501:8501 nsm-app
#8501 is the port Streamlit uses
```
