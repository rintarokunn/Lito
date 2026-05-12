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

# --- 2. メイン処理 ---

def main():
    init_db()
    st.title("お悩み相談アプリ - Lito")

    # サイドバーで認証とコスト表示
    with st.sidebar:
        st.subheader("🔑 認証")
        input_key = st.text_input("合言葉を入力してください", type="password")
        is_admin = (input_key == st.secrets["ADMIN_PASSWORD"])
        
        if is_admin:
            st.success("管理者モード")
            user_id = "my_name"
        else:
            st.info("一般ユーザーモード")
            user_id = "guest"

        st.header("💰 コスト管理")
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

    user_input = st.text_input("質問を入力してください：")
    if st.button("送信") and user_input:
        st.write("デバッグ：ボタンが押されました！") 
        if not is_allowed_before_api(user_id, limit):
            st.error("デバッグ：金額制限で止まりました")
            st.error("本日の予算を超えました。また明日相談してくださいね。")
            return

        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        with st.spinner("回答を生成中..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": prompts[worries_type]},
                        {"role": "user", "content": user_input}
                    ]
                )
                # 金額を保存
                save_new_cost(user_id, response.usage)
                
                st.subheader(f"【{worries_type}アドバイザーからの回答】")
                st.write(response.choices[0].message.content)
                # 金額表示を更新するために再描画（オプション）
                st.rerun()
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()