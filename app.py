import streamlit as st
import pandas as pd
import io

# --- パスワードロック機能 ---
password = st.text_input("パスワードを入力してください", type="password")

if password != "secret1234":
    st.warning("正しいパスワードを入力してください。")
    st.stop() 

# --- 認証成功後、ここからメインのアプリ画面 ---
st.success("ログイン成功！")

# 画面の幅を広く使う設定
st.set_page_config(layout="wide")

st.title('🤖 クラフィットハウス | 広告パフォーマンス自動判定')

# ==========================================
# 📘 評価基準まとめの表示（アコーディオンで開閉可能に）
# ==========================================
with st.expander("📖 クラフィットハウス 広告・LP評価基準まとめ（ここをクリックで開閉）", expanded=False):
    st.markdown("### ■ クラフィットハウス専用ベースライン")
    base_data = {
        "指標": ["CPA", "CVR（来場予約）", "確認の順番"],
        "基準値": ["¥30,000 以下", "0.3% 以上", "CPC → CTR → CVR → CPA"],
        "備考": [
            "これより低い場合、データ量不足/投下予算不足で機会損失している可能性。むしろ予算を伸ばせる余地あり",
            "LP単体の細かい数値より、広告経由のCPA・CVRのバランスを優先して判断する",
            "予約完了に学習を置いている前提での確認順"
        ]
    }
    st.table(pd.DataFrame(base_data))

    st.markdown("### ■ 切り分けロジック（広告 or LPどちらが問題か）")
    logic_data = {
        "状況": [
            "CTR(リンク)が1.0%前後を下回る/CPCが悪い",
            "クリックは取れているがCVRが基準(0.3%)を下回る",
            "CTRが高いのにCVRが低い"
        ],
        "判定": ["広告（クリエイティブ・ターゲット）の問題", "イベントページの問題の可能性", "即断しない"],
        "対処": [
            "クリエイティブ・ターゲティングを見直す",
            "ページ構成・導線・フォームを見直す",
            "ヒートマップ・スクロール率・離脱箇所を確認。同業者/既購入層が反応している可能性があり、ターゲット精度の問題をLPの問題と読み違えない"
        ]
    }
    st.table(pd.DataFrame(logic_data))
    
    st.markdown("### ▽ よくある事例")
    st.info("""
    * **CTRが高い → CVRが低い**なら興味だけをつっている
    * **CPCが安い → 来場予約につながらない**。ターゲットがずれている
    * **アクセス数UP → 予約率が下がった**ら質の低い流入が増えただけ
    * **CVRが高い → 来場が少なすぎる**（母数不足）の可能性
    """)

st.write("---") # 区切り線

# ==========================================
# 📊 CSVアップロードと自動判定ロジック
# ==========================================
st.write('Facebook広告のCSVをアップロードすると、上記の基準に基づいた判定を自動で行います。')

uploaded_file = st.file_uploader("CSVファイルをアップロードしてください", type='csv')

if uploaded_file is not None:
    df_csv = pd.read_csv(uploaded_file)
    df_clean = df_csv.dropna(subset=['広告名']).copy()

    df_clean['消化金額 (JPY)'] = df_clean['消化金額 (JPY)'].fillna(0)
    df_clean['インプレッション'] = df_clean['インプレッション'].fillna(0)
    df_clean['リンククリック'] = df_clean['リンククリック'].fillna(0)
    df_clean['結果'] = df_clean['結果'].fillna(0)

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

    st.subheader('📊 判定結果')
    res_df = df_clean.apply(calculate_metrics_and_judge, axis=1)
    res_df.columns = ['広告名', '配信ステータス', '消化金額', 'インプレッション', 'リンククリック', 'CTR(%)', 'CPC(円)', 'CV', 'CVR(%)', 'CPA(円)', '判定', 'コメント']
    
    st.dataframe(res_df, use_container_width=True)

    csv_buffer = io.StringIO()
    res_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig') 
    csv_content = csv_buffer.getvalue()

    st.download_button(
        label="📥 判定結果のCSVをダウンロード",
        data=csv_content,
        file_name="自動判定レポート.csv",
        mime="text/csv"
    )
