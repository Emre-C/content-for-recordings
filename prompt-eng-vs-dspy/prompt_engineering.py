# 0.  Setup & Configuration ────────────────────────────────────────────────────

import os
import json
import time
from openai import OpenAI
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In this exampple, we will categorize historical events.
EVENT_CATEGORIES = [
    "Wars",
    "Politics",
    "Science",
    "Culture"
]

# 1.  Build a Labeled Training Set for Evaluation ──────────────────────────────────────────

# 1a. Configure your Training LM client
TRAINING_MODEL_NAME = "gpt-4o"
TRAINING_MODEL_TEMPERATURE = 0.7
TRAINING_MAX_RESPONSE_TOKENS = 300

# 1b. Helper: call the model to generate N examples for a given category
def generate_events_for_category(
    category_label: str,
    number_of_examples: int
) -> List[str]:
    """
    Prompts the LM to output a JSON array of 'number_of_examples'
    concise historical-event descriptions for the given category.
    """
    TRAINSET_PROMPT_TEMPLATE = """
You are a dataset-generation assistant.
Produce exactly {number_of_examples} short, realistic historical
event descriptions that clearly belong to the category: {category_label}.

Return ONLY a valid JSON array of strings, nothing else. Example format:
["Event one description", "Event two description", "Event three description"]

Do not include any other text, explanations, or formatting - just the JSON array.
"""

    prompt = TRAINSET_PROMPT_TEMPLATE.format(
        number_of_examples=number_of_examples,
        category_label=category_label
    ).strip()

    response = client.chat.completions.create(
        model=TRAINING_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You generate high-quality synthetic data. Always respond with valid JSON arrays only."},
            {"role": "user", "content": prompt}
        ],
        temperature=TRAINING_MODEL_TEMPERATURE,
        max_tokens=TRAINING_MAX_RESPONSE_TOKENS
    )

    raw_output = response.choices[0].message.content.strip()

    # 1b-i. Try parsing JSON directly
    try:
        events_list = json.loads(raw_output)
        # Validate it's a list of strings
        if not isinstance(events_list, list):
            raise ValueError("Response is not a list")
        if not all(isinstance(event, str) for event in events_list):
            raise ValueError("Not all items are strings")
        return events_list
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse JSON for category {category_label}: {e}")
        print(f"Raw output: {raw_output}")
        # 1b-ii. Fallback: parse bullet points or lines
        events_list = []
        for line in raw_output.splitlines():
            line = line.strip()
            # Remove common prefixes and clean up
            line = line.lstrip("-*• ").strip()
            # Skip empty lines, JSON artifacts, and lines that look like formatting
            if (len(line) > 10 and 
                not line.startswith(("[", "]", "{", "}", "\"number_", "\"category_")) and
                not line.endswith((",", '"'))):
                # Remove surrounding quotes if present
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                events_list.append(line)
        
        print(f"Fallback parsing extracted {len(events_list)} events")
        return events_list

# 1c. Loop over each category, generate examples, and assemble the train set
training_examples: List[Dict[str, str]] = []
examples_per_category = 15      # 4 categories × 15 = 60 total examples

# Only generate if file doesn't exist
if not os.path.exists("labeled_event_examples.json"):
    for label in EVENT_CATEGORIES:
        generated_events = generate_events_for_category(label, examples_per_category)
        for event_description in generated_events:
            training_examples.append({
                "event": event_description,
                "category": label
            })

    print(f"Generated {len(training_examples)} total training examples.")

    # 1d. Save to disk for later
    with open("labeled_event_examples.json", "w") as outfile:
        json.dump(training_examples, outfile, indent=2)
else:
    print("Training examples file already exists, skipping generation.")


# 2.  Manually-Engineered Prompts ──────────────────────────────────────

CLASSIFICATION_MODEL_NAME = "gpt-4o-mini"
CLASSIFICATION_MODEL_TEMPERATURE = 0.0   # keep answers deterministic
CLASSIFICATION_MAX_RESPONSE_TOKENS = 50  # trim replies so parsing is easier

# 2a.  Baseline: "Just give me the label"
BASELINE_PROMPT_TEMPLATE = """
You are a historical-event classifier.
Allowed labels: {labels}

TASK:
Given the event description below, respond with **only** the correct label.

EVENT DESCRIPTION:
{event_text}

RESPONSE FORMAT:
One word: the exact label from the allowed labels.
"""

