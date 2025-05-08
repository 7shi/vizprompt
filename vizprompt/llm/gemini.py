'''Gemini APIと通信するためのモジュール'''
import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("環境変数 GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=api_key)

# 必要に応じてモデルを変更してください。
model = "gemini-2.0-flash-001"

def send_prompt_to_gemini(prompt: str) -> str:
    """
    Gemini APIにプロンプトを送信し、応答を取得します。

    Args:
        prompt: Geminiに送信するプロンプト文字列。

    Returns:
        Geminiからの応答文字列。

    Raises:
        ValueError: GEMINI_API_KEYが設定されていない場合。
        Exception: API呼び出し中にエラーが発生した場合。
    """

    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
        )
        return response.text
    except Exception as e:
        # エラーハンドリングを強化することを推奨します
        raise Exception(f"Gemini API呼び出し中にエラーが発生しました: {e}")

if __name__ == '__main__':
    # 簡単なテスト用（環境変数 GEMINI_API_KEY を設定して実行）
    try:
        user_prompt = "こんにちは、今日の天気は？"
        print(f"ユーザー: {user_prompt}")
        gemini_response = send_prompt_to_gemini(user_prompt)
        print(f"Gemini: {gemini_response}")
    except Exception as e:
        print(e)
