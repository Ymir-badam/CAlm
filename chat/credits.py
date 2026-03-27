MODEL_RATES = {
    "gemini-2.5-flash": {
        "input": 0.0000005,
        "output": 0.000001
    },
    "openai": {
        "input": 0.000002,
        "output": 0.000004
    },
    "groq": {
        "input": 0.0000008,
        "output": 0.0000015
    }
}

def calculate_cost(model, input_tokens, output_tokens):
    print(model, input_tokens, output_tokens)
    rates = MODEL_RATES[model]
    return (input_tokens * rates["input"]) + (output_tokens * rates["output"])