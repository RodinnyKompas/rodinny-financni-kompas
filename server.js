const express = require("express");
const path = require("path");
const crypto = require("crypto");
const bcrypt = require("bcryptjs");
const helmet = require("helmet");
const rateLimit = require("express-rate-limit");
const { Pool } = require("pg");
const cookieSession = require("cookie-session");

const app = express();
const PORT = process.env.PORT || 3000;

if (!process.env.DATABASE_URL) {
  console.error("DATABASE_URL není nastavená.");
  process.exit(1);
}
if (process.env.NODE_ENV === "production" && (!process.env.SESSION_SECRET || process.env.SESSION_SECRET.length < 32)) {
  console.error("SESSION_SECRET musí mít v produkci alespoň 32 znaků.");
  process.exit(1);
}

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_SSL === "false" ? false : { rejectUnauthorized: false }
});

app.use(helmet({
  contentSecurityPolicy: false
}));
app.use(express.json({ limit: "256kb" }));
app.use(cookieSession({
  name: "kompas_session",
  keys: [process.env.SESSION_SECRET || "CHANGE_ME_BEFORE_DEPLOYMENT"],
  httpOnly: true,
  secure: process.env.NODE_ENV === "production",
  sameSite: "lax",
  maxAge: 1000 * 60 * 60 * 24 * 30
}));

const authLimiter = rateLimit({ windowMs: 15 * 60 * 1000, limit: 20 });
app.use("/api/login", authLimiter);
app.use("/api/register", authLimiter);

async function db(sql, params=[]) {
  const r = await pool.query(sql, params);
  return r.rows;
}

function requireLogin(req,res,next){
  if(!req.session?.householdId || !req.session?.memberId){
    return res.status(401).json({error:"Nepřihlášeno"});
  }
  next();
}

