'''VizPromptのコマンドラインインターフェース'''
import argparse

from ..llm import gemini
from ..llm import ollama
from ..core.node import NodeSaver

def handle_chat(prompt, response, model):
    prompt = prompt.rstrip()
    response = response.rstrip()
    print(f"ユーザー: {prompt}")
    print(f"{model}: {response}")

    # --- ノード保存処理 ---
    saver = NodeSaver(base_dir="project")
    node_id, node_path = saver.save_node(prompt, response, model=model)
    print(f"チャット履歴をノードとして保存しました: {node_path} (ID: {node_id})")

def run_cli():
    parser = argparse.ArgumentParser(description="VizPrompt CLI")
    subparsers = parser.add_subparsers(dest="command", help='トップレベルコマンド', required=True)

    # 'chat' サブコマンド
    chat_command_parser = subparsers.add_parser("chat", help="LLMとチャットします")
    chat_subparsers = chat_command_parser.add_subparsers(dest="service", help='チャットサービス', required=True)

    # 'chat gemini' サブコマンド
    gemini_parser = chat_subparsers.add_parser("gemini", help="Geminiとチャットします")
    gemini_parser.add_argument("prompt", type=str, help="Geminiへのプロンプト")

    # 'chat ollama' サブコマンド
    ollama_parser = chat_subparsers.add_parser("ollama", help="Ollamaとチャットします")
    ollama_parser.add_argument("prompt", type=str, help="Ollamaへのプロンプト")

    args = parser.parse_args()

    if args.command == "chat":
        if args.service == "gemini":
            response, model = gemini.generate_content(args.prompt)
            handle_chat(args.prompt, response, model)
        elif args.service == "ollama":
            response, model = ollama.generate_content(args.prompt)
            handle_chat(args.prompt, response, model)
        else:
            chat_command_parser.print_help()
    else:
        parser.print_help()

def main():
    run_cli()

if __name__ == "__main__":
    main()
