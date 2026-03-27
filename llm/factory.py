from .gemini import GeminiLLM
# from .openai_llm import OpenAILLM
# from .groq_llm import GroqLLM


def get_llm(model_name):
    if "gemini" in model_name:
        return GeminiLLM()
    if "openai" in model_name:
        return "openai"
    if "groq" in model_name:
        return "groq"
    raise ValueError("Unsupported model")