function cleanName(v){
  return String(v||"").trim().replace(/[.,!?;:"'()[\]{}<>\/\\@#$%^&*+=|~`]/g,"").replace(/\s+/g," ");
}

function cleanUsername(v){
  return cleanName(v).toLocaleLowerCase("cs-CZ");
}

async function init(){
  await db(`
    CREATE TABLE IF NOT EXISTS households(
      id UUID PRIMARY KEY,
      owner_email TEXT NOT NULL UNIQUE,
      household_name TEXT NOT NULL,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS members(
      id UUID PRIMARY KEY,
      household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE(household_id, name)
    );
    CREATE TABLE IF NOT EXISTS data(
      household_id UUID PRIMARY KEY REFERENCES households(id) ON DELETE CASCADE,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS history(
      id BIGSERIAL PRIMARY KEY,
      household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
      member_id UUID REFERENCES members(id) ON DELETE SET NULL,
      action TEXT NOT NULL,
      payload JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE IF NOT EXISTS backups(
      id BIGSERIAL PRIMARY KEY,
      household_id UUID NOT NULL REFERENCES households(id) ON DELETE CASCADE,
      payload JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS history_household_created_idx
      ON history(household_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS backups_household_created_idx
      ON backups(household_id, created_at DESC);
  `);
}

app.post("/api/register", async (req,res)=>{
  try{
    const email=String(req.body.email||"").trim().toLowerCase();
    const householdName=cleanName(req.body.householdName);
    const username=cleanUsername(req.body.username);
    const password=String(req.body.password||"");
    const firstMember=cleanName(req.body.firstMember||"");

    if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({error:"Zadejte platný e-mail."});
    if(!householdName || !username || !firstMember) return res.status(400).json({error:"Vyplňte všechny údaje."});
    if(password.length < 10) return res.status(400).json({error:"Heslo musí mít alespoň 10 znaků."});

    const exists=await db("SELECT 1 FROM households WHERE owner_email=$1 OR username=$2",[email,username]);
    if(exists.length) return res.status(409).json({error:"E-mail nebo uživatelské jméno už existuje."});

    const householdId=crypto.randomUUID();
    const memberId=crypto.randomUUID();
    const hash=await bcrypt.hash(password,12);

    await db("INSERT INTO households(id,owner_email,household_name,username,password_hash) VALUES($1,$2,$3,$4,$5)",
      [householdId,email,householdName,username,hash]);
    await db("INSERT INTO members(id,household_id,name) VALUES($1,$2,$3)",[memberId,householdId,firstMember]);
    await db("INSERT INTO data(household_id,payload) VALUES($1,$2)",[householdId,JSON.stringify({})]);

    req.session={householdId,memberId};
    res.json({ok:true, householdName, member:firstMember});
  }catch(e){
    console.error(e); res.status(500).json({error:"Účet se nepodařilo vytvořit."});
  }
});

app.post("/api/login", async (req,res)=>{
  try{
    const username=cleanUsername(req.body.username);
    const password=String(req.body.password||"");
    const memberName=cleanName(req.body.memberName);
    const rows=await db("SELECT * FROM households WHERE username=$1",[username]);
    if(!rows.length) return res.status(401).json({error:"Nesprávné přihlašovací údaje."});
    const h=rows[0];
    const ok=await bcrypt.compare(password,h.password_hash);
    if(!ok) return res.status(401).json({error:"Nesprávné přihlašovací údaje."});
    const ms=await db("SELECT * FROM members WHERE household_id=$1 AND name=$2",[h.id,memberName]);
    if(!ms.length) return res.status(401).json({error:"Tento člen v rodině není."});
    req.session={householdId:h.id,memberId:ms[0].id};
    res.json({ok:true, householdName:h.household_name, member:ms[0].name});
  }catch(e){ console.error(e); res.status(500).json({error:"Přihlášení se nepodařilo."}); }
});

app.post("/api/logout",(req,res)=>{ req.session=null; res.json({ok:true}); });

app.get("/api/me",requireLogin,async(req,res)=>{
  const h=await db("SELECT household_name,username,owner_email FROM households WHERE id=$1",[req.session.householdId]);
  const ms=await db("SELECT id,name FROM members WHERE household_id=$1 ORDER BY created_at",[req.session.householdId]);
  res.json({household:h[0],members:ms,currentMemberId:req.session.memberId});
});

app.post("/api/members",requireLogin,async(req,res)=>{
  try{
    const name=cleanName(req.body.name);
    if(!name) return res.status(400).json({error:"Zadejte jméno."});
    const count=await db("SELECT count(*)::int AS n FROM members WHERE household_id=$1",[req.session.householdId]);
    if(count[0].n>=20) return res.status(400).json({error:"Maximálně 20 členů."});
    const id=crypto.randomUUID();
    await db("INSERT INTO members(id,household_id,name) VALUES($1,$2,$3)",[id,req.session.householdId,name]);
    res.json({id,name});
  }catch(e){res.status(400).json({error:"Člena se nepodařilo přidat."});}
});

app.delete("/api/members/:id",requireLogin,async(req,res)=>{
  if(req.params.id===req.session.memberId) return res.status(400).json({error:"Nelze odebrat právě přihlášeného člena."});
  await db("DELETE FROM members WHERE id=$1 AND household_id=$2",[req.params.id,req.session.householdId]);
  res.json({ok:true});
});

app.post("/api/switch-member",requireLogin,async(req,res)=>{
  const ms=await db("SELECT id,name FROM members WHERE id=$1 AND household_id=$2",[req.body.memberId,req.session.householdId]);
  if(!ms.length)return res.status(400).json({error:"Člen neexistuje."});
  req.session.memberId=ms[0].id;
  res.json({ok:true,member:ms[0].name});
});

app.get("/api/data",requireLogin,async(req,res)=>{
  const rows=await db("SELECT payload,updated_at FROM data WHERE household_id=$1",[req.session.householdId]);
  res.json(rows[0]||{payload:{},updated_at:null});
});

app.get("/api/health",async(req,res)=>{
  try{await db("SELECT 1");res.json({ok:true});}
  catch(e){res.status(503).json({ok:false});}
});

app.put("/api/data",requireLogin,async(req,res)=>{
  const payload=req.body?.payload;
  if(payload===undefined || payload===null || typeof payload!=="object" || Array.isArray(payload)) return res.status(400).json({error:"Data nejsou ve správném tvaru."});
  const raw=JSON.stringify(payload);
  if(Buffer.byteLength(raw,"utf8")>200000) return res.status(413).json({error:"Data jsou příliš velká."});
  const client=await pool.connect();
  try{
    await client.query("BEGIN");
    const old=await client.query("SELECT payload FROM data WHERE household_id=$1 FOR UPDATE",[req.session.householdId]);
    const oldPayload=old.rows[0]?.payload||{};
    await client.query("INSERT INTO backups(household_id,payload) VALUES($1,$2)",[req.session.householdId,JSON.stringify(oldPayload)]);
    const historyInsert=await client.query("INSERT INTO history(household_id,member_id,action,payload) VALUES($1,$2,$3,$4) RETURNING id",[req.session.householdId,req.session.memberId,"změna dat",JSON.stringify({before:oldPayload,after:payload})]);
    const historyId=historyInsert.rows[0].id;
    await client.query("UPDATE data SET payload=$1,updated_at=now() WHERE household_id=$2",[raw,req.session.householdId]);
    await client.query("DELETE FROM history WHERE household_id=$1 AND id NOT IN (SELECT id FROM history WHERE household_id=$1 ORDER BY id DESC LIMIT 500)",[req.session.householdId]);
    await client.query("DELETE FROM backups WHERE household_id=$1 AND id NOT IN (SELECT id FROM backups WHERE household_id=$1 ORDER BY id DESC LIMIT 200)",[req.session.householdId]);
    await client.query("COMMIT");
    res.json({ok:true,historyId:String(historyId)});
  }catch(e){
    await client.query("ROLLBACK");console.error(e);res.status(500).json({error:"Data se nepodařilo bezpečně uložit."});
  }finally{client.release();}
});

app.get("/api/history",requireLogin,async(req,res)=>{
  const rows=await db(`
    SELECT h.id,h.action,h.created_at,m.name AS member
    FROM history h LEFT JOIN members m ON m.id=h.member_id
    WHERE h.household_id=$1 ORDER BY h.id DESC LIMIT 50
  `,[req.session.householdId]);
  res.json(rows);
});

app.post("/api/history/:id/restore",requireLogin,async(req,res)=>{
  const rows=await db("SELECT payload FROM history WHERE id=$1 AND household_id=$2",[req.params.id,req.session.householdId]);
  if(!rows.length)return res.status(404).json({error:"Historie nenalezena."});
  const before=rows[0].payload?.before;
  if(before===undefined)return res.status(400).json({error:"Tuto verzi nelze obnovit."});

  const current=await db("SELECT payload FROM data WHERE household_id=$1",[req.session.householdId]);
  await db("INSERT INTO backups(household_id,payload) VALUES($1,$2)",[req.session.householdId,JSON.stringify(current[0]?.payload||{})]);
  await db("UPDATE data SET payload=$1,updated_at=now() WHERE household_id=$2",[JSON.stringify(before),req.session.householdId]);
  await db("INSERT INTO history(household_id,member_id,action,payload) VALUES($1,$2,$3,$4)",
    [req.session.householdId,req.session.memberId,"obnovení starší verze",JSON.stringify({before:current[0]?.payload||{},after:before})]);
  res.json({ok:true});
});

app.use((req,res)=>res.sendFile(path.join(__dirname,"public","index.html")));

init().then(()=>{
  app.listen(PORT,()=>console.log(`Kompas server běží na portu ${PORT}`));
}).catch(err=>{console.error("Inicializace databáze selhala",err);process.exit(1);});
