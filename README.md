# SIH26142: Deep Learning Based SRM & Sub-Pixel Mapping Prototype

This repository contains a full end-to-end prototype for the Smart India Hackathon (SIH) problem statement **SIH26142** by NTRO.

## Architecture & Features
- **Agentic Workflow**: Uses LangChain and OpenAI to translate a user's natural language request into geospatial tool executions.
- **Microservice Backend**: A FastAPI (`api.py`) exposing the inference pipeline.
- **Interactive UI**: A Streamlit frontend (`app.py`) featuring an LLM chatbox and an interactive Leafmap split-map to compare 10m resolution vs AI-Enhanced 5m/2.5m mapped outputs.
- **Geospatial Fidelity**: All pipelines natively read and write `.tif` formats, strictly preserving coordinate reference systems (CRS) and multi-spectral bands.
- **Zero-Shot Models**: Utilizes `segment-geospatial` (LangSAM) for text-prompted sub-pixel land cover extraction.

---

## Step-by-Step Guide for Demo

### 1. Set Up the Environment
You need Python 3.9+ installed. Open a terminal in this directory and run:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Microservice API (Optional but recommended)
Open a terminal and run the FastAPI server:
```bash
python api.py
```
*The API will be available at `http://localhost:8000`. You can view the docs at `http://localhost:8000/docs`.*

### 3. Start the Streamlit Dashboard
Open a new terminal (activate the `venv` again) and run:
```bash
streamlit run app.py
```

### 4. Running the Demo for Judges
1. Open the Streamlit URL provided in the terminal (usually `http://localhost:8501`).
2. Input your **OpenAI API Key** in the sidebar (required for the LangChain agent to orchestrate the pipeline).
3. Upload a sample `.tif` Sentinel-2 tile.
4. In the Agent Prompt box, type a query like: `"Upscale this tile to 5m resolution and map out the buildings."`
5. Click **Execute Pipeline**. 
6. Watch the agent think and trigger the tools in the left column.
7. Once finished, the interactive **Split-Map** on the right will allow you to drag the slider left and right to compare the original 10m imagery with the Super-Resolved + Segmented output. 

> **Note on Super-Resolution Phase:** For hackathon speed, the current prototype uses standard resampling to simulate the SR mapping phase and maintain CRS. To plug in the actual L1BSR or DSen2 weights, you can easily modify the `upscale_geotiff` function in `tools.py` to pass the raster tensor through your PyTorch model.
