async function registerPasskey() {
    const username = document.getElementById("passkey-username").value || "user1";
    
    try {
        const res = await fetch("/api/register/challenge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username })
        });
        await res.json();
        
        const credentialId = "cred_" + Math.random().toString(36).substring(2);
        const publicKey = "pubkey_sig_" + Math.random().toString(36).substring(2);
        const credentialName = prompt("패스키 이름을 입력하세요:", "내 기기 패스키") || "기본 패스키";
        
        const completeRes = await fetch("/api/register/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username,
                credentialId,
                publicKey,
                credentialName
            })
        });
        const completeData = await completeRes.json();
        
        if (completeData.success) {
            alert("패스키 등록이 완료되었습니다!");
            loadLoginCredentials();
        }
    } catch (e) {
        console.error("패스키 등록 실패", e);
        alert("패스키 등록 중 오류가 발생했습니다.");
    }
}

async function loadLoginCredentials() {
    const username = document.getElementById("passkey-username").value || "user1";
    try {
        const res = await fetch(`/api/credentials?username=${username}`);
        const creds = await res.json();
        
        const selectEl = document.getElementById("login-credential-select");
        if (creds.length === 0) {
            selectEl.innerHTML = '<option value="">등록된 패스키가 없습니다</option>';
            alert("등록된 패스키가 없습니다. 먼저 패스키를 등록해주세요.");
            return;
        }
        
        selectEl.innerHTML = creds.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
        alert("패스키 목록을 불러왔습니다. 사용할 기기 패스키를 선택하세요.");
    } catch (e) {
        console.error("패스키 목록 조회 실패", e);
    }
}

async function loginWithPasskey() {
    const username = document.getElementById("passkey-username").value || "user1";
    const selectedCredId = document.getElementById("login-credential-select").value;
    
    if (!selectedCredId) {
        alert("먼저 [목록 조회]를 누르고 로그인할 패스키를 선택해주세요.");
        return;
    }
    
    try {
        const res = await fetch("/api/login/challenge", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username })
        });
        await res.json();
        
        const verifyRes = await fetch("/api/login/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username,
                credentialId: selectedCredId
            })
        });
        
        if (verifyRes.ok) {
            alert("패스키 인증 성공! 포트폴리오로 입장합니다.");
            loadPrivateData(username);
        } else {
            alert("인증에 실패했습니다.");
        }
    } catch (e) {
        console.error("로그인 실패", e);
    }
}

async function loadPrivateData(username) {
    try {
        const res = await fetch(`/api/private/data?username=${username}`);
        if (res.status === 401 || res.status === 403) {
            alert("권한이 없습니다.");
            return;
        }
        const data = await res.json();
        
        const listEl = document.getElementById("private-items-list");
        listEl.innerHTML = data.items.map(item => `<li>${item}</li>`).join("");
        
        document.getElementById("lock-screen-section").style.display = "none";
        document.getElementById("main-portfolio-content").style.display = "block";
        document.getElementById("logged-in-user").innerText = username;
        
        loadCredentialsList(username);
    } catch (e) {
        console.error("비공개 데이터 로드 실패", e);
    }
}

async function loadCredentialsList(username) {
    const res = await fetch(`/api/credentials?username=${username}`);
    const creds = await res.json();
    const credListEl = document.getElementById("credentials-list");
    
    credListEl.innerHTML = creds.map(c => `
        <li style="margin-bottom: 5px;">
            ${c.name} 
            <button onclick="deleteCredential('${username}', '${c.id}')" style="margin-left:10px; padding:2px 6px; cursor:pointer;">삭제</button>
        </li>
    `).join("");
}

async function deleteCredential(username, credentialId) {
    const res = await fetch("/api/credentials/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, credentialId })
    });
    const data = await res.json();
    if (data.success) {
        alert("패스키가 삭제되었습니다.");
        loadCredentialsList(username);
        loadLoginCredentials();
    } else {
        alert(data.error || "삭제 실패");
    }
}

function logoutPrivateZone() {
    document.getElementById("main-portfolio-content").style.display = "none";
    document.getElementById("lock-screen-section").style.display = "block";
    alert("로그아웃되었습니다.");
}