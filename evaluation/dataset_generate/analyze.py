import json
import os
from pprint import pprint
import argparse
import plotly.graph_objects as go
from evaluation.dataset_generate.generate import generate_qa_pairs
from rag.file_conversion_router.conversion.ed_converter import json_kb_filter

def compute_bias(data):

    categories = []
    category_dict = {}
    total_count = 0

    for entry in data:

        category = entry['category']
        if category not in categories and category not in category_dict:
            categories.append(category)
            category_dict[category] = 1
        else:
            category_dict[category] += 1
        total_count += 1

    biases = {key: value / total_count for key, value in category_dict.items()}
    
    return biases


def analyze(input_filename, graph=True):

    original_file_path = os.path.join("evaluation", "dataset_generate", "input", input_filename)
    generated_file_path = os.path.join("evaluation", "dataset_generate", "output", f"evaluation_dataset_{input_filename}")

    with open(original_file_path, 'r') as file:
            original_file = json.load(file)

    with open(generated_file_path, 'r') as file:
        generated_dataset = json.load(file)
    
    original_cleaned = json_kb_filter(original_file)
    original_dataset = generate_qa_pairs(original_cleaned)

    biases_before = compute_bias(original_dataset)
    biases_after = compute_bias(generated_dataset)

    biases_stats = {
        "Before": biases_before,
        "After": biases_after
    }

    after_dict = {(entry["question"], entry["answer"]): entry["category"] for entry in generated_dataset}

    change = []

    for entry in original_dataset:
        question, answer, category_before = entry["question"], entry["answer"], entry["category"]
        new_category = after_dict.get((question, answer))

        if new_category:
            change_status = {
                "question": question,
                "answer": answer,
                "before_category": category_before,
                "after_category": new_category
            }
            change.append(change_status)
        else:
            invalid_pair = {
                "question": question,
                "answer": answer,
                "before_category": category_before,
                "after_category": "Invalid"
            }
            change.append(invalid_pair)

    result = {
        "biases": biases_stats,
        "results_comparison": change
    }

    pprint(biases_stats)

    output_path = os.path.join("evaluation", "dataset_generate", "output", f"datasets_analysis_{input_filename}")
    with open(output_path, 'w') as file:
        json.dump(result, file, indent=4)

    if graph:
        before_categories = set()
        after_categories = set()
        transitions = {}

        category_colors = {
            "General": "#aec7e8",      # Light Blue
            "Problem Sets": "#ffbb78", # Light Orange
            "Assignments": "#98df8a",  # Light Green
            "Lectures": "#ff9896",     # Light Red
            "Sections": "#c5b0d5",     # Light Purple
            "Social": "#c49c94"        # Light Brown
        }

        for entry in change:
            before = entry.get("before_category")
            after = entry.get("after_category")

            before_categories.add(before)
            after_categories.add(after)

            if (before, after) in transitions:
                transitions[(before, after)] += 1
            else:
                transitions[(before, after)] = 1

        before_labels = sorted(before_categories)
        after_labels = sorted(after_categories)
        all_labels = before_labels + after_labels
        node_indices = {label: i for i, label in enumerate(all_labels)}

        link_sources = []
        link_targets = []
        link_values = []
        link_colors = []

        for (before, after), count in transitions.items():
            link_sources.append(node_indices[before])
            link_targets.append(node_indices[after])
            link_values.append(count)
            link_colors.append(category_colors.get(before, "#d3d3d3"))

        fig = go.Figure(go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=all_labels,
                color=["#a0c4ff"] * len(before_labels) + ["#ffc09f"] * len(after_labels)
            ),
            link=dict(
                source=link_sources,
                target=link_targets,
                value=link_values,
                color=link_colors
            )
        ))
        
        output_path = os.path.join("evaluation", "dataset_generate", "output", f"category_flow_diagram_{os.path.splitext(input_filename)[0]}.png")

        fig.update_layout(title_text="Diagram of Category Transitions", font_size=10)
        fig.write_image(output_path)
        
        print(f"Sankey diagram saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate evaluation dataset")
    parser.add_argument("input_filename", type=str, help="The input JSON file")
    parser.add_argument("--graph", action="store_true", help="Generate Graph")

    args = parser.parse_args()
    analyze(args.input_filename, args.graph)

   
 