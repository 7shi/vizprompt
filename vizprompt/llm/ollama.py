'''Ollama APIと通信するためのモジュール'''
import ollama
from .base import BaseGenerator

default_model = "gemma3:1b"

class OllamaGenerator(BaseGenerator):
    def __init__(self, model = default_model):
        """
        OllamaGeneratorの初期化。

        Args:
            model_name: 使用するOllamaモデルの名前。
        """
        super().__init__(model)

    def generate(self, prompt: str):
        """
        Ollamaにプロンプトを送信し、ストリーム応答を取得します。

        Args:
            prompt: Ollamaに送信するプロンプト文字列。

        Yields:
            応答のチャンク文字列。
        """
        response = ollama.generate(model=self.model, prompt=prompt, stream=True)
        text = ""
        for chunk in response:
            text += chunk.response
            yield chunk.response
        self.text = text
        self.prompt_count    = chunk.prompt_eval_count
        self.prompt_duration = chunk.prompt_eval_duration / 1e9
        self.prompt_rate     = self.prompt_count / self.prompt_duration if self.prompt_duration > 0 else 0
        self.eval_count      = chunk.eval_count
        self.eval_duration   = chunk.eval_duration / 1e9
        self.eval_rate       = self.eval_count / self.eval_duration if self.eval_duration > 0 else 0

if __name__ == '__main__':
    user_prompt = "こんにちは、自己紹介してください。"
    print(f"ユーザー: {user_prompt}")
    g = OllamaGenerator()
    print(f"{g.model}: ", end="")
    response = g.generate(user_prompt)
    for chunk in response:
        print(chunk, end="", flush=True)
    if not g.text.endswith("\n"):
        print() # 最後に改行
    print()
    g.show_statistics()
