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

    def chat(self, messages):
        """
        Ollamaにプロンプトを送信し、ストリーム応答を取得します。

        Args:
            messages: Ollamaに送信するメッセージのリスト。

        Yields:
            応答のチャンク文字列。
        """
        response = ollama.chat(
            model=self.model,
            messages=messages,
            stream=True,
        )
        text = ""
        count = 0
        for chunk in response:
            content = chunk["message"]["content"]
            if content:
                text += content
                count += 1
                yield content
        self.text = text
        self.prompt_count    = chunk.get("prompt_eval_count", 0)
        self.prompt_duration = chunk.get("prompt_eval_duration", 0) / 1e9
        self.prompt_rate     = self.prompt_count / self.prompt_duration if self.prompt_duration > 0 else 0
        self.eval_count      = chunk.get("eval_count", count)
        self.eval_duration   = chunk.get("eval_duration", 0) / 1e9
        self.eval_rate       = self.eval_count / self.eval_duration if self.eval_duration > 0 else 0

    def generate(self, prompt: str, history=None):
        """
        Ollamaにプロンプトを送信し、ストリーム応答を取得します。

        Args:
            prompt: Ollamaに送信するプロンプト文字列。
            history: Ollamaに送信する履歴のリスト。

        Yields:
            応答のチャンク文字列。
        """
        contents1 = [("user", prompt)]
        if history is None:
            contents = self.convert_history(contents1)
        else:
            # 履歴がある場合は、履歴を追加
            contents = self.convert_history(history + contents1)
        return self.chat(contents)

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
