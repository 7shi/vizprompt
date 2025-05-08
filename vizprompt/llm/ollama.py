'''Ollama APIと通信するためのモジュール'''
import ollama

# 必要に応じてモデルを変更してください。
model = "gemma3:1b"

def generate_content(prompt: str) -> str:
    """
    Ollamaにプロンプトを送信し、応答を取得します。

    Args:
        prompt: Ollamaに送信するプロンプト文字列。

    Returns:
        Ollamaからの応答文字列。

    Raises:
        Exception: API呼び出し中にエラーが発生した場合。
    """
    response = ollama.generate(model=model, prompt=prompt)
    return response.response

if __name__ == '__main__':
    # 簡単なテスト用（OLLAMA_MODEL環境変数を設定して実行）
    user_prompt = "こんにちは、自己紹介してください。"
    print(f"ユーザー: {user_prompt}")
    ollama_response = generate_content(user_prompt)
    print(f"Ollama: {ollama_response}")
