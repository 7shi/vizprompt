from colorama import just_fix_windows_console, Style

just_fix_windows_console()

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
