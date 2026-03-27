import tiktoken

def count_tokens(text, model="gpt-3.5-turbo"):
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))