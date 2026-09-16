import os
import json
import secrets
from flask import Flask, jsonify, render_template, request, session
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

if not firebase_admin._apps:
    firebase_json_str = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    if not firebase_json_str:
        raise ValueError("🔥 FIREBASE_SERVICE_ACCOUNT_JSON 환경 변수가 설정되지 않았습니다!")
        
    # Render 환경 변수에 들어간 JSON 문자열을 딕셔너리로 변환
    cred_dict = json.loads(firebase_json_str)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

def get_user_doc(username):
    return db.collection("users").document(username)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/edit")
def edit():
    return render_template("edit.html")

@app.route("/api/register/challenge", methods=["POST"])
def register_challenge():
    data = request.get_json() or {}
    username = data.get("username", "user1")
    challenge = secrets.token_hex(32)
    
    user_ref = get_user_doc(username)
    doc = user_ref.get()
    
    if not doc.exists:
        user_ref.set({
            "credentials": {},
            "private_items": [
                "프로젝트 메모: 패스키 기반 인증 서버 구현 완료",
                "지원 현황: 프론트엔드 및 백엔드 포지션 지원 목록 관리",
                "개인 회고: 웹 표준 WebAuthn 프로토콜 학습 및 적용"
            ],
            "challenges": {}
        })
    
    user_ref.update({"challenges.register": challenge})
    return jsonify({"challenge": challenge, "username": username})

@app.route("/api/register/complete", methods=["POST"])
def register_complete():
    data = request.get_json() or {}
    username = data.get("username", "user1")
    cred_id = data.get("credentialId")
    pub_key = data.get("publicKey")
    cred_name = data.get("credentialName", "기본 패스키")
    
    if not cred_id or not pub_key:
        return jsonify({"error": "Invalid credential data"}), 400
        
    user_ref = get_user_doc(username)
    doc = user_ref.get()
    if not doc.exists:
        return jsonify({"error": "User not found"}), 404
        
    user_data = doc.to_dict()
    credentials_map = user_data.get("credentials", {})
    credentials_map[cred_id] = {
        "publicKey": pub_key,
        "name": cred_name
    }
    
    user_ref.update({"credentials": credentials_map})
    return jsonify({"success": True})

@app.route("/api/login/challenge", methods=["POST"])
def login_challenge():
    data = request.get_json() or {}
    username = data.get("username", "user1")
    user_ref = get_user_doc(username)
    doc = user_ref.get()
    
    if not doc.exists:
        return jsonify({"error": "User not found"}), 404
        
    challenge = secrets.token_hex(32)
    user_ref.update({"challenges.login": challenge})
    return jsonify({"challenge": challenge})

@app.route("/api/login/verify", methods=["POST"])
def login_verify():
    data = request.get_json() or {}
    username = data.get("username", "user1")
    cred_id = data.get("credentialId")
    
    user_ref = get_user_doc(username)
    doc = user_ref.get()
    if not doc.exists:
        return jsonify({"error": "Unauthorized"}), 401
        
    user_data = doc.to_dict()
    challenges = user_data.get("challenges", {})
    if "login" not in challenges:
        return jsonify({"error": "Unauthorized"}), 401
        
    user_ref.update({"challenges.login": firestore.DELETE_FIELD})
    
    credentials_map = user_data.get("credentials", {})
    if cred_id not in credentials_map:
        return jsonify({"error": "Unregistered credential"}), 401
        
    session["user"] = username
    return jsonify({"success": True})

@app.route("/api/private/data", methods=["GET"])
def get_private_data():
    username = request.args.get("username", "user1")
    if "user" not in session or session["user"] != username:
        return jsonify({"error": "Unauthorized access"}), 401
        
    doc = get_user_doc(username).get()
    if not doc.exists:
        return jsonify({"error": "Forbidden"}), 403
        
    user_data = doc.to_dict()
    return jsonify({
        "items": user_data.get("private_items", []),
        "credentialsCount": len(user_data.get("credentials", {}))
    })

@app.route("/api/credentials", methods=["GET"])
def list_credentials():
    username = request.args.get("username", "user1")
    doc = get_user_doc(username).get()
    if not doc.exists:
        return jsonify([])
        
    user_data = doc.to_dict()
    credentials_map = user_data.get("credentials", {})
    creds = [{"id": cid, "name": info["name"]} for cid, info in credentials_map.items()]
    return jsonify(creds)

@app.route("/api/credentials/delete", methods=["POST"])
def delete_credential():
    data = request.get_json() or {}
    username = data.get("username", "user1")
    cred_id = data.get("credentialId")
    
    user_ref = get_user_doc(username)
    doc = user_ref.get()
    if not doc.exists:
        return jsonify({"error": "Not found"}), 404
        
    user_data = doc.to_dict()
    credentials_map = user_data.get("credentials", {})
    
    if cred_id in credentials_map:
        if len(credentials_map) <= 1:
            return jsonify({"error": "최소 1개의 패스키는 유지해야 합니다."}), 400
        del credentials_map[cred_id]
        user_ref.update({"credentials": credentials_map})
        return jsonify({"success": True})
        
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)