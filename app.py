import streamlit as st
import pandas as pd
import time
import random
import re # 전화번호 추출용 정규식 라이브러리 추가
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

def get_industry_tag(category_text):
    if any(kw in category_text for kw in ['농장', '축산', '양돈', '계사', '목장']):
        return "축산업"
    elif any(kw in category_text for kw in ['제조', '공장', '산업', '금속', '기계']):
        return "제조업"
    elif any(kw in category_text for kw in ['주차', '시설', '공영']):
        return "시설업"
    return "기타"

def run_crawler(region, keyword, max_scroll=3):
    options = Options()
    
    # 서버 환경 안정성 최적화 옵션
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage") 
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # 봇 탐지 방지
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={user_agent}")

    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
        
    wait = WebDriverWait(driver, 10)
    
    data = []
    try:
        url = f"https://map.naver.com/v5/search/{region} {keyword}"
        driver.get(url)
        time.sleep(random.uniform(2, 4)) 
        
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "searchIframe")))
        
        for _ in range(max_scroll):
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, ".UE715")
                if elements:
                    driver.execute_script("arguments[0].scrollIntoView(true);", elements[-1])
                time.sleep(random.uniform(1.5, 2.5))
            except:
                break

        items = driver.find_elements(By.CSS_SELECTOR, ".UE715")
        
        for item in items:
            try:
                name = item.find_element(By.CSS_SELECTOR, ".TYpbg").text
                category = item.find_element(By.CSS_SELECTOR, ".K7094").text
                
                # [기능 추가] 텍스트 전체에서 전화번호 패턴 찾기 (정규식)
                text_content = item.text
                phone_match = re.search(r'(\d{2,4}-\d{3,4}-\d{4}|\d{4}-\d{4})', text_content)
                phone_number = phone_match.group(0) if phone_match else "번호 미등록"
                
                link_element = item.find_element(By.TAG_NAME, "a")
                place_id = link_element.get_attribute("href").split('/')[-1].split('?')[0]
                map_url = f"https://map.naver.com/p/entry/place/{place_id}"

                data.append({
                    "업체명": name,
                    "기존분류": category,
                    "산업태그": get_industry_tag(category),
                    "전화번호": phone_number, # 엑셀에 들어갈 열 추가!
                    "지도링크": map_url
                })
            except Exception:
                continue
                
    finally:
        if 'driver' in locals():
            driver.quit()
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.drop_duplicates(subset=['업체명'], keep='first')
    return df

# --- Streamlit UI ---
st.set_page_config(page_title="영업 섭외 DB 추출기", layout="wide")
st.title("📍 지역별 타겟 업체 DB 수집기")
st.markdown("네이버 지도를 기반으로 섭외할 업체의 리스트를 추출하고 엑셀로 다운로드합니다.")

col1, col2 = st.columns(2)
with col1:
    region = st.text_input("지역 입력 (예: 포천시, 경기 광주)", "김천")
with col2:
    keyword = st.text_input("검색 키워드 (예: 양돈농장, 공영주차장, 공단)", "양돈농장")

scroll_cnt = st.slider("검색 깊이 (스크롤 횟수 - 높을수록 오래 걸림)", 1, 10, 6)

if st.button("데이터 추출 시작", type="primary"):
    with st.spinner('서버에서 네이버 지도를 탐색 중입니다... (데이터 양에 따라 1~3분 소요)'):
        df = run_crawler(region, keyword, max_scroll=scroll_cnt)
        
        if not df.empty:
            st.success(f"총 {len(df)}건의 고유 데이터를 성공적으로 추출했습니다!")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 엑셀(CSV) 파일로 저장하기",
                data=csv,
                file_name=f"섭외DB_{region}_{keyword}.csv",
                mime="text/csv"
            )
        else:
            st.error("데이터를 찾지 못했거나 일시적으로 접근이 지연되었습니다. 잠시 후 다시 시도해주세요.")
