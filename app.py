from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# .envファイルから環境変数を読み込み
load_dotenv()

def main():
    st.title("お悩み相談アプリ - Lito")

    # ラジオボタンで専門家を選択
    worries_type = st.radio(
        "今あなたが抱えている悩みを教えてください:",
        ("健康", "心理", "仕事", "人間関係", "その他")
    )

    # 選択された専門家に応じてシステムメッセージを切り替え
    if worries_type == "健康":
        system_content ="あなたは優秀な健康アドバイザーです。健康に関する質問に対して、科学的根拠に基づき、わかりやすく丁寧に回答してください。"
    elif worries_type == "心理":    
        system_content = "あなたは経験豊富な心理カウンセラーです。心理的な悩みに対して、共感を持って寄り添い、適切なアドバイスを提供してください。"
    elif worries_type == "仕事":
        system_content = "あなたは優秀なキャリアコンサルタントです。仕事に関する悩みに対して、実践的なアドバイスや戦略を提供してください。"
    elif worries_type == "人間関係":
        system_content = "あなたは熟練した人間関係の専門家です。対人関係の悩みに対して、建設的な解決策やコミュニケーションのコツを提供してください。"
    else:   
        system_content = "あなたは多様な悩みに対応できる優秀な相談員です。あらゆる種類の悩みに対して、親身になって丁寧にアドバイスを提供してください。"
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
                
                st.subheader(f"【{worries_type}からの回答】")
                st.write(result.content)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()