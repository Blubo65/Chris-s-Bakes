// Cloudflare Worker for Chidsey Chowdown photo uploads.
// Bind R2 bucket "chidsey-recipe-photos" as PHOTO_BUCKET in Worker settings.
// Set SUPABASE_PUBLISHABLE_KEY as a Worker secret (the site's public Supabase key).
const ORIGIN = 'https://chidseychowdown.co.uk';
const SUPABASE = 'https://vjqffpdggasgtgnxtktj.supabase.co';
const OWNER_ID = '127e4f28-83e6-4a91-a786-bdb51a965830';
const PUBLIC_IMAGES = 'https://images.chidseychowdown.co.uk';
const cors = {'Access-Control-Allow-Origin':ORIGIN,'Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type','Vary':'Origin'};
function json(body,status=200){return new Response(JSON.stringify(body),{status,headers:{...cors,'Content-Type':'application/json','Cache-Control':'no-store'}});}
export default {
 async fetch(request,env){
  if(request.headers.get('Origin')!==ORIGIN)return json({error:'Origin not allowed'},403);
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
  if(request.method!=='POST')return json({error:'Method not allowed'},405);
  if(!env.PHOTO_BUCKET||!env.SUPABASE_PUBLISHABLE_KEY)return json({error:'Worker not configured'},503);
  const auth=request.headers.get('Authorization')||'';
  if(!/^Bearer\s+\S+$/.test(auth))return json({error:'Sign in required'},401);
  const userResponse=await fetch(SUPABASE+'/auth/v1/user',{headers:{'Authorization':auth,'apikey':env.SUPABASE_PUBLISHABLE_KEY}});
  if(!userResponse.ok)return json({error:'Invalid session'},401);
  const user=await userResponse.json();
  if(user.id!==OWNER_ID)return json({error:'Not authorised'},403);
  const contentType=(request.headers.get('Content-Type')||'').split(';')[0].toLowerCase();
  if(contentType!=='image/jpeg')return json({error:'Only JPEG photographs accepted'},415);
  const size=Number(request.headers.get('Content-Length')||0);
  if(size>5*1024*1024)return json({error:'Photograph is too large'},413);
  const bytes=await request.arrayBuffer();
  if(bytes.byteLength===0||bytes.byteLength>5*1024*1024)return json({error:'Invalid photograph size'},413);
  const head=new Uint8Array(bytes.slice(0,3));
  if(head[0]!==255||head[1]!==216||head[2]!==255)return json({error:'Invalid JPEG file'},415);
  const key=OWNER_ID+'/'+crypto.randomUUID()+'.jpg';
  await env.PHOTO_BUCKET.put(key,bytes,{httpMetadata:{contentType:'image/jpeg',cacheControl:'public, max-age=31536000'}});
  return json({url:PUBLIC_IMAGES+'/'+key});
 }
};