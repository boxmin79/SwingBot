import requests
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# .env 파일 로드
load_dotenv()

class KiwoomAPI():
    def __init__(self):
        self.host = 'https://mockapi.kiwoom.com'
        self.api_params = self._load_api_params()
        self.app_key = os.getenv("MOCK_APP_KEY")
        self.secret_key = os.getenv("MOCK_SECRET_KEY")
        
        # .env 체크
        if not self.app_key or not self.secret_key:
            print("\n[설정 오류] .env 파일에서 MOCK_APP_KEY와 MOCK_SECRET_KEY를 확인해주세요.")

    def _token_manager(self):
        """토큰 유효성을 검사하고 유효한 토큰 문자열을 반환합니다."""
        token_file = os.path.join(os.path.dirname(__file__), "token.json")
        
        # 1. 파일 확인
        if os.path.exists(token_file):
            try:
                with open(token_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    expires_dt = datetime.strptime(data.get('expires_dt'), '%Y-%m-%d %H:%M:%S')
                    token = data.get('token')
                    
                    # 유효기간이 남았으면 토큰 반환
                    if expires_dt > datetime.now():
                        return token
            except Exception as e:
                print(f"[오류] 토큰 파일 읽기 중 에러: {e}")

        # 2. 만료되었거나 파일이 없으면 재발급
        print("[정보] 토큰이 없거나 만료되어 신규 발급을 시도합니다.")
        return self._issue_new_token(token_file)

    def _issue_new_token(self, token_file):
        """au10001 API를 호출하여 새 토큰을 발급받고 파일에 저장합니다."""
        api_id = "au10001"
        if api_id not in self.api_params:
            print("[오류] params.json에 'au10001' 정보가 없습니다.")
            return None

        # params.json에서 정보 로드
        api_info = self.api_params[api_id]
        url = self.host + api_info.get("endpoint")
        
        # 헤더 설정 (Content-Type 등)
        headers = api_info.get("headers", {}).copy()
        
        # 바디 설정
        payload = {
            "appkey": self.app_key,
            "secretkey": self.secret_key,
            "grant_type": "client_credentials"
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                res_json = response.json()
                token = res_json.get("token")
                expires_in = res_json.get("expires_in", 86400) # 기본값 24시간
                
                # 만료 시간 계산
                new_expires_dt = (datetime.now() + timedelta(seconds=int(expires_in))).strftime('%Y-%m-%d %H:%M:%S')

                # 파일 저장
                with open(token_file, 'w', encoding='utf-8') as f:
                    json.dump({'token': token, 'expires_dt': new_expires_dt}, f, indent=4, ensure_ascii=False)
                
                print(f"[성공] 새 토큰 발급 완료: {token[:10]}...")
                return token
            else:
                print(f"[오류] 토큰 발급 요청 실패: {response.status_code}")
                print(response.text)
                return None
        except Exception as e:
            print(f"[예외] 토큰 발급 중 예외 발생: {e}")
            return None

    def _fill_params(self, template_dict, **kwargs):
        """
        params.json의 템플릿 딕셔너리 값({key})을 kwargs 값으로 치환합니다.
        template_dict: {"CANO": "{CANO}", "PDNO": "{stock_code}"}
        kwargs: {"CANO": "12345678", "stock_code": "005930"}
        return: {"CANO": "12345678", "PDNO": "005930"}
        """
        filled_dict = template_dict.copy()
        
        for key, val in filled_dict.items():
            # 값이 "{...}" 형태인 문자열인지 확인
            if isinstance(val, str) and val.startswith("{") and val.endswith("}"):
                placeholder_key = val[1:-1] # 중괄호 제거 (예: stock_code)
                
                # 1. kwargs에 해당 키가 있으면 교체
                if placeholder_key in kwargs:
                    filled_dict[key] = kwargs[placeholder_key]
                
                # 2. kwargs에 없으면 그대로 두거나, 필요시 빈 문자열로 처리
                # (여기서는 그대로 둠, 나중에 디버깅 용이)
        
        return filled_dict

    def _get_response(self, api_id, **kwargs):
        """
        API 호출 메인 함수.
        params.json의 정의에 따라 헤더와 바디를 구성하고 요청을 보냅니다.
        """
        if api_id not in self.api_params:
            print(f"[오류] params.json에 '{api_id}' 키가 존재하지 않습니다.")
            return None

        # 1. API 기본 정보 로드
        api_info = self.api_params[api_id]
        endpoint = api_info.get("endpoint")
        url = self.host + endpoint
        
        # 2. 토큰 처리 (au10001 제외)
        token = None
        if api_id != "au10001":
            token = self._token_manager()
            if not token:
                return None

        # 3. 헤더 구성 (params.json 기반 + kwargs 오버라이드)
        # 템플릿 로드
        headers_template = api_info.get("headers", {})
        
        # 기본 헤더값 설정
        req_headers = headers_template.copy()
        
        # (중요) Bearer 토큰 설정
        if token and "authorization" not in kwargs:
             req_headers["authorization"] = f"Bearer {token}"
        
        # kwargs로 들어온 값 중 헤더에 정의된 키가 있다면 교체 (예: cont-yn)
        for h_key in req_headers.keys():
            if h_key in kwargs:
                req_headers[h_key] = kwargs[h_key]
        
        # api-id 등 자동 설정
        if "api-id" in req_headers and req_headers["api-id"].startswith("{"):
             req_headers["api-id"] = api_id # 엑셀 파싱 때 {api-id}로 된 경우 대비

        # 4. 바디 구성
        body_template = api_info.get("body", {})
        
        # A. 템플릿의 {placeholder} 치환
        req_body = self._fill_params(body_template, **kwargs)
        
        # B. 템플릿에는 없지만 kwargs로 들어온 나머지 값들 추가 (동적 파라미터)
        for k, v in kwargs.items():
            # 헤더 키가 아니고, 이미 바디에 처리되지 않은 키라면 추가
            if k not in req_headers and k not in body_template:
                req_body[k] = v

        try:
            print(f"\n[요청] {api_id} ({api_info.get('name')})")
            # print(f" - URL: {url}")
            # print(f" - Body: {req_body}") # 디버깅용
            
            response = requests.post(url, headers=req_headers, json=req_body)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[실패] 상태코드: {response.status_code}")
                print(f"[응답] {response.text}")
                return None
                
        except Exception as e:
            print(f"[예외 발생] {e}")
            return None
    
    def _load_api_params(self):
        params_file_path = os.path.join(os.path.dirname(__file__), 'params.json')
        if os.path.exists(params_file_path):
            with open(params_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print("[오류] params.json 파일이 존재하지 않습니다.")
            return {}

if __name__ == '__main__':
    api = KiwoomAPI()
    
    # 테스트: 주식 잔고 조회 (ka00002 가 params.json에 있다고 가정)
    # 엑셀 파싱결과에 따라 변수명(CANO 등)은 params.json을 참고해야 합니다.
    # 예시: 엑셀의 변수명이 'CANO', 'PDNO' 등으로 저장되었다면 아래와 같이 호출
    
    test_api_id = "ka10001"  # 실제 params.json에 있는 ID 사용
    
    # **kwargs를 이용해 필요한 파라미터 전달
    args = {"stk_cd": "005930"}
    
    response = api._get_response(test_api_id, **args)
    
    if response:
        print("\n[응답 결과]")
        # 보기 좋게 출력
        print(json.dumps(response, indent=4, ensure_ascii=False))