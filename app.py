import streamlit as st
import pandas as pd
import io

# --- パスワードロック機能 ---
password = st.text_input("パスワードを入力してください", type="password")

if password != "secret1234":
    st.warning("正しいパスワードを入力してください。")
    st.stop() # パスワードが違う場合はここで画面の描画を止める

# --- 認証成功後、ここからメインのアプリ画面 ---
st.success("ログイン成功！")

# アプリのタイトル
st.title('🤖 広告パフォーマンス自動判定アプリ')
st.write('Facebook広告のCSVをアップロードすると、基準に基づいた判定を自動で行います。')

# 1. ファイルアップロード機能
uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type='csv')

if uploaded_file is not None:
    # 2. アップロードされたCSVを読み込む
    df_csv = pd.read_csv(uploaded_file)
    df_clean = df_csv.dropna(subset=['広告名']).copy()

    # 空白を0で埋める
    df_clean['消化金額 (JPY)'] = df_clean['消化金額 (JPY)'].fillna(0)
    df_clean['インプレッション'] = df_clean['インプレッション'].fillna(0)
    df_clean['リンククリック'] = df_clean['リンククリック'].fillna(0)
    df_clean['結果'] = df_clean['結果'].fillna(0)

    # 判定ロジックの関数
    def calculate_metrics_and_judge(row):
        ad_name = row['広告名']
        status = row['広告配信']
        spend = row['消化金額 (JPY)']
        imps = row['インプレッション']
        clicks = row['リンククリック']
        cv = row['結果']
        
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
            
        return pd.Series([ad_name, status, spend, imps, clicks, round(ctr, 2), round(cpc, 0), cv, round(cvr, 2), round(cpa, 0), judgement, comment])

    # 3. データの処理と画面表示
    st.subheader('📊 判定結果')
    res_df = df_clean.apply(calculate_metrics_and_judge, axis=1)
    res_df.columns = ['広告名', '配信ステータス', '消化金額', 'インプレッション', 'リンククリック', 'CTR(%)', 'CPC(円)', 'CV', 'CVR(%)', 'CPA(円)', '判定', 'コメント']
    
    # 画面に表を表示
    st.dataframe(res_df)

    # 4. CSVダウンロード機能
    csv_buffer = io.StringIO()
    # 日本語の文字化けを防ぐために utf-8-sig を指定
    res_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig') 
    csv_content = csv_buffer.getvalue()

    st.download_button(
        label="📥 判定結果のCSVをダウンロード",
        data=csv_content,
        file_name="自動判定レポート.csv",
        mime="text/csv"
    )
