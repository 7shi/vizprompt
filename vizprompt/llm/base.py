'''LLM Generatorの共通基底クラス'''

class BaseGenerator:
    def __init__(self, model):
        self.model = model
        self.text  = ""
        self.prompt_count    = 0
        self.prompt_duration = 0
        self.prompt_rate     = 0
        self.eval_count      = 0
        self.eval_duration   = 0
        self.eval_rate       = 0

    def show_statistics(self):
        print(f"prompt_count   : {self.prompt_count}")
        print(f"prompt_duration: {self.prompt_duration:.2f} s")
        print(f"prompt_rate    : {self.prompt_rate:.2f} tokens/s")
        print(f"eval_count     : {self.eval_count}")
        print(f"eval_duration  : {self.eval_duration:.2f} s")
        print(f"eval_rate      : {self.eval_rate:.2f} tokens/s")

    def show_statistics_short(self):
        print(f"[in: {self.prompt_count} / {self.prompt_duration:.2f} s = {self.prompt_rate:.2f} tps]", end="")
        print(f"[out: {self.eval_count} / {self.eval_duration:.2f} s = {self.eval_rate:.2f} tps]")

    def convert_history(self, history):
        """
        (role, content) のリストを履歴形式に変換
        """
        return [{"role": role, "content": content} for role, content in history]
