// 1. Firebase 설정 (본인의 Firebase 프로젝트 설정 값)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getFirestore, doc, setDoc, getDoc } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-firestore.js";

const firebaseConfig = {
  // 사용 중이신 Firebase 설정 정보를 그대로 넣으시면 됩니다.
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// Helper: Base64URL 변환 함수
function bufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let string = "";
  for (let j = 0; j < bytes.byteLength; j++) {
    string += String.fromCharCode(bytes[j]);
  }
  return btoa(string).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function base64urlToBuffer(base64url) {
  const padding = "=".repeat((4 - (base64url.length % 4)) % 4);
  const base64 = (base64url + padding).replace(/\-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const buffer = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    buffer[i] = rawData.charCodeAt(i);
  }
  return buffer.buffer;
}

// 2. 패스키 등록 함수
async function registerPasskey() {
  try {
    const challenge = new Uint8Array(32);
    window.crypto.getRandomValues(challenge);

    const userId = new Uint8Array(16);
    window.crypto.getRandomValues(userId);

    const publicKeyCredentialCreationOptions = {
      challenge: challenge,
      rp: {
        name: "My Portfolio",
        // ⭐ window.location.hostname 덕분에 GitHub Pages에서도 자동 대응됩니다.
        id: window.location.hostname
      },
      user: {
        id: userId,
        name: "user@example.com",
        displayName: "Portfolio User"
      },
      pubKeyCredParams: [{ alg: -7, type: "public-key" }],
      authenticatorSelection: {
        authenticatorAttachment: "platform",
        userVerification: "preferred"
      },
      timeout: 60000
    };

    const credential = await navigator.credentials.create({
      publicKey: publicKeyCredentialCreationOptions
    });

    // Firestore에 저장할 데이터 구성
    const passkeyData = {
      id: credential.id,
      rawId: bufferToBase64url(credential.rawId),
      type: credential.type,
      createdAt: new Date().toISOString()
    };

    // Firestore 'passkeys' 컬렉션에 저장
    await setDoc(doc(db, "passkeys", credential.id), passkeyData);
    alert("패스키가 성공적으로 등록되었습니다!");
  } catch (err) {
    console.error(err);
    alert("등록 실패 또는 취소: " + err.message);
  }
}

// 3. 패스키 로그인/열기 함수
async function loginWithPasskey() {
  try {
    const challenge = new Uint8Array(32);
    window.crypto.getRandomValues(challenge);

    const publicKeyCredentialRequestOptions = {
      challenge: challenge,
      rpId: window.location.hostname, // ⭐ GitHub Pages 도메인 자동 반영
      userVerification: "preferred"
    };

    const assertion = await navigator.credentials.get({
      publicKey: publicKeyCredentialRequestOptions
    });

    // Firestore에서 저장된 패스키 조회 검증
    const docRef = doc(db, "passkeys", assertion.id);
    const docSnap = await getDoc(docRef);

    if (docSnap.exists()) {
      alert("패스키 인증 성공! 비공개 영역을 엽니다.");
      // 인증 성공 시 비공개 영역 표시 로직
      const privateZone = document.getElementById("private-zone");
      if (privateZone) privateZone.style.display = "block";
    } else {
      alert("등록되지 않은 패스키입니다.");
    }
  } catch (err) {
    console.error(err);
    alert("인증 실패: " + err.message);
  }
}

// 4. 버튼 이벤트 리스너 연결
document.addEventListener("DOMContentLoaded", () => {
  const registerBtn = document.getElementById("register-btn");
  const loginBtn = document.getElementById("login-btn");

  if (registerBtn) registerBtn.addEventListener("click", registerPasskey);
  if (loginBtn) loginBtn.addEventListener("click", loginWithPasskey);
});