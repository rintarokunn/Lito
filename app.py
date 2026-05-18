import streamlit as st
import sqlite3
import datetime
from openai import OpenAI
from datetime import datetime

# --- 1. データベース・お財布管理の定義（ここが金庫番！） ---

def get_db_connection():
    conn = sqlite3.connect('lito.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_usage (
            date TEXT PRIMARY KEY,
            total_cost REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()

def get_db_cost():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT total_cost FROM api_usage WHERE date = ?", (today,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0.0

PRICE_PER_TOKEN_INPUT = 0.150 / 1_000_000
PRICE_PER_TOKEN_OUTPUT = 0.600 / 1_000_000

def is_allowed_before_api(user_id, total_cost_limit=0.5):
    if user_id == "my_name":
        return True
    current_cost = get_db_cost()
    if current_cost >= total_cost_limit:
        return False
    return True

def save_new_cost(user_id, usage):
    if user_id == "my_name":
        return
    today = datetime.now().strftime("%Y-%m-%d")
    current_cost = get_db_cost()
    call_cost = (usage.prompt_tokens * PRICE_PER_TOKEN_INPUT) + \
                (usage.completion_tokens * PRICE_PER_TOKEN_OUTPUT)
    new_cost = current_cost + call_cost
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO api_usage (date, total_cost) VALUES (?, ?)", (today, new_cost))
    conn.commit()
    conn.close()

# -----2.システムの内部処理
with st.expander("📊 本アプリケーションの技術仕様・ソースコード構造解説"):
    st.markdown("""
    ### 🏗️ テクニカル・アーキテクチャ解説
    本アプリケーションは、ユーザーのUI操作の裏側で、データベース管理、クラウドコスト制御、LLMの状態管理を統合したバックエンド処理を実行しています。

    #### 1. 堅牢なお財布ガード（予算超過防止システム）
    * **1トークン刻みの原価計算**: `PRICE_PER_TOKEN_INPUT / OUTPUT` を定義し、OpenAIの公式料金（100万トークンあたりのドル単価）をベースに、1回ごとのチャットにかかる利用料金を小数点以下6桁レベルで精密に算出。
    * **事前インターセプト処理**: `is_allowed_before_api()` 関数により、AIへリクエストを送信する「直前」に当日の消費額をチェック。上限（$0.5）を超えている一般ユーザーからのアクセスはAPIに到達させる前に遮断（エラーハンドリング）し、予期せぬクラウド破産を防ぐ設計にしています。

    #### 2. プロンプト・エンジニアリングの動的カプセル化
    * **コンテキストの自動注入**: `st.radio` で選択されたジャンル（健康・心理・仕事など）に応じた役割（System Prompt）を、ディクショナリ構造（`prompts`）から動的に抽出。ユーザーの入力文とカプセル化して大言語モデル（`gpt-4o-mini`）へ引き渡すことで、高度な対話の最適化を実現しています。

        """)



# --- 3. メイン処理 ---

def main():
    init_db()
    st.title("お悩み相談アプリ - Lito")
    
    if "lito_answer" not in st.session_state:
        st.session_state["lito_answer"] = ""
    # サイドバーで認証とコスト表示
    with st.sidebar:
        st.subheader("🔑 無制限に使用できるようになる合言葉")
        input_key = st.text_input("合言葉を入力してください", type="password")
        is_admin = (input_key == st.secrets["ADMIN_PASSWORD"])
        
        if is_admin:
            st.success("管理者モード")
            user_id = "my_name"
        else:
            st.info("一般ユーザーモード")
            user_id = "guest"

        st.header("💰 OpenAI API利用状況")
        current_cost = get_db_cost()
        limit = 0.5
        st.metric("本日の利用額", f"${current_cost:.4f}")
        st.progress(min(current_cost / limit, 1.0))
        if current_cost >= limit and not is_admin:
            st.error("⚠️ 本日の上限に達しました")

    # 相談ジャンル選択
    worries_type = st.radio(
        "悩みのジャンルを選択してください:",
        ("健康", "心理", "仕事", "人間関係", "その他")
    )

    prompts = {
        "健康": "あなたは優秀な健康アドバイザーです。",
        "心理": "あなたは経験豊富な心理カウンセラーです。",
        "仕事": "あなたは優秀なキャリアコンサルタントです。",
        "人間関係": "あなたは熟練した人間関係の専門家です。",
        "その他": "あなたは親身な相談員です。"
    }
    if "lito_answer" not in st.session_state:
        st.session_state["lito_answer"] = ""
    user_input = st.text_input("質問を入力してください：")
    if st.button("送信") and user_input:
        if not is_allowed_before_api(user_id, limit):
            st.error("本日の予算を超えました。また明日相談してくださいね。")
        else:
            # 1. クライアントを初期化（ここでLLMを準備！）
            client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            
            with st.spinner("回答を生成中..."):
                try:
                    # 2. ここでLLMに「お願い」をする（response = ...）
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": prompts[worries_type]},
                            {"role": "user", "content": user_input}
                        ]
                    )
                    
                    # 3. 消費金額をDBに記録
                    save_new_cost(user_id, response.usage)
                    
                    # 4. 回答を画面に表示！
                    # 2. 回答を「記憶の箱」に覚えさせる！（ここが重要）
                    st.session_state["lito_answer"] = response.choices[0].message.content
                    
                    # 金額表示を更新するために再起動（これでも箱の中身は消えない！）
                    st.rerun() 
                except Exception as e:
                    st.error(f"エラー: {e}")

    # 3. ボタンの外（一番左のインデント）で、箱の中身を表示する！
    if st.session_state["lito_answer"]:
        st.subheader(f"【{worries_type}からの回答】")
        st.write(st.session_state["lito_answer"])
                    
if __name__ == "__main__":
    main()    