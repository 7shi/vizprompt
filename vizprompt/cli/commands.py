'''VizPromptのコマンドラインインターフェース'''
import argparse
from ..core.node import NodeManager

def handle_chat(manager, generator, prompt):
    prompt = prompt.rstrip()
    print(f"User: {prompt}")
    print(f"{generator.model}: ", end="", flush=True)
    for chunk in generator.generate(prompt):
        print(chunk, end="", flush=True)
    if not generator.text.endswith("\n"):
        print() # 最後に改行
    print()
    generator.show_statistics()
    response = generator.text.rstrip()

    # ノード保存処理
    node = manager.create_node(prompt, response, generator)
    print(f"チャット履歴をノードとして保存しました: {node.path} (ID: {node.id})")

def run_cli():
    parser = argparse.ArgumentParser(description="VizPrompt CLI")
    subparsers = parser.add_subparsers(dest="command", help='トップレベルコマンド', required=True)

    # 'chat' サブコマンド
    chat_command_parser = subparsers.add_parser("chat", help="LLMとチャットします")
    chat_subparsers = chat_command_parser.add_subparsers(dest="service", help='チャットサービス', required=True)

    # 'chat gemini' サブコマンド
    gemini_parser = chat_subparsers.add_parser("gemini", help="Geminiとチャットします")
    gemini_parser.add_argument("prompt", type=str, nargs="?", help="Geminiへのプロンプト")

    # 'chat ollama' サブコマンド
    ollama_parser = chat_subparsers.add_parser("ollama", help="Ollamaとチャットします")
    ollama_parser.add_argument("prompt", type=str, nargs="?", help="Ollamaへのプロンプト")

    # 'chat openai' サブコマンド
    openai_parser = chat_subparsers.add_parser("openai", help="OpenAIとチャットします")
    openai_parser.add_argument("prompt", type=str, nargs="?", help="OpenAIへのプロンプト")

    args = parser.parse_args()

    if args.command == "chat":
        generator = None
        if args.service == "gemini":
            from ..llm import gemini
            generator = gemini.GeminiGenerator()
        elif args.service == "ollama":
            from ..llm import ollama
            generator = ollama.OllamaGenerator()
        elif args.service == "openai":
            from ..llm import openai
            generator = openai.OpenAIGenerator()
        if generator is None:
            chat_command_parser.print_help()
        else:
            manager = NodeManager(base_dir="project")
            if args.prompt is None:
                # REPLモード
                while True:
                    try:
                        prompt = input(">>> ").rstrip()
                        if not prompt:
                            break
                        handle_chat(manager, generator, prompt)
                    except EOFError:
                        break
            else:
                handle_chat(manager, generator, args.prompt)
    else:
        parser.print_help()

def main():
    run_cli()

if __name__ == "__main__":
    main()
