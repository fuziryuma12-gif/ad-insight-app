import streamlit as st
import pandas as pd
import io
import openpyxl
from openpyxl.styles import Border, Side
import os

# ==========================================
# 🔐 パスワード管理機能
# ==========================================
PW_FILE = "password.txt"

def get_password():
    if os.path.exists(PW_FILE):
        with open(PW_FILE, "r") as f:
            return f.read().strip()
    return "secret1234" # 初期パスワード

def set_password(new_pw):
    with open(PW_FILE, "w") as f:
        f.write(new_pw)

current_password = get_password()

# ページ設定
st.set_page_config(layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# 未ログイン時の画面
if not st.session_state.logged_in:
    password_input = st.text_input("パスワードを入力してください", type="password")
    if password_input:
        if password_input == current_password:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.warning("正しいパスワードを入力してください。")
    st.stop()

# ==========================================
# 📱 メインアプリ画面（ログイン成功後）
# ==========================================
st.success("ログイン成功！")

# ⚙️ パスワード変更UI（アコーディオン）
with st.expander("⚙️ パスワードの変更（管理者用）", expanded=False):
    new_password = st.text_input("新しいパスワードを入力してください", type="password")
    if st.button("パスワードを更新"):
        if new_password:
            set_password(new_password)
            st.success("パスワードを変更しました！次回のログインから有効になります。")
        else:
            st.error("パスワードを入力してください。")

st.title('🤖 クラフィットハウス | 広告パフォーマンス自動判定')

with st.expander("📖 クラフィットハウス 広告・LP評価基準まとめ", expanded=False):
    st.markdown("※必要に応じてここに評価基準を表示できます")

st.write("---")

# CSVアップロード
uploaded_file = st.file_uploader("Facebook広告のCSVをアップロードしてください", type='csv')

if uploaded_file is not None:
    df_csv = pd.read_csv(uploaded_file)
    df_clean = df_csv.dropna(subset=['広告名']).copy()

    # 欠損値を0で埋める
    cols_to_fill = ['消化金額 (JPY)', 'インプレッション', 'リンククリック', '結果', 'リーチ', 'フリークエンシー', 'CPM(インプレッション単価) (JPY)']
    for col in cols_to_fill:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].fillna(0)

    processed_data = []

    for index, row in enumerate(df_clean.to_dict('records'), start=1):
        ad_name = row.get('広告名', '')
        spend = row.get('消化金額 (JPY)', 0)
        imps = row.get('インプレッション', 0)
        clicks = row.get('リンククリック', 0)
        cv = row.get('結果', 0)
        reach = row.get('リーチ', 0)
        freq = row.get('フリークエンシー', 0)
        cpm = row.get('CPM(インプレッション単価) (JPY)', 0)

        ctr = (clicks / imps * 100) if imps > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        cvr = (cv / clicks * 100) if clicks > 0 else 0
        cpa = (spend / cv) if cv > 0 else 0

        judgement = "良好"
        comment = "現状のまま配信を継続"

        if ctr < 1.0:
            judgement = "広告の問題"
            comment = "CTRが1.0%未満です。クリエイティブ等を見直してください。"
        elif cvr < 0.3 and clicks >= 10:
            judgement = "LPの問題の可能性"
            comment = "CVRが0.3%を下回っています。LPを見直してください。"
        elif cpa > 30000 or (cv == 0 and spend > 30000):
            judgement = "予算超過/停止推奨"
            comment = "CPAが3万円を超えている、もしくはCVゼロで3万円以上消化しています。"

        # 中西様邸フォーマット
        row_data = [
            index, ad_name, reach, freq, imps, spend, round(cpm, 0), 
            clicks, round(ctr, 2), round(cpc, 0), cv, round(cpa, 0), judgement, comment
        ]
        processed_data.append(row_data)

    st.subheader('📊 判定結果プレビュー')
    preview_df = pd.DataFrame(processed_data, columns=["No", "クリエイティブ名", "リーチ", "FQ", "IMP", "消化金額", "CPM", "クリック", "CTR", "CPC", "CV", "CPA", "判定", "コメント"])
    st.dataframe(preview_df, use_container_width=True)

    # ==========================================
    # 📝 エクセル出力＆ダウンロード機能
    # ==========================================
    st.write("---")
    st.subheader("📥 レポートのダウンロード")
    
    # 1. ファイル名の入力欄
    output_filename = st.text_input("出力するファイル名を入力してください", value="中西様邸_広告パフォーマンスレポート")

    try:
        wb = openpyxl.load_workbook("template.xlsx")
        ws = wb["クリエイティブ別"] 

        # 罫線の設定（実線）
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'), 
            top=Side(style='thin'), bottom=Side(style='thin')
        )

        # 4行目からデータを書き込み、同時に罫線を引く
        start_row = 4
        for r_idx, row_data in enumerate(processed_data):
            for c_idx, val in enumerate(row_data):
                cell = ws.cell(row=start_row + r_idx, column=c_idx + 1, value=val)
                cell.border = thin_border # ★ここでセルに線を引いています

        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        # 2. 入力されたファイル名でダウンロード
        st.download_button(
            label="📊 エクセル(.xlsx)をダウンロード",
            data=excel_buffer,
            file_name=f"{output_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except FileNotFoundError:
        st.error("⚠️ テンプレートファイルが見つかりません。GitHubに `template.xlsx` がアップロードされているか確認してください。")
    except KeyError:
        st.error("⚠️ エクセルの中に「クリエイティブ別」というシートが見つかりません。")
