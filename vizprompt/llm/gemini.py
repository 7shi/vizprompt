'''Gemini APIと通信するためのモジュール'''
import os, sys, re, time
from google import genai
from .base import BaseGenerator, test

default_model = "gemini-2.0-flash-001"

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("環境変数 GEMINI_API_KEY が設定されていません。")

client = genai.Client(api_key=api_key)

class Generator(BaseGenerator):
    def __init__(self, model=None):
        """
        Generatorの初期化。

        Args:
            model_name: 使用するGeminiモデルの名前。
        """
        if model is None:
            model = default_model
        super().__init__(model)

    def generate_content_retry(self, config, contents):
        """
        Gemini APIにプロンプトを送信し、ストリーム応答を取得します。
        Args:
            config: Gemini APIの設定。
            contents: Geminiに送信するコンテンツリスト。
        Yields:
            応答のチャンク文字列。
        Raises:
            RuntimeError: 最大リトライ回数を超えた場合。
        """
        # リトライ回数を制限
        for _ in range(5):
            try:
                time1 = time.monotonic()
                response = client.models.generate_content_stream(
                    model=self.model,
                    config=config,
                    contents=contents,
                )
                time2 = None
                text = ""
                count = 0
                for chunk in response:
                    if chunk.text:
                        text += chunk.text
                        count += 1
                        if not time2:
                            time2 = time.monotonic()
                        yield chunk.text
                time3 = time.monotonic()
                self.text = text
                chunk_dict = chunk.to_json_dict()
                if usage_metadata := chunk_dict.get("usage_metadata"):
                    self.prompt_count = usage_metadata.get("prompt_token_count", 0)
                    self.eval_count = usage_metadata.get("candidates_token_count", count)
                else:
                    self.prompt_count = 0
                    self.eval_count = count
                self.prompt_duration = time2 - time1
                self.prompt_rate = self.prompt_count / self.prompt_duration if self.prompt_duration > 0 else 0
                self.eval_duration = time3 - time2
                self.eval_rate = self.eval_count / self.eval_duration if self.eval_duration > 0 else 0
                return
            except genai.errors.APIError as e:
                if hasattr(e, "code") and e.code in [429, 500, 502, 503]:
                    print(e, file=sys.stderr)
                    delay = 30
                    if e.code == 429:
                        details = getattr(e, "details", {}).get("error", {}).get("details", [])
                        rd = None
                        for d in details:
                            if "retryDelay" in d:
                                rd = d["retryDelay"]
                                break
                        if rd and (m := re.match(r"^(\d+)s$", rd)):
                            delay = int(m.group(1)) or delay
                    for i in range(delay, -1, -1):
                        print(f"\rRetrying... {i}s ", end="", file=sys.stderr, flush=True)
                        time.sleep(1)
                    print(file=sys.stderr)
                    continue
                else:
                    raise
        raise RuntimeError("Max retries exceeded.")

    def convert_history(self, history):
        """
        (role, content) のリストを Gemini 用の履歴形式に変換
        """
        return [
            genai.types.Content(
                role=role,
                parts=[genai.types.Part.from_text(text=content)]
            )
            for role, content in history
        ]

    def generate(self, prompt: str, history=None):
        """
        Geminiにプロンプトを送信し、ストリーム応答を取得します。

        Args:
            prompt: Geminiに送信するプロンプト文字列。
            history: Geminiに送信する履歴のリスト。

        Yields:
            応答のチャンク文字列。
        """
        config = genai.types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        contents1 = [("user", prompt)]
        if history is None:
            contents = self.convert_history(contents1)
        else:
            # 履歴がある場合は、履歴を追加
            contents = self.convert_history(history + contents1)
        return self.generate_content_retry(config, contents)

if __name__ == '__main__':
    test(Generator)
