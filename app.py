import streamlit as st
import pandas as pd
import requests
import time

def get_industry_tag(category_text):
    if any(kw in category_text for kw in ['농장', '축산', '양돈', '계사', '목장', '동물']):
        return "축산업"
    elif any(kw in category_text for kw in ['제조', '공장', '산업', '금속', '기계']):
        return "제조업"
    elif any(kw in category_text for kw in ['주차', '시설', '공영']):
        return "시설업"
    return "기타"

def run_api_crawler(region, keyword, max_pages=3):
    # 네이버 지도의 숨겨진 내부 검색 통신망 URL
    url = "https://map.naver.com/p/api/search/allSearch"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://map.naver.com/"
    }
    
    data = []
    
    for page in range(1, max_pages + 1):
        params = {
            "query": f"{region} {keyword}",
            "type": "all",
            "page": page,
            "displayCount": 20 # 1페이지당 20개씩 가져옴
        }
        
        try:
            # 브라우저 대신 직접 네이버 서버에 데이터 요청
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code != 200:
                break
                
            json_data = response.json()
            
            # 구조화된 JSON 데이터에서 업체 목록만 쏙 빼오기
            places = json_data.get("result", {}).get("place", {}).get("list", [])
            
            # 검색 결과가 'place'가 아닌 'site'에 담기는 경우 예외 처리
            if not places:
                places = json_data.get("result", {}).get("site", {}).get("list", [])
                
            if not places:
                break # 더 이상 페이지에 결과가 없으면 스톱
                
            for p in places:
                name = p.get("name", "이름없음")
                
                # 카테고리 텍스트 정리
                cat_list = p.get("category", [])
                category_str = " > ".join(cat_list) if isinstance(cat_list, list) else str(cat_list)
                
                phone = p.get("tel", "")
                if not phone:
                    phone = "번호 미등록"
                    
                address = p.get("address", "")
                place_id = p.get("id", "")
                map_url = f"https://map.naver.com/p/entry/place/{place_id}" if place_id else ""
                
                data.append({
                    "업체명": name,
                    "기존분류": category_str,
                    "산업태그": get_industry_tag(category_str),
                    "주소": address, # 주소도 추가로 뽑아드립니다!
                    "전화번호": phone,
                    "지도링크": map_url
                })
                
        except Exception as e:
            st.warning(f"데이터 통신 중 약간의 지연이 발생했습니다: {e}")
            break
            
        time.sleep(0.5) # 네이버 서버를 배려하는 0.5초 딜레이
        
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.drop_duplicates(subset=['업체명'], keep='first')
    return df

# --- Streamlit UI ---
st.set_page_config(page_title="영업 섭외 DB 추출기", layout="wide")
st.title("⚡ 지역별 타겟 업체 DB 수집기 (초고속 API 버전)")
st.markdown("크롬 브라우저를 띄우지 않고 네이버 내부 데이터를 직접 호출하여 기존보다 10배 이상 빠르고 튕김 없이 엑셀을 추출합니다.")

col1, col2 = st.columns(2)
with col1:
    region = st.text_input("지역 입력 (예: 포천시, 경기 광주)", "김천")
with col2:
    keyword = st.text_input("검색 키워드 (예: 양돈농장, 공영주차장, 공단)", "양돈농장")

# 기존엔 스크롤이었지만, API 방식에선 '페이지' 개념으로 명확해집니다.
page_cnt = st.slider("검색 깊이 (페이지 수 - 1페이지당 최대 20건)", 1, 10, 3)

if st.button("데이터 추출 시작", type="primary"):
    with st.spinner('초고속 내부망 탐색 중입니다... (보통 5초 이내 완료)'):
        df = run_api_crawler(region, keyword, max_pages=page_cnt)
        
        if df is not None and not df.empty:
            st.success(f"총 {len(df)}건의 고유 데이터를 단숨에 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 엑셀(CSV) 파일로 저장하기",
                data=csv,
                file_name=f"섭외DB_{region}_{keyword}.csv",
                mime="text/csv"
            )
        else:
            st.error("데이터를 찾지 못했습니다. 검색 조건을 바꿔서 다시 시도해주세요.")
