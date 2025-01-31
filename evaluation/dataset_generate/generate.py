import json
import openai
import os
from openai import OpenAI
import argparse
from pprint import pprint
from rag.file_conversion_router.conversion.ed_converter import json_kb_filter

api_key = os.getenv("OPENAI_API_KEY")

openai.api_key = api_key

GENERAL_LABELS = ["Logistics: Questions and Discussions About Course Administration and Operations", 
                  "Concepts: Understanding and Clarifying Theoretical knowledge and ideas", 
                  "Application: Practical Use of Knowledge in Assignments, Projects, and Real-world Contexts"]

client = None


def generate_qa_pairs(data):
    student_posts = []
    admin_posts = []
    qa_pairs = []

    for post in data:
        if post['type'] == 'question' and post['user']['role'] == 'student' and post['answers']:
            student_posts.append(post)

        if post['type'] == 'post' and post['user']['role'] == 'admin' and post['comments']:
            admin_posts.append(post)

    for post in student_posts:
        question = post.get('text', '')
        answer = None
        category = post.get('category', '')

        for answer_post in post['answers']:
            if answer_post['user']['role'] == 'admin':
                answer = answer_post.get('text', '')
                break
        
        if question and answer:
            qa_pairs.append({
                "question": question,
                "answer": answer,
                "category": category,
            })

    for post in admin_posts:
        category = post.get('category', '')

        for comment in post.get('comments', []):
            if comment['user']['role'] == 'student':
                question = comment.get('text', '')
                answer = None

                for reply in comment.get('comments', []):
                    if reply['user']['role'] == 'admin':
                        answer = reply.get('text', '')
                        break
                
                if question and answer:
                    question = str(question)
                    answer = str(answer)
                    qa_pairs.append({
                        "question": question,
                        "answer": answer,
                        "category": category,
                    })

    return qa_pairs


def get_labels(question, answer):
    global client

    sys_prompt = f"""Task: For the given question and answer pair:
                    Provide the results in the following format:
                    {{
                        "summary": "Summarize the content of both the question and answer into one concise sentence.",
                        "label": "Carefully review and understand the definitions of the provided labels, then select the most fitting label based on these definitions. The output label must strictly be the label name without including its definition: {", ".join(GENERAL_LABELS)}.",,
                        "valid": "Verify if the answer logically responds to the question and maintains context (1 for yes, 0 for no).",
                        "future_relevance": "Determine if this question-answer pair is generally useful for future reference (1) or limited to a time-specific context (0)."
                    }}
                """

    user_prompt = f"""
                    Question: {question}
                    Answer: {answer}
                """
    
    if client is None:
        client = OpenAI()
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )

    pprint(response.choices[0].message.content)
    parsed_response = json.loads(response.choices[0].message.content)
    
    return parsed_response


def generate(input_filename, num_pairs=None, quiet=False):

    input_path = os.path.join("evaluation", "dataset_generate", "input", input_filename)

    with open(input_path, 'r') as file:
        json_data = json.load(file)
    
    dataset_cleaned = json_kb_filter(json_data)
    qa_pairs = generate_qa_pairs(dataset_cleaned)

    if num_pairs:
        qa_pairs = qa_pairs[:num_pairs]
    else:
        qa_pairs = qa_pairs

    final_dataset = []

    for entry in qa_pairs: 
        question = entry["question"]
        answer = entry["answer"]
        
        label_response = get_labels(question, answer)

        label = label_response.get("label")
        valid = label_response.get("valid")
        future_relevance = label_response.get("future_relevance")

        entry["category"] = label
        entry["valid"] = valid
        entry["future_relevance"] = future_relevance

        if not quiet:
            pprint(label_response)
            
        if valid:
            final_dataset.append({"question": question, "answer": answer, "category": label, "future_relevance": future_relevance})
            
    
    output_path = os.path.join("evaluation", "dataset_generate", "output", f"evaluation_dataset_{input_filename}")

    with open(output_path, 'w') as output_file:
        json.dump(final_dataset, output_file, indent=4)

    print(f"QA pairs successfully written to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate evaluation dataset")
    parser.add_argument("input_filename", type=str, help="The input JSON file")
    parser.add_argument("--num_pairs", type=int, help="Number of QA pairs to generate")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")

    args = parser.parse_args()
    generate(args.input_filename, args.num_pairs, args.quiet)

