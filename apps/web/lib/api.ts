export const API=process.env.NEXT_PUBLIC_API_BASE_URL||'http://localhost:8000';

export function token(){
  if(typeof window==='undefined') return '';
  return localStorage.getItem('bv_token')||'';
}
export function authHeaders(extra:Record<string,string>={}){
  const t=token();
  return {...(t?{Authorization:`Bearer ${t}`} : {}),...extra};
}
export async function apiFetch(path:string, init:RequestInit={}){
  const headers={...authHeaders(),...(init.headers||{})} as Record<string,string>;
  const r=await fetch(`${API}${path}`,{...init,headers,cache:'no-store'});
  if(r.status===401 && typeof window!=='undefined' && !location.pathname.startsWith('/login') && !location.pathname.startsWith('/register')){
    localStorage.removeItem('bv_token'); localStorage.removeItem('bv_user');
    location.href='/login?next='+encodeURIComponent(location.pathname);
  }
  return r;
}
export function saveAuth(body:any){
  localStorage.setItem('bv_token',body.token);
  localStorage.setItem('bv_user',JSON.stringify(body.user));
}
export function logout(){localStorage.removeItem('bv_token');localStorage.removeItem('bv_user');location.href='/login'}
