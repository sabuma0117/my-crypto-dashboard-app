import streamlit as st
import requests
import feedparser # feedparserを追加
import json
import time
from datetime import datetime

# --- 設定項目 ---
# 価格取得コインID (デフォルト)
default_coin_ids = ['ethereum', 'solana', 'sui', 'ondo-finance']
# ニュースフィルタリングキーワード (デフォルト)
default_keywords = [
    'eth', 'ethereum', 'sol', 'solana', 'sui', 'ondo', 'bitcoin', 'btc',
    '規制', 'アップデート', 'nft', 'defi', 'web3', 'バイナンス',
]
# ニュース取得元RSSフィード
rss_feeds = {
    "CoinTelegraph Japan": "https://jp.cointelegraph.com/rss",
    "あたらしい経済": "https://www.neweconomy.jp/feed",
}
# ニュース取得/表示設定
max_entries_to_fetch = 20
max_entries_to_display = 10
# User-Agentヘッダー
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}
# --- 設定項目ここまで ---

# --- 関数定義 ---
# (get_price_data関数は前回と同じなので省略)
@st.cache_data(ttl=600) # データ取得結果を10分間キャッシュする
def get_price_data(coin_ids):
    """CoinGecko APIから価格情報を取得する関数 (Streamlit版)"""
    price_data_list = []
    if not coin_ids: return [] # 対象がなければ空リスト

    st.write("価格情報 取得中...")
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=jpy&ids={','.join(coin_ids)}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            for coin_data in data:
                 price_info = {
                     'id': coin_data.get('id', 'N/A'),
                     'name': coin_data.get('name', 'N/A'),
                     'current_price': coin_data.get('current_price', 0),
                     'price_change_percentage_24h': coin_data.get('price_change_percentage_24h', 0),
                     'market_cap': coin_data.get('market_cap', 0)
                 }
                 price_data_list.append(price_info)
            st.success("価格情報 取得完了！")
            return price_data_list
        else:
            st.error(f"エラー: 指定されたコインID ({','.join(coin_ids)}) の価格データが見つかりません。")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"価格APIエラー: {e}")
        return []
    except Exception as e:
        st.error(f"価格API予期せぬエラー: {e}")
        return []


