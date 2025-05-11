'''VizPromptのコマンドラインインターフェース'''
import argparse

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

from ..core.node import NodeManager
from ..core.flow import FlowManager

def handle_chat(manager, generator, prompt, history=None):
    prompt = prompt.rstrip()
    print(f"{generator.model}: ", end="", flush=True)
    for chunk in generator.generate(prompt, history=history):
        print(chunk, end="", flush=True)
    if not generator.text.endswith("\n"):
        print() # 最後に改行
    generator.show_statistics_short()
    response = generator.text.rstrip()

    # ノード保存処理
    node = manager.create_node(prompt, response, generator)
    print(f"チャット履歴をノードとして保存しました: {node.path} (ID: {node.id})")
    return node.id

def chat_command(service, prompt):
    generator = None
    if service == "gemini":
        from ..llm import gemini
        generator = gemini.GeminiGenerator()
    elif service == "ollama":
        from ..llm import ollama
        generator = ollama.OllamaGenerator()
    elif service == "openai":
        from ..llm import openai
        generator = openai.OpenAIGenerator()
    if generator is None:
        chat_command_parser.print_help()
        return

    node_manager = NodeManager(base_dir="project")
    if prompt:
        print("User:", prompt)
        handle_chat(node_manager, generator, prompt)
        return

    # REPLモード
    flow_manager = FlowManager(base_dir="project")
    flow = flow_manager.create_flow(name="Chat Session")
    prev_node_id = None
    while True:
        try:
            prompt = input("User: ")
            if not prompt:
                break
            if prev_node_id is None:
                history_ids = []
            else:
                # 前のノードの履歴を取得
                history_ids = flow.get_history(prev_node_id) or [prev_node_id]
            history = node_manager.get_contents(history_ids)
            curr_node_id = handle_chat(node_manager, generator, prompt, history)
            if prev_node_id is not None:
                flow.connect(prev_node_id, curr_node_id)
                flow.save()
            prev_node_id = curr_node_id
        except EOFError:
            break

def run_cli():
    args = parser.parse_args()
    if args.command == "chat":
        chat_command(args.service, args.prompt)
    else:
        parser.print_help()

def main():
    run_cli()

if __name__ == "__main__":
    main()
