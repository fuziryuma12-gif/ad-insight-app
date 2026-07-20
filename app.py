import streamlit as st
import pandas as pd
import io
import openpyxl

# --- パスワードロック機能 ---
password = st.text_input("パスワードを入力してください", type="password")

if password != "secret1234":
    st.warning("正しいパスワードを入力してください。")
    st.stop()

# --- 認証成功後 ---
st.success("ログイン成功！")
st.set_page_config(layout="wide")

st.title('🤖 クラフィットハウス | 広告パフォーマンス自動判定')

with st.expander("📖 クラフィットハウス 広告・LP評価基準まとめ（ここをクリックで開閉）", expanded=False):
    st.markdown("※必要に応じてここに評価基準を表示できます（省略）")

st.write("---")

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

        # ★今回いただいた中西様邸のフォーマット（全14列）に合わせました★
        row_data = [
            index,           # 1: No
            ad_name,         # 2: クリエイティブ名
            reach,           # 3: リーチ
            freq,            # 4: フリークエンシー(FQ)
            imps,            # 5: インプレッション
            spend,           # 6: 消化金額(円)
            round(cpm, 0),   # 7: CPM(円)
            clicks,          # 8: リンククリック数
            round(ctr, 2),   # 9: CTR(リンク)
            round(cpc, 0),   # 10: CPC(リンク,円)
            cv,              # 11: 結果(CV)
            round(cpa, 0),   # 12: 結果の単価(CPA,円)
            judgement,       # 13: 判定
            comment          # 14: コメント
        ]
        processed_data.append(row_data)

    st.subheader('📊 判定結果プレビュー')
    preview_df = pd.DataFrame(processed_data, columns=["No", "クリエイティブ名", "リーチ", "FQ", "IMP", "消化金額", "CPM", "クリック", "CTR", "CPC", "CV", "CPA", "判定", "コメント"])
    st.dataframe(preview_df, use_container_width=True)

    try:
        wb = openpyxl.load_workbook("template.xlsx")
        ws = wb["クリエイティブ別"] 

        # 4行目からデータを書き込む
        start_row = 4
        for r_idx, row_data in enumerate(processed_data):
            for c_idx, val in enumerate(row_data):
                ws.cell(row=start_row + r_idx, column=c_idx + 1, value=val)

        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)

        st.download_button(
            label="📥 判定結果のエクセル(.xlsx)をダウンロード",
            data=excel_buffer,
            file_name="広告パフォーマンス自動判定.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except FileNotFoundError:
        st.error("⚠️ テンプレートファイルが見つかりません。GitHubに `template.xlsx` という名前でファイルがアップロードされているか確認してください。")
    except KeyError:
        st.error("⚠️ エクセルの中に「クリエイティブ別」という名前のシートが見つかりません。テンプレートの内容を確認してください。")
