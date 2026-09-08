# app.py
from flask import Flask, render_template, request, jsonify, session
import webauthn
import os
import uuid

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.urandom(24)

# 인메모리 데이터베이스 (테스트 및 제출용)
# T08-C21, T08-C24, T08-C36
USERS = {
    "user_1": {
        "id": b"user_id_1",
        "name": "이시헌 (계정 1)",
        "credentials": [], # [{ 'id': bytes, 'public_key': bytes, 'sign_count': int, 'name': str, 'created_at': str }]
        "private_data": [
            {"title": "준비 중인 프로젝트 메모", "content": "RAG 기반 포트폴리오 에이전트 개발 중"},
            {"title": "지원하려는 곳 목록", "content": "네이버, 카카오, 라인 프론트엔드/풀스택 파트"},
            {"title": "스스로 쓰는 회고", "content": "매일 WebAuthn 및 백엔드 보안 학습 기록 작성"}
        ]
    },
    "user_2": {
        "id": b"user_id_2",
        "name": "테스터 (계정 2)",
        "credentials": [],
        "private_data": [
            {"title": "비공개 프로젝트 B", "content": "보안 대시보드 모듈 설계"},
            {"title": "비공개 노트 B", "content": "암호화 키 관리 아키텍처"},
            {"title": "회고 B", "content": "패스키 멀티 디바이스 동기화 테스트 완료"}
        ]
    }
}

RP_ID = "localhost" # 실제 배포 시 HTTPS 도메인 적용
RP_NAME = "My Portfolio Passkey Service"

# --- T08-C16, T08-C17, T08-C18: 비공개 데이터 요청 검증 ---
@app.route('/api/private-data', methods=['GET'])
def get_private_data():
    user_id = session.get('logged_in_user')
    if not user_id or user_id not in USERS:
        # T08-C17: 미인증 접근 시 401 Unauthorized 반환
        return jsonify({"error": "Unauthorized"}), 401

    # T08-C40: 다른 계정의 데이터 요청을 차단하고 오직 로그인한 자신의 데이터만 반환
    return jsonify({
        "owner": USERS[user_id]["name"],
        "items": USERS[user_id]["private_data"]
    }), 200

# --- T08-C19, T08-C20: 등록 챌린지 생성 ---
@app.route('/api/auth/register/challenge', methods=['POST'])
def register_challenge():
    user_id = request.json.get('user_id', 'user_1')
    user = USERS.get(user_id)

    options = webauthn.generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user["id"],
        user_name=user["name"],
    )
    
    # T08-C19: 서버에 challenge 저장
    session['register_challenge'] = options.challenge
    session['target_user'] = user_id

    return jsonify(webauthn.options_to_json(options))

# --- T08-C21~C26: 패스키 등록 완료 및 저장 ---
@app.route('/api/auth/register/finish', methods=['POST'])
def register_finish():
    challenge = session.get('register_challenge')
    user_id = session.get('target_user')
    key_name = request.json.get('key_name', '기본 패스키')

    if not challenge or not user_id:
        return jsonify({"error": "Invalid session or challenge"}), 400

    try:
        registration_verification = webauthn.verify_registration_response(
            credential=request.json.get('credential'),
            expected_challenge=challenge,
            expected_origin=request.host_url.rstrip('/'),
            expected_rp_id=RP_ID,
        )

        # T08-C21, T08-C24: 공개키 및 별칭 저장 (개인키는 절대 넘어오지 않음)
        USERS[user_id]["credentials"].append({
            "id": registration_verification.credential_id,
            "public_key": registration_verification.public_key,
            "sign_count": registration_verification.sign_count,
            "name": key_name,
            "created_at": "2026-09-07"
        })
        
        session.pop('register_challenge', None)
        return jsonify({"status": "success", "message": "패스키 등록 완료"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- T08-C27~C31: 로그인 챌린지 및 검증 ---
@app.route('/api/auth/login/challenge', methods=['POST'])
def login_challenge():
    user_id = request.json.get('user_id', 'user_1')
    user = USERS.get(user_id)

    # 등록된 패스키 유효성 검사
    user_credentials = [
        webauthn.PublicKeyCredentialDescriptor(id=c["id"]) 
        for c in user["credentials"]
    ]

    options = webauthn.generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=user_credentials
    )

    # T08-C31: 일회용 질문(Challenge)을 세션에 저장 및 1회 사용 후 폐기
    session['login_challenge'] = options.challenge
    session['login_user_target'] = user_id

    return jsonify(webauthn.options_to_json(options))

@app.route('/api/auth/login/finish', methods=['POST'])
def login_finish():
    challenge = session.pop('login_challenge', None) # 재사용 방지 (1회성)
    user_id = session.get('login_user_target')

    if not challenge:
        # T08-C31: 이미 사용된 Challenge로 재요청 시 거절
        return jsonify({"error": "Challenge reused or expired"}), 400

    user = USERS.get(user_id)
    credential_id = request.json.get('credential', {}).get('id')

    # 해당 Credential의 공개키 조회
    cred = next((c for c in user["credentials"] if c["id"] == credential_id), None)
    if not cred:
        return jsonify({"error": "Credential not found"}), 400

    try:
        auth_verification = webauthn.verify_authentication_response(
            credential=request.json.get('credential'),
            expected_challenge=challenge,
            expected_origin=request.host_url.rstrip('/'),
            expected_rp_id=RP_ID,
            credential_public_key=cred["public_key"],
            credential_current_sign_count=cred["sign_count"]
        )

        # Sign Count 업데이트
        cred["sign_count"] = auth_verification.new_sign_count
        # T08-C32: 쿠키 기반 세션으로 인증 상태 유지
        session['logged_in_user'] = user_id

        return jsonify({"status": "success", "user": user["name"]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- T08-C33: 로그아웃 ---
@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success"}), 200

# --- T08-C43~C46: 패스키 관리 및 삭제 ---
@app.route('/api/auth/keys', methods=['GET', 'DELETE'])
def manage_keys():
    user_id = session.get('logged_in_user', 'user_1')
    user = USERS.get(user_id)

    if request.method == 'GET':
        # T08-C43: 등록된 패스키 목록, 이름, 날짜 조회
        keys = [{"id": c["id"].hex(), "name": c["name"], "created_at": c["created_at"]} for c in user["credentials"]]
        return jsonify({"keys": keys}), 200

    elif request.method == 'DELETE':
        key_id_hex = request.json.get('key_id')
        user["credentials"] = [c for c in user["credentials"] if c["id"].hex() != key_id_hex]
        
        # T08-C46: 패스키가 0개 남아있을 때 세션 제거
        if len(user["credentials"]) == 0:
            session.clear()

        return jsonify({"status": "success", "remaining": len(user["credentials"])}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)