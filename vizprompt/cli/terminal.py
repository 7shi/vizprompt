from colorama import just_fix_windows_console, Style

just_fix_windows_console()

def bold(text):
    """Coloramaの太字に変換"""
    return Style.BRIGHT + text + Style.NORMAL

def convert_markdown(text):
    """Markdownの**強調**部分をColoramaの太字に変換（閉じられていなくても対応）"""
    result = ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")  # 改行コードをLFに変換
    bright_mode = False
    i = 0

    while i < len(text):
        # **を検索
        if i + 1 < len(text) and text[i:i+2] == "**":
            # スタイルを切り替える
            bright_mode = not bright_mode
            if bright_mode:
                result += Style.BRIGHT
            else:
                result += Style.NORMAL
            i += 2  # **の2文字分スキップ
        else:
            # 改行があって閉じられていなければ自動で閉じる
            if bright_mode and text[i] == "\n":
                result += Style.NORMAL
                bright_mode = False
            # 通常の文字はそのまま追加
            result += text[i]
            i += 1

    # 閉じられていなければ自動で閉じる
    if bright_mode:
        result += Style.NORMAL

    return result

class MarkdownStreamConverter:
    """
    ストリームで受け取ったテキストを逐次的に**ボールド**変換するクラス。
    "*"が来たら次も"*"かを見てボールド切替、閉じられていなければ改行や終了時に自動で閉じる。
    """
    def __init__(self):
        self.buffer = ""
        self.bright_mode = False

    def feed(self, chunk):
        output = ""
        i = 0
        text = self.buffer + chunk
        self.buffer = ""
        while i < len(text):
            # "**"を検出
            if i + 1 < len(text) and text[i:i+2] == "**":
                self.bright_mode = not self.bright_mode
                output += Style.BRIGHT if self.bright_mode else Style.NORMAL
                i += 2
            else:
                # 最後の"*"で終わっている場合はバッファに残す
                if text[i] == "*" and i + 1 == len(text):
                    self.buffer = "*"
                    break
                # 改行で自動で閉じる
                if self.bright_mode and text[i] == "\n":
                    output += Style.NORMAL
                    self.bright_mode = False
                output += text[i]
                i += 1
        return output

    def flush(self):
        # バッファに*が残っていた場合は出力
        output = self.buffer
        self.buffer = ""
        if self.bright_mode:
            output += Style.NORMAL
            self.bright_mode = False
        return output
