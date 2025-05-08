'''VizPromptのコマンドラインインターフェース'''
import argparse

from vizprompt.llm.gemini import send_prompt_to_gemini

def handle_chat_gemini(args):
    try:
        print(f"ユーザー: {args.prompt}")
        response = send_prompt_to_gemini(args.prompt)
        print(f"Gemini: {response}")
    except ValueError as ve:
        print(f"設定エラー: {ve}")
        print("環境変数 GEMINI_API_KEY が正しく設定されているか確認してください。")
    except Exception as e:
        print(f"エラー: {e}")

def run_cli():
    parser = argparse.ArgumentParser(description="VizPrompt CLI")
    subparsers = parser.add_subparsers(dest="command", help='トップレベルコマンド', required=True)

    # 'chat' サブコマンド
    chat_command_parser = subparsers.add_parser("chat", help="LLMとチャットします")
    chat_subparsers = chat_command_parser.add_subparsers(dest="service", help='チャットサービス', required=True)

    # 'chat gemini' サブコマンド
    gemini_parser = chat_subparsers.add_parser("gemini", help="Geminiとチャットします")
    gemini_parser.add_argument("prompt", type=str, help="Geminiへのプロンプト")

    args = parser.parse_args()

    if args.command == "chat":
        if args.service == "gemini":
            handle_chat_gemini(args)
        else:
            chat_command_parser.print_help()
    else:
        parser.print_help()

def main():
    run_cli()

if __name__ == "__main__":
    main()
