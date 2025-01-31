# Evaluation Pipeline

TAI is equipped with the ability to measure the reliability and accuracy of its underlying Retrieval-Augmented Generation (RAG) agent. To simplify dataset creation and evaluation, this module provides customized evaluation functionality, ranging from creating evaluation datasets to implementing evaluation algorithms specifically designed for TAI.

## Features

- **Dataset Generation**: Seamlessly generate evaluation datasets tailored to the needs of the TAI system.
- **Analysis Tools**: Analyze generated datasets to uncover biases and visualize relationships using Sankey graphs.

## Setup

1. **Install Requirements**: Install the required dependencies by running the following command:
   ```sh
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**: Ensure the `OPENAI_API_KEY` is stored as an environment variable. You can add it to your `.bashrc`, `.zshrc`, or `.env` file for persistent configuration:
   ```sh
   export OPENAI_API_KEY="your_api_key_here"
   ```

3. **Prepare Input Data**: Place your input JSON file in the following directory:
   ```
   /evaluation/dataset_generate/input
   ```

## Dataset Generation

To generate an evaluation dataset, run the following command:
```sh
python -m evaluation.dataset_generate.generate <input_filename> [--num_pairs] [--quiet]
```

### Arguments:
- `<input_filename>`: Name of the input JSON file located in `/evaluation/dataset_generate/input`.
- `--num_pairs`: (Optional) Specify the number of pairs to generate.
- `--quiet`: (Optional) Suppress output logs for a cleaner console experience.

Example:
```sh
python -m evaluation.dataset_generate.generate sample_input.json --num_pairs 50
```

## Dataset Analysis

To analyze the generated dataset for bias statistics and visualize relationships using a Sankey graph, use the following command:
```sh
python -m evaluation.dataset_analyze.analyze <input_filename> [--graph]
```

### Arguments:
- `<input_filename>`: Name of the input dataset file to analyze biases based on the input and output dataset labels.
- `--graph`: Option to generate the Sankey graph visualization. 

Example:
```sh
python -m evaluation.dataset_analyze.analyze generated_dataset.json --graph
```

## Output Files

- **Generated Datasets**: Saved in `/evaluation/dataset_generate/output`.
- **Analysis Results**: Saved in `/evaluation/dataset_analyze/output`.