# DSPy vs Manual Prompt Engineering Comparison

This project demonstrates the efficiency and effectiveness of DSPy compared to manual prompt engineering for a historical event classification task.

## Files

- **`prompt_engineering.py`** - Manual prompt engineering approach (284 lines)
- **`dspy.py`** - DSPy implementation (much shorter and more efficient)
- **`requirements.txt`** - Dependencies for both approaches

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

## Usage

### Run Individual Scripts

```bash
# Manual prompt engineering approach
python prompt_engineering.py

# DSPy approach  
python dspy.py
```

### Run Comparison

```bash
python compare.py
```

## Key Differences

| Aspect | Manual Approach | DSPy Approach |
|--------|----------------|---------------|
| **Lines of Code** | ~284 lines | ~90 lines |
| **Prompt Engineering** | Manual template crafting | Automatic optimization |
| **Data Generation** | Manual JSON parsing/fallbacks | Automatic with type safety |
| **Evaluation** | Custom evaluation loops | Built-in metrics |
| **Model Switching** | Manual API client management | Unified LM interface |
| **Optimization** | Manual trial-and-error | Automatic with MIPROv2 |
| **Type Safety** | No validation | Pydantic-powered validation |
| **Persistence** | No model saving | Built-in save/load |

## DSPy Advantages Demonstrated

1. **Code Reduction**: ~68% fewer lines of code
2. **Automatic Optimization**: No manual prompt tuning required
3. **Type Safety**: Pydantic validation prevents runtime errors
4. **Better Modularity**: Clean separation of concerns
5. **Built-in Evaluation**: Standardized metrics and comparison
6. **Model Persistence**: Easy save/load functionality
7. **Provider Agnostic**: Switch between LLM providers easily

## Results

The DSPy implementation typically achieves:
- Similar or better accuracy than manual approaches
- Significantly less development time
- More maintainable and readable code
- Better error handling and type safety
- Automatic prompt optimization that often outperforms manual engineering 