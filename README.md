# Data-Knowledge-Fused Digital Twin Model Extraction
# In the A Posteriori Model Extraction Strategy

A lightweight tool for extracting Stochastic Petri Net models informed by both IoT data and expert knowledg in unstructured natural language.

## Getting Started

Navigate into the folder model_extraction and execute the file main.py, which contains the model extraction pipeline: *Tested with Python 3.12*
With this the approach implementation will be automatically executed with the case study data.

### Via git

```bash
git clone https://gitlab.kit.edu/michelle.jungmann/dkdt-model-extraction.git  # 1. clone repository
pip install -r requirements.txt # 2. install the requirements.txt
cd model_extraction # 3. navigate into the model extraction pipeline folder
python main.py  # 4. run the model extraction pipeline
```

## Model Extraction Input

The model extraction pipeline requires two inputs in the input_data folder: 

1) IoT data in format of event and state logs. In this case they are structured in one file. For the journal paper case study, we utilize the MainProcess.xes, which we transformed into csv format. MainProcess.xes is stemming from the dataset An IoT-Enriched Event Log for process mining in Smart Factories [1,2].

2) Expert knowlege in format of unstructured natural language in a csv file format. For the journal paper case study, we provide the case study expert knowledge statements in the expert_knowledge.csv file.


## Model Extraction Pipeline

In the a posteriori strategy, the model extraction pipeline first processes IoT data and second it processes the provided expert knowledge. Next, it extracts a Stochastic Petri Net model in a data-driven manner from the processed IoT data and subsequently integrates expert knowledge with differentiated  model components to complement the data-driven model and extract a data-knowledge-fused model. With this the extracted model is informed by both expert knowledge and IoT data. Last, the pipeline creates a visualization based on a adapted version of pyspn. The algorithm steps are named as in the journal paper to support comparability. 

## Model Extraction Output

The results of the algorithm are saved in the output folder. The results contain the visualized model in gv, png and pdf format. The output file also contains the results of the automated expert knowledge processing step including knowledge classification and formalization.


## Usage & Attribution

If you are using the tool for a scientific project please consider citing [publication placeholder]

For questions and feedback feel free to contact me.

[1] Malburg L, Grüger J, Bergmann R. An IoT-Enriched Event Log for Process Mining in Smart Factories 2022. https://doi.org/10.48550/arXiv.2209.02702.

[2]	Malburg L, Grüger J, Bergmann R. Dataset: An IoT-Enriched Event Log for Process Mining in Smart Factories 2024:1942783852 Bytes. https://doi.org/10.6084/M9.FIGSHARE.20130794.V6