# --- ★★★ ニュース取得関数 (Streamlit版) を追加 ★★★ ---
@st.cache_data(ttl=600) # データ取得結果を10分間キャッシュする
def get_filtered_news(keywords):
    """RSSフィードからニュースを取得しフィルタリングする関数 (Streamlit版)"""
    filtered_news_list = []
    if not keywords: return [] # キーワードがなければ空リスト

    st.write("\nニュース 取得・フィルタリング中...")
    total_fetched_count = 0

    for site_name, feed_url in rss_feeds.items():
        # st.write(f"[{site_name}] 処理中...") # 詳細ログはコメントアウトしてもOK
        feed_content = None
        try:
            response = requests.get(feed_url, headers=headers, timeout=15)
            response.raise_for_status()
            feed_content = response.text
        except requests.exceptions.RequestException as e:
            st.warning(f"ニュース取得エラー ({site_name}): {e}") # エラーではなく警告に変更
            continue
        except Exception as e:
             st.warning(f"ニュース取得予期せぬエラー ({site_name}): {e}")
             continue

        if feed_content:
            try:
                parsed_data = feedparser.parse(feed_content)
                if parsed_data.bozo:
                     st.warning(f"フィード解析に問題あり ({site_name}) - {parsed_data.bozo_exception}")

                if not parsed_data.entries:
                     # st.write(f"記事データなし ({site_name})") # ログは省略可
                     continue

                for entry in parsed_data.entries[:max_entries_to_fetch]:
                    title = entry.get('title', '')
                    link = entry.get('link', '#')
                    title_lower = title.lower()
                    matched_keyword = ""
                    for keyword in keywords: # 引数で受け取ったキーワードを使用
                        if keyword in title_lower:
                            matched_keyword = keyword
                            break

                    if matched_keyword:
                        published_time_str = "日時不明"
                        published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
                        if published_parsed:
                            try:
                                published_time_str = time.strftime('%Y-%m-%d %H:%M', published_parsed)
                            except ValueError:
                                published_time_str = "不正な日時"

                        filtered_news_list.append({
                            'site': site_name,
                            'keyword': matched_keyword,
                            'title': title,
                            'link': link,
                            'published': published_time_str
                        })
                        total_fetched_count += 1
            except Exception as e:
                st.warning(f"ニュース解析エラー ({site_name}): {e}")

    # ソート処理 (前回同様)
    def get_sort_key(news_item):
        try:
            return datetime.strptime(news_item.get('published', ''), '%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
             return datetime.min
    filtered_news_list.sort(key=get_sort_key, reverse=True)

    st.success(f"関連ニュース {len(filtered_news_list)}件 収集完了！")
    return filtered_news_list
# --- ★★★ 関数追加ここまで ★★★ ---


# --- Streamlit アプリケーションのメイン部分 ---

st.set_page_config(page_title="仮想通貨情報ダッシュボード", layout="wide")
st.title('🚀 仮想通貨情報ダッシュボード')

# --- サイドバー (設定用) ---
st.sidebar.header('⚙️ 設定')
# コインID入力 (複数選択可能にする場合は st.multiselect が便利だが、まずはテキスト入力)
coin_ids_input = st.sidebar.text_input('価格取得コインID (カンマ区切り)', value=','.join(default_coin_ids))
coin_ids_to_fetch = [coin_id.strip() for coin_id in coin_ids_input.split(',') if coin_id.strip()]
if not coin_ids_to_fetch:
    st.sidebar.warning("コインIDが指定されていません。デフォルト値を使用します。")
    coin_ids_to_fetch = default_coin_ids

# キーワード入力
keywords_input = st.sidebar.text_input('ニュースフィルタリングキーワード (カンマ区切り)', value=','.join(default_keywords))
keywords_to_use = [keyword.strip().lower() for keyword in keywords_input.split(',') if keyword.strip()]
if not keywords_to_use:
    st.sidebar.warning("キーワードが指定されていません。デフォルト値を使用します。")
    keywords_to_use = default_keywords

# --- メインコンテンツ ---

# --- 価格表示 ---
st.header('📈 価格情報')
# 更新ボタン
if st.button('🔄 データ更新'):
    # キャッシュをクリアして再実行 (st.cache_data を使っている場合)
    st.cache_data.clear()
    st.experimental_rerun()

price_data = get_price_data(coin_ids_to_fetch) # 入力されたコインIDを渡す

if price_data:
    cols = st.columns(4)
    col_index = 0
    for price_info in price_data:
        current_col = cols[col_index % len(cols)]
        current_col.metric(
            label=f"{price_info.get('name', 'N/A')} ({price_info.get('id', 'N/A').capitalize()})",
            value=f"{price_info.get('current_price', 0):,.2f} JPY",
            delta=f"{price_info.get('price_change_percentage_24h', 0):.2f}%"
        )
        col_index += 1
    # 詳細データ表示 (オプション)
    with st.expander("詳細価格データを表示"):
        st.dataframe(price_data, use_container_width=True)
else:
    st.warning('価格データを表示できませんでした。')


# --- ★★★ ニュース表示を追加 ★★★ ---
st.header('📰 関連ニュース')
st.write(f"(キーワード: {', '.join(keywords_to_use)})")

# ニュースデータを取得 (入力されたキーワードを渡す)
news_data = get_filtered_news(keywords_to_use)

if news_data:
    # 表示上限までのニュースを表示
    for i, news_item in enumerate(news_data[:max_entries_to_display]):
        site = news_item.get('site', '不明サイト')
        keyword = news_item.get('keyword', '')
        title = news_item.get('title', 'タイトル不明')
        link = news_item.get('link', '#')
        published = news_item.get('published', '日時不明')

        # st.expanderを使うと、クリックで詳細（リンク）を表示できる
        with st.expander(f"[{site} / {keyword}] ({published}) {title}"):
            st.markdown(f"[{link}]({link})") # markdown形式でリンクを表示

    if len(news_data) > max_entries_to_display:
         st.caption(f"（全{len(news_data)}件中、最新{max_entries_to_display}件を表示）")

else:
    st.info('関連ニュースは見つかりませんでした。')
# --- ★★★ ニュース表示ここまで ★★★ ---


# --- フッター的な情報 ---
st.sidebar.write("---")
st.sidebar.write(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")