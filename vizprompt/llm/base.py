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