# 2b. Chain-of-Thought: guide the model to "think" before answering
COT_PROMPT_TEMPLATE = """
You are a historical-event classifier.
Allowed labels: {labels}

TASK:
Given the event description below, respond with **only** the correct label.

EVENT DESCRIPTION:
{event_text}

YOUR REASONING:
First, think step by step about the key facts.
1. ...
2. ...
3. ...

Then, at the end, respond with the single label from the allowed labels.

RESPONSE FORMAT:
One word: the exact label from the allowed labels.
"""

# 3.  Classification Functions ──────────────────────────────────────────────────

def classify_with_baseline_prompt(event_text: str) -> str:
    """
    Calls the LM with the baseline template and returns the predicted label.
    """
    prompt = BASELINE_PROMPT_TEMPLATE.format(
        labels=", ".join(EVENT_CATEGORIES),
        event_text=event_text
    ).strip()

    response = client.chat.completions.create(
        model=CLASSIFICATION_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=CLASSIFICATION_MODEL_TEMPERATURE,
        max_tokens=CLASSIFICATION_MAX_RESPONSE_TOKENS
    )

    raw_reply = response.choices[0].message.content.strip()

    # Parse out the first word as label
    predicted_label = raw_reply.split()[0]
    return predicted_label


def classify_with_chain_of_thought(event_text: str) -> str:
    """
    Calls the LM with the Chain-of-Thought template and returns the predicted label.
    """
    prompt = COT_PROMPT_TEMPLATE.format(
        labels=", ".join(EVENT_CATEGORIES),
        event_text=event_text
    ).strip()

    response = client.chat.completions.create(
        model=CLASSIFICATION_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=CLASSIFICATION_MODEL_TEMPERATURE,
        max_tokens=CLASSIFICATION_MAX_RESPONSE_TOKENS
    )

    raw_reply = response.choices[0].message.content.strip()
    
    # Look for any of our valid labels in the response
    for label in EVENT_CATEGORIES:
        if label in raw_reply:
            return label
    
    # Fallback: try to extract the last word as in baseline
    words = raw_reply.split()
    if words:
        last_word = words[-1].strip(".,!?")
        if last_word in EVENT_CATEGORIES:
            return last_word
    
    # If nothing found, return the first valid category as fallback
    return EVENT_CATEGORIES[0]


# 4.  Evaluation Utility ───────────────────────────────────────────────────────

def evaluate_classification_function(classify_fn, examples):
    """
    Runs classify_fn over each example in 'examples', 
    computes accuracy, and reports elapsed time.
    """
    correct_predictions = 0
    total_examples = len(examples)

    start_time = time.time()

    for example in examples:
        event_description = example["event"]
        true_label = example["category"]

        predicted_label = classify_fn(event_description)

        if predicted_label == true_label:
            correct_predictions += 1

    end_time = time.time()
    elapsed_seconds = end_time - start_time

    accuracy = correct_predictions / total_examples

    print(f"→ Function `{classify_fn.__name__}`")
    print(f"   • Accuracy: {accuracy:.2%}")
    print(f"   • Time elapsed: {elapsed_seconds:.1f}s")
    print("")

# 5.  Run Experiments ───────────────────────────────────────────────────────────

labeled_event_examples = json.load(open("labeled_event_examples.json"))

print("Evaluating baseline prompt…")
evaluate_classification_function(
    classify_with_baseline_prompt,
    labeled_event_examples
)

print("Evaluating Chain-of-Thought prompt…")
evaluate_classification_function(
    classify_with_chain_of_thought,
    labeled_event_examples
)


# 7.  Manual Tweak Loop ────────────────────────────────────────────────────────

# Now, whenever you want to adjust the prompt (e.g. add a few-shot example,
# change the instruction wording, tweak the format), you must:
#
#   1. Edit BASELINE_PROMPT_TEMPLATE or COT_PROMPT_TEMPLATE
#   2. Save your file
#   3. Rerun this entire script (minutes of API calls)
#   4. Compare the printed accuracies by eye, or write additional logging
#
# There is no built-in way to:
#   • track which prompt version gave which score
#   • easily swap to a different LM backend
#   • automatically explore hundreds of variants or log the results
