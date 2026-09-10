// Base64URL을 Uint8Array로 변환하는 유틸리티
function bufferDecode(value) {
    let base64 = value.replace(/-/g, '+').replace(/_/g, '/');
    let pad = base64.length % 4;
    if (pad) {
        base64 += '='.repeat(4 - pad);
    }
    let binary = window.atob(base64);
    let bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

// Uint8Array를 Base64URL로 변환하는 유틸리티
function bufferEncode(value) {
    let base64 = window.btoa(String.fromCharCode(...new Uint8Array(value)));
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

// 새 패스키 등록 함수
async function registerPasskey() {
    try {
        let res = await fetch('/api/register/begin', { method: 'POST' });
        if (!res.ok) throw new Error('서버 통신 실패 (등록 시작)');
        let options = await res.json();

        options.challenge = bufferDecode(options.challenge);
        options.user.id = bufferDecode(options.user.id);

        let credential = await navigator.credentials.create({ publicKey: options });
        
        let credentialData = {
            id: credential.id,
            rawId: bufferEncode(credential.rawId),
            response: {
                clientDataJSON: bufferEncode(credential.response.clientDataJSON),
                attestationObject: bufferEncode(credential.response.attestationObject)
            },
            type: credential.type
        };

        let completeRes = await fetch('/api/register/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: credentialData })
        });
        
        let result = await completeRes.json();
        if (result.status === 'ok') {
            alert('패스키가 성공적으로 등록되었습니다!');
            location.reload();
        } else {
            alert('등록에 실패했습니다.');
        }
    } catch (err) {
        console.error(err);
        alert('패스키 등록 오류: ' + err.message);
    }
}

// 패스키 로그인(열기) 함수
async function loginPasskey() {
    try {
        let res = await fetch('/api/login/begin', { method: 'POST' });
        if (!res.ok) throw new Error('서버 통신 실패 (로그인 시작)');
        let options = await res.json();

        options.challenge = bufferDecode(options.challenge);
        if (options.allowCredentials) {
            options.allowCredentials.forEach(cred => {
                cred.id = bufferDecode(cred.id);
            });
        }

        let assertion = await navigator.credentials.get({ publicKey: options });

        let assertionData = {
            id: assertion.id,
            rawId: bufferEncode(assertion.rawId),
            response: {
                clientDataJSON: bufferEncode(assertion.response.clientDataJSON),
                authenticatorData: bufferEncode(assertion.response.authenticatorData),
                signature: bufferEncode(assertion.response.signature),
                userHandle: assertion.response.userHandle ? bufferEncode(assertion.response.userHandle) : null
            },
            type: assertion.type
        };

        let completeRes = await fetch('/api/login/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(assertionData)
        });

        let result = await completeRes.json();
        if (result.status === 'ok') {
            alert('비공개 영역 인증 성공!');
            location.reload();
        } else {
            alert('인증에 실패했습니다.');
        }
    } catch (err) {
        console.error(err);
        alert('패스키 로그인 오류: ' + err.message);
    }
}

// HTML 버튼에서 바로 호출할 수 있도록 전역 객체(window)에 등록
window.registerPasskey = registerPasskey;
window.loginPasskey = loginPasskey;