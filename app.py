from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# .envファイルから環境変数を読み込み
load_dotenv()

def main():
    st.title("AI専門家チャット")

    # ラジオボタンで専門家を選択
    expert_type = st.radio(
        "相談したい専門家を選んでください:",
        ("IT技術の専門家", "料理の専門家")
    )

    # 選択された専門家に応じてシステムメッセージを切り替え
    if expert_type == "IT技術の専門家":
        system_content = "あなたは優秀なITエンジニアです。技術的な質問に対して、初心者にもわかりやすく、正確なコードや用語解説を交えて回答してください。"
    else:
        system_content = "あなたはプロのシェフです。料理のレシピやコツ、食材の知識について、親切かつ情熱的にアドバイスしてください。"

    # 入力フォーム
    user_input = st.text_input("質問を入力してください：")
    submit_button = st.button("送信")

    if submit_button and user_input:
        # LLMの準備
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

        # メッセージの構築
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_input),
        ]

        # LLMに送信して結果を取得
        with st.spinner("回答を生成中..."):
            try:
                # Lesson8を参考にした呼び出し（invokeを使用）
                result = llm.invoke(messages)
                
                st.subheader(f"【{expert_type}からの回答】")
                st.write(result.content)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()