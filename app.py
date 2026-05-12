from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
#SQLiteを使うためのライブラリ
import sqlite3
#日付と時間を扱うためのライブラリ
import datetime
#openaiを使うためのライブラリ
from openai import OpenAI 
from datetime import datetime


def get_db_connection():
    conn = sqlite3.connect('lito.db', check_same_thread=False)
    return conn

#データベースとつなげるための関数をていぎします。これで、データベースにアクセスするためのコードを簡単に再利用できるようになります。
def init_db():
    conn = sqlite3.connect("lito.db", check_same_thread=False)
    c = conn.cursor()
    # ここに「api_usage」テーブルを作る命令を足す！
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_usage (
            date TEXT PRIMARY KEY,
            total_cost REAL DEFAULT 0.0
        )
    ''')
    conn.commit()
    conn.close()

# gpt-4o-miniの現在の料金（2026年時点の最新価格をご確認ください）
# ※ここでは例として、入力$0.15/1M, 出力$0.60/1Mトークンで計算
PRICE_PER_TOKEN_INPUT = 0.150 / 1_000_000
PRICE_PER_TOKEN_OUTPUT = 0.600 / 1_000_000

def is_allowed_before_api(user_id, total_cost_limit=0.5):
    """APIを叩く前に、すでに上限金額を超えていないかチェックする"""
# 自分（管理者）は無条件でパス
    if user_id == "my_name":
        print("--- 管理者モード：無制限 ---")
        return True

    today = datetime.now().strftime("%Y-%m-%d")
    current_cost = get_db_cost()
# 既に上限に達している場合は、APIを叩かずに即ブロック
    if current_cost >= total_cost_limit:
        print(f"【エラー】本日の一般利用の上限金額（${total_cost_limit}）に達したため、APIを呼び出せません。")
        return False
    return True

def save_new_cost(user_id, usage):
    """API実行後に、消費したトークン分の金額を記録する"""
    if user_id == "my_name":
        return

    today = datetime.now().strftime("%Y-%m-%d")
    current_cost = get_db_cost()

# 今回の正確な利用料金を計算
    call_cost = (usage.prompt_tokens * PRICE_PER_TOKEN_INPUT) + \
                (usage.completion_tokens * PRICE_PER_TOKEN_OUTPUT)
    new_cost = current_cost + call_cost

# データベースに最新の合計金額を書き込み
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO api_usage (date, total_cost) VALUES (?, ?)", (today, new_cost))
    conn.commit()
    conn.close()

    print(f"一般利用：本日の累計金額は ${new_cost:.4f} です。")

# --- API実行部分 ---
client = OpenAI()

def ask_ai(user_id, prompt):
# 【ステップ1】APIを叩く前に金額チェック（超えていたらここで処理終了）
    if not is_allowed_before_api(user_id, total_cost_limit=0.5):
        return

# 【ステップ2】制限内、または自分であればAPIを呼び出す
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
)

# 【ステップ3】使った分の金額をファイルに加算
    save_new_cost(user_id, response.usage)

    print("AIの回答:", response.choices.message.content)

def get_db_cost():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    c = conn.cursor()
    
    # api_usageテーブルから、dateがtodayと一致するtotal_costを1つ取ってくる命令
    c.execute("SELECT total_cost FROM api_usage WHERE date = ?", (today,))
    
    result = c.fetchone()
    conn.close()
    
    # resultに中身があればその値(result[0])を、なければ0.0を返したい
    return result[0] if result else 0.0

#------------------------------------------ # OpenAI UI # -----------------------------------------

with st.sidebar:
    st.subheader("🔑 認証")
    input_key = st.text_input("合言葉を入力してください", type="password")
    st.header("💰 コスト管理")
    current_cost = get_db_cost() # さっき作った金庫から取る関数！
    limit = 0.5
    
    # メトリック（数字）で表示
    st.metric("本日の利用額", f"${current_cost:.4f}", delta=f"上限まで残り ${limit - current_cost:.4f}")
    
    # プログレスバーで視覚的に表示
    percent = min(current_cost / limit, 1.0)
    st.progress(percent)
    
    if current_cost >= limit:
        st.error("⚠️ 本日の上限に達しました")

# 合言葉が合っているかチェック
is_admin = (input_key == st.secrets["ADMIN_PASSWORD"])

# 合言葉が合っていれば管理者モード、そうでなければ一般ユーザーモード
if is_admin:
    st.sidebar.success("管理者モードでログイン中")
    user_id = "my_name"  # これでAPI制限をパス！
else:
    st.sidebar.info("一般ユーザーモード")
    user_id = "guest"    # こっちは制限がかかる！


# OpenAIクライアント初期化
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])



# .envファイルから環境変数を読み込み
load_dotenv()

def main():
    init_db()
    st.title("お悩み相談アプリ - Lito")
    
    current_cost = get_db_cost()
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
                # 呼び出し（invokeを使用）
                result = llm.invoke(messages)
                
                st.subheader(f"【{worries_type}からの回答】")
                st.write(result.content)
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()