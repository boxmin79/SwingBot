import pandas as pd
import json
import os
import re

def parse_kiwoom_excel_to_json(file_path):
    """
    엑셀 파일(Request 테이블에 Header/Body가 공존하는 형태)을 분석하여
    params.json을 생성합니다.
    """
    if not os.path.exists(file_path):
        print(f"❌ 오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return

    print(f"📂 파일 분석 시작: {file_path}")
    final_data = {}

    try:
        # 1. 엑셀 로드 (모든 시트)
        all_sheets = pd.read_excel(file_path, sheet_name=None, header=None)

        for sheet_name, df in all_sheets.items():
            # 제외할 시트
            if any(x in sheet_name for x in ["목차", "Index", "History", "Sample", "오류"]):
                continue

            # NaN(빈값)을 빈 문자열 ""로 변환
            df = df.fillna("")

            # ---------------------------------------------------
            # A. 메타 데이터 (ID, Name, URL) 추출
            # ---------------------------------------------------
            api_info = {"api_id": "", "name": "", "endpoint": ""}
            
            table_header_row_idx = -1
            col_idx_map = {"element": -1, "section": -1} # element:변수명, section:구분(Header/Body)

            # 시트 상단 탐색
            for i, row in df.iterrows():
                row_list = [str(val).strip() for val in row.tolist()]
                row_str = " ".join(row_list)

                # API ID (예: ka00001)
                if not api_info["api_id"]:
                    for item in row_list:
                        if re.match(r'^[a-z]{2}\d{5}$', item):
                            api_info["api_id"] = item
                            break
                
                # API 명칭
                if "API 명" in row_str and not api_info["name"]:
                    try:
                        idx = -1
                        for k, cell in enumerate(row_list):
                            if "API 명" in cell: idx = k; break
                        if idx != -1:
                            for check_cell in row_list[idx+1:]:
                                if check_cell: api_info["name"] = check_cell; break
                    except: pass

                # URL
                if "URL" in row_str and "/" in row_str and not api_info["endpoint"]:
                    for item in row_list:
                        if item.startswith("/") or item.startswith("http"):
                            api_info["endpoint"] = item
                            break

                # 테이블 헤더 찾기 (이미지의 "구분", "Element" 찾기)
                # "Element"가 있고 "구분"이 있는 행을 찾음
                if "Element" in row_list and "구분" in row_list:
                    table_header_row_idx = i
                    # 컬럼 위치 저장
                    for c_idx, val in enumerate(row_list):
                        if val == "Element":
                            col_idx_map["element"] = c_idx
                        elif val == "구분":
                            col_idx_map["section"] = c_idx
                    break

            # API ID가 없으면 스킵
            if not api_info["api_id"]:
                continue

            # ---------------------------------------------------
            # B. 데이터 구조 초기화
            # ---------------------------------------------------
            result_obj = {
                "api_id": api_info["api_id"],
                "name": api_info["name"],
                "endpoint": api_info["endpoint"],
                "headers": {},
                "body": {}
            }
            
            # Content-Type은 기본적으로 넣어줌 (엑셀에 없더라도)
            result_obj["headers"]["Content-Type"] = "application/json;charset=UTF-8"

            # ---------------------------------------------------
            # C. Request 테이블 파싱 (Header/Body 구분 로직)
            # ---------------------------------------------------
            if table_header_row_idx != -1:
                current_section = "Body" # 기본값 (혹시 구분이 안 적혀있을 경우 대비)
                
                # 헤더 다음 행부터 데이터 읽기
                for i in range(table_header_row_idx + 1, len(df)):
                    row = df.iloc[i]
                    row_list = [str(val).strip() for val in row.tolist()]
                    
                    # 멈춤 조건 ("Response" 섹션 시작 시)
                    if any(stop in row_list[0] for stop in ["Response", "Output", "응답", "출력"]):
                        break

                    # 인덱스 가져오기
                    elt_idx = col_idx_map["element"]
                    sec_idx = col_idx_map["section"]
                    
                    if elt_idx == -1: continue

                    element_name = row_list[elt_idx]
                    section_val = row_list[sec_idx] if sec_idx != -1 else ""

                    # 1. 구분 값(Header/Body) 갱신 로직 (엑셀 셀 병합 대응)
                    # "Header"라고 적혀있으면 섹션 변경, 빈칸이면 이전 섹션 유지
                    if section_val.lower() in ["header", "헤더"]:
                        current_section = "header"
                    elif section_val.lower() in ["body", "바디"]:
                        current_section = "body"
                    
                    # 변수명이 없으면 스킵 (빈 줄)
                    if not element_name:
                        continue

                    # 2. 값 생성 ({변수명} 형태)
                    # 예외: api-id는 실제 ID값, grant_type 등은 고정값
                    param_value = f"{{{element_name}}}"
                    
                    if element_name == "api-id":
                        param_value = api_info["api_id"] # {api-id} 대신 실제 id(ka00001) 입력
                    elif element_name == "grant_type":
                        param_value = "client_credentials"
                    elif element_name == "ACNT_PRDT_CD": # 상품코드
                         param_value = "01"

                    # 3. 현재 섹션에 따라 저장
                    if current_section == "header":
                        # Content-Type은 중복 방지
                        if element_name.lower() != "content-type":
                            result_obj["headers"][element_name] = param_value
                    else:
                        # body 섹션
                        result_obj["body"][element_name] = param_value

            # 결과 저장
            final_data[api_info["api_id"]] = result_obj
            print(f"✅ [{api_info['api_id']}] 생성 완료 - {api_info['name']}")

        # ---------------------------------------------------
        # D. 파일 쓰기
        # ---------------------------------------------------
        output_path = os.path.join(os.path.dirname(__file__), 'params.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)

        print("-" * 40)
        print(f"🎉 params.json 생성 완료! ({output_path})")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 엑셀 파일명 (경로에 맞게 수정하세요)
    target_files = ["키움 REST API 문서.xlsx", "API.xlsx"]
    
    file_path = None
    for fname in target_files:
        temp_path = os.path.join(os.path.dirname(__file__), fname)
        if os.path.exists(temp_path):
            file_path = temp_path
            break
            
    if file_path:
        parse_kiwoom_excel_to_json(file_path)
    else:
        print("엑셀 파일을 찾을 수 없습니다.")