from pathlib import Path
p=Path('/mnt/data/online_work/public/index.html')
s=p.read_text()
# Login form: add member field and update text
s=s.replace('''      <div id="setupFields">\n        <label for="ownerEmail">E-mail zakladatele</label>''','''      <div id="setupFields">\n        <label for="ownerEmail">E-mail zakladatele</label>''')
s=s.replace('''        <input id="familyName" type="text" maxlength="40" autocomplete="organization" placeholder="např. Novákovi" required>\n      </div>\n\n      <label for="familyLogin">Uživatelské jméno rodiny</label>''','''        <input id="familyName" type="text" maxlength="40" autocomplete="organization" placeholder="např. Novákovi" required>\n      </div>\n\n      <label for="memberName">Kdo se přihlašuje?</label>\n      <input id="memberName" type="text" maxlength="40" autocomplete="name" placeholder="např. Táta" required>\n\n      <label for="familyLogin">Uživatelské jméno rodiny</label>''')
s=s.replace('''<input id="familyPassword" type="password" minlength="8" autocomplete="new-password" placeholder="alespoň 8 znaků" required>''','''<input id="familyPassword" type="password" minlength="10" autocomplete="new-password" placeholder="alespoň 10 znaků" required>''')
s=s.replace('''<div class="login-note">E-mail slouží jako kotva účtu a později také k obnově přístupu. Uživatelské jméno a heslo bude společné pro domácnost. Tato první verze přihlášení je zatím pouze místní prototyp; internetové ukládání připojíme v dalším kroku.</div>''','''<div class="login-note">E-mail zakladatele je kotva domácnosti. Rodina má společné uživatelské jméno a heslo; při přihlášení si každý vybere své jméno. Data se ukládají na server a po přihlášení jsou stejná na telefonu i počítači.</div>''')
s=s.replace('''<button type="button" id="switchMemberBtn">Změnit člena</button>\n</div>''','''<button type="button" id="switchMemberBtn">Změnit člena</button>\n  <button type="button" id="logoutBtn" class="secondary">Odhlásit</button>\n</div>''')
s=s.replace('''<div class="online-plan" id="onlinePlanBanner">\n  <strong>Kompas je připraven na online propojení.</strong><br>\n  Tato verze zatím ukládá data v zařízení. Online synchronizaci zapojíme až po připojení zabezpečeného serveru.\n</div>''','''<div class="online-plan" id="onlinePlanBanner">\n  <strong>Online účet je zapnutý.</strong><br>\n  Změny se ukládají průběžně na server, takže domácnost používá stejná data na telefonu i počítači.\n</div>''')
# main data save: load fallback remains, save becomes queued API save
old='''function save(){localStorage.setItem(KEY,JSON.stringify(data));renderAll()}'''
new='''let saveChain=Promise.resolve();\nfunction save(){\n  const snapshot=JSON.parse(JSON.stringify(data));\n  renderAll();\n  if(!window.kompasOnline) return;\n  saveChain=saveChain.then(async()=>{\n    const r=await fetch("/api/data",{method:"PUT",headers:{"Content-Type":"application/json"},credentials:"same-origin",body:JSON.stringify({payload:snapshot})});\n    if(!r.ok){\n      let msg="Změnu se nepodařilo uložit.";\n      try{const x=await r.json();if(x.error)msg=x.error}catch(e){}\n      throw new Error(msg);\n    }\n    window.kompasOnlineLastSaved=new Date();\n  }).catch(async(err)=>{\n    console.error(err);\n    alert("Pozor: " + err.message + "\n\nKompas načte poslední bezpečně uložená data ze serveru.");\n    try{\n      const r=await fetch("/api/data",{credentials:"same-origin"});\n      if(r.ok){const x=await r.json(); data=normalizeOnlineData(x.payload||{}); renderAll();}\n    }catch(e){}\n  });\n  return saveChain;\n}\nfunction normalizeOnlineData(x){\n  x=x&&typeof x==="object"?x:{};\n  return {income:Number(x.income)||0,expenses:Array.isArray(x.expenses)?x.expenses:[],piggies:Array.isArray(x.piggies)?x.piggies:[],recurring:Array.isArray(x.recurring)?x.recurring:[]};\n}'''
assert old in s
s=s.replace(old,new)
# Replace from login prototype through end with online bridge, preserving backup/history/chooser HTML not needed; rebuild simple history and chooser markup.
start=s.index('<script id="login-prototype">')
end=s.rindex('</body>')
replacement=r'''<div id="historyCard" class="history-card" style="display:none">
  <h2>Historie změn</h2>
  <div class="muted" style="font-size:13px;margin-bottom:8px">Poslední změny uložené na serveru. U změn je možné obnovit předchozí stav.</div>
  <div id="historyList"></div>
</div>

<div id="memberChooser" class="member-chooser" style="display:none">
  <div class="member-chooser-box">
    <h2>Kdo právě používá Kompas?</h2>
    <p>Vyberte své jméno. U každého nového výdaje se uloží, kdo ho zadal.</p>
    <div id="memberChooserList"></div>
    <button type="button" class="secondary" id="closeMemberChooser">Zavřít</button>
  </div>
</div>

<script id="online-app">
(function(){
  const layer=document.getElementById('loginLayer');
  const form=document.getElementById('loginForm');
  const setup=document.getElementById('setupFields');
  const email=document.getElementById('ownerEmail');
  const familyName=document.getElementById('familyName');
  const memberName=document.getElementById('memberName');
  const login=document.getElementById('familyLogin');
  const password=document.getElementById('familyPassword');
  const submit=document.getElementById('loginSubmit');
  const switchBtn=document.getElementById('loginSwitch');
  const subtitle=document.getElementById('loginSubtitle');
  const error=document.getElementById('loginError');
  const memberBar=document.getElementById('currentMemberBar');
  const memberNameEl=document.getElementById('currentMemberName');
  const memberListEl=document.getElementById('familyMemberList');
  const memberCountEl=document.getElementById('familyMemberCount');
  let setupMode=true;
  let members=[];
  let currentMember={id:'',name:''};
  let loggedIn=false;

  function cleanName(v){return String(v||'').trim().replace(/[.,!?;:"'()[\]{}<>\/\\@#$%^&*+=|~`]/g,'').replace(/\s+/g,' ')}
  function lettersAndSpacesOnly(v){return /^[\p{L}\p{M} ]+$/u.test(String(v||'').trim())}
  function normalizeLogin(v){return String(v||'').trim().toLowerCase().replace(/\s+/g,'')}
  function setError(t){error.textContent=t||''}
  function openApp(){layer.hidden=true;document.body.classList.remove('login-mode');loggedIn=true;window.kompasOnline=true;loadOnlineState()}
  function renderMode(){
    setup.style.display=setupMode?'block':'none';
    submit.textContent=setupMode?'Vytvořit rodinný Kompas':'Přihlásit se';
    switchBtn.textContent=setupMode?'Už máme Kompas – přihlásit se':'Chci založit nový rodinný Kompas';
    subtitle.textContent=setupMode?'Nejdříve vytvořte společný účet pro celou domácnost.':'Přihlaste domácnost a vyberte, kdo právě zapisuje.';
    password.autocomplete=setupMode?'new-password':'current-password';
    password.minLength=10;
    if(!setupMode){email.value='';familyName.value='';}
    setError('');
  }
  async function api(url,options){
    const r=await fetch(url,Object.assign({credentials:'same-origin'},options||{}));
    let x={};try{x=await r.json()}catch(e){}
    if(!r.ok)throw new Error(x.error||'Něco se nepodařilo.');
    return x;
  }
  async function loadOnlineState(){
    try{
      const me=await api('/api/me');
      members=me.members||[];
      currentMember=members.find(m=>m.id===me.currentMemberId)||members[0]||{id:'',name:''};
      renderMembers(); renderCurrent(); window.kompasCurrentMember=()=>currentMember.name||'';
      window.kompasChooseMember=chooseMember; window.kompasMembers=()=>members.map(m=>m.name);
      const d=await api('/api/data');
      data=normalizeOnlineData(d.payload||{});
      renderAll();
      await renderHistory();
      if(!currentMember.id) chooseMember();
    }catch(e){
      setError(e.message); layer.hidden=false; document.body.classList.add('login-mode'); loggedIn=false; window.kompasOnline=false;
    }
  }
  function renderCurrent(){
    if(!memberBar||!memberNameEl)return;
    memberNameEl.textContent=currentMember.name||'';
    memberBar.style.display=currentMember.name?'flex':'none';
  }
  function renderMembers(){
    if(!memberListEl||!memberCountEl)return;
    memberListEl.innerHTML='';
    members.forEach(m=>{
      const chip=document.createElement('div');chip.className='member-chip';
      const span=document.createElement('span');span.textContent=m.name;
      const b=document.createElement('button');b.type='button';b.textContent='×';b.setAttribute('aria-label','Odebrat člena');
      b.addEventListener('click',()=>removeMember(m));
      chip.append(span,b);memberListEl.appendChild(chip);
    });
    memberCountEl.textContent='Členů: '+members.length+' / 20';
  }
  async function addMember(){
    const input=document.getElementById('newFamilyMember'); if(!input)return;
    const name=cleanName(input.value);
    if(!name){alert('Napište jméno člena rodiny.');return}
    if(!lettersAndSpacesOnly(name)){alert('Jméno může obsahovat jen písmena, diakritiku a mezery.');return}
    if(members.length>=20){alert('Můžete mít nejvýše 20 členů rodiny.');return}
    if(members.some(m=>m.name.toLocaleLowerCase('cs-CZ')===name.toLocaleLowerCase('cs-CZ'))){alert('Tento člen už v rodině je.');return}
    try{const m=await api('/api/members',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});members.push(m);input.value='';renderMembers();}
    catch(e){alert(e.message)}
  }
  async function removeMember(m){
    if(m.id===currentMember.id){alert('Nelze odebrat právě přihlášeného člena.');return}
    if(!confirm('Opravdu chcete odebrat člena „'+m.name+'“?'))return;
    try{await api('/api/members/'+encodeURIComponent(m.id),{method:'DELETE'});members=members.filter(x=>x.id!==m.id);renderMembers();}
    catch(e){alert(e.message)}
  }
  async function chooseMember(){
    const list=document.getElementById('memberChooserList'),modal=document.getElementById('memberChooser');if(!list||!modal)return;
    list.innerHTML='';
    members.forEach(m=>{const b=document.createElement('button');b.type='button';b.className='member-choice';b.textContent='👤 '+m.name;b.onclick=async()=>{try{await api('/api/switch-member',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({memberId:m.id})});currentMember=m;renderCurrent();modal.style.display='none';renderAll();}catch(e){alert(e.message)}};list.appendChild(b)});
    modal.style.display='flex';
  }
  async function logout(){try{await api('/api/logout',{method:'POST'});}catch(e){} location.reload()}
  async function saveHistoryRestore(id){
    if(!confirm('Vrátit Kompas do stavu před touto změnou?'))return;
    try{await api('/api/history/'+encodeURIComponent(id)+'/restore',{method:'POST'});await loadOnlineState();alert('Stav byl obnoven.');}
    catch(e){alert(e.message)}
  }
  async function renderHistory(){
    const card=document.getElementById('historyCard'),list=document.getElementById('historyList');if(!card||!list)return;
    try{
      const rows=await api('/api/history');card.style.display=rows.length?'block':'none';list.innerHTML='';
      rows.forEach(row=>{const el=document.createElement('div');el.className='history-item';
        const t=document.createElement('div');t.textContent=row.action;const m=document.createElement('div');m.className='history-meta';m.textContent=new Date(row.created_at).toLocaleString('cs-CZ')+' · '+(row.member||'Neznámý člen');el.append(t,m);
        const b=document.createElement('button');b.type='button';b.textContent='↩ Obnovit stav';b.onclick=()=>saveHistoryRestore(row.id);el.appendChild(b);list.appendChild(el);});
    }catch(e){console.error(e)}
  }
  form.addEventListener('submit',async function(e){
    e.preventDefault();setError('');submit.disabled=true;
    try{
      const l=normalizeLogin(login.value),pw=password.value,mn=cleanName(memberName.value);
      if(!mn||!lettersAndSpacesOnly(mn))throw new Error('Zadejte jméno člena – jen písmena, diakritiku a mezery.');
      if(l.length<3||!lettersAndSpacesOnly(login.value))throw new Error('Uživatelské jméno může obsahovat jen písmena, diakritiku a mezery.');
      if(pw.length<10)throw new Error('Heslo musí mít alespoň 10 znaků.');
      if(setupMode){
        const em=email.value.trim(),hn=cleanName(familyName.value);
        if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em))throw new Error('Zadejte platný e-mail.');
        if(!hn||!lettersAndSpacesOnly(hn))throw new Error('Název domácnosti může obsahovat jen písmena, diakritiku a mezery.');
        await api('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:em,householdName:hn,username:l,password:pw,firstMember:mn})});
      }else{
        await api('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:l,password:pw,memberName:mn})});
      }
      openApp();
    }catch(e){setError(e.message)}finally{submit.disabled=false}
  });
  switchBtn.addEventListener('click',()=>{setupMode=!setupMode;renderMode()});
  document.addEventListener('DOMContentLoaded',()=>{
    const add=document.getElementById('addFamilyMember'),input=document.getElementById('newFamilyMember'),sw=document.getElementById('switchMemberBtn'),close=document.getElementById('closeMemberChooser'),logoutBtn=document.getElementById('logoutBtn');
    if(add)add.addEventListener('click',addMember);if(input)input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();addMember()}});if(sw)sw.addEventListener('click',chooseMember);if(close)close.addEventListener('click',()=>document.getElementById('memberChooser').style.display='none');if(logoutBtn)logoutBtn.addEventListener('click',logout);
    // Hide the temporary local backup card; server backups are automatic.
    const bc=document.getElementById('backupCard');if(bc)bc.style.display='none';
    renderMode();
    api('/api/me').then(()=>openApp()).catch(()=>{window.kompasOnline=false;});
  });
})();
</script>
</body>
</html>
'''
s=s[:start]+replacement
p.write_text(s)
