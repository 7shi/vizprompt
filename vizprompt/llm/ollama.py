'''Ollama APIと通信するためのモジュール'''
import ollama

# 必要に応じてモデルを変更してください。
model = "gemma3:1b"

def generate_content(prompt: str) -> tuple[str, str]:
    """
    Ollamaにプロンプトを送信し、応答を取得します。

    Args:
        prompt: Ollamaに送信するプロンプト文字列。

    Returns:
        (Ollamaからの応答文字列, 使用モデル名) のタプル。

    Raises:
        Exception: API呼び出し中にエラーが発生した場合。
    """
    response = ollama.generate(model=model, prompt=prompt)
    return response.response, model

if __name__ == '__main__':
    user_prompt = "こんにちは、自己紹介してください。"
    print(f"ユーザー: {user_prompt}")
    ollama_response, used_model = generate_content(user_prompt)
    print(f"{used_model}: {ollama_response}")
