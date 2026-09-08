'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {apiFetch,token} from '../../lib/api';

type Plan={id:string;name:string;price_inr:number;credits:number;tagline:string;features:string[];popular?:boolean};

declare global { interface Window { Razorpay:any } }

async function ensureRazorpay(){
  if(window.Razorpay) return;
  await new Promise<void>((resolve,reject)=>{
    const existing=document.querySelector<HTMLScriptElement>('script[data-bv-razorpay="1"]');
    if(existing){existing.addEventListener('load',()=>resolve(),{once:true});existing.addEventListener('error',()=>reject(new Error('Razorpay Checkout failed to load')),{once:true});return}
    const s=document.createElement('script');
    s.dataset.bvRazorpay='1';
    s.src='https://checkout.razorpay.com/v1/checkout.js';
    s.onload=()=>resolve();
    s.onerror=()=>reject(new Error('Razorpay Checkout failed to load'));
    document.body.appendChild(s);
  });
}

export default function Pricing(){
  const[plans,setPlans]=useState<Plan[]>([]);
  const[mode,setMode]=useState('mock');
  const[msg,setMsg]=useState('');
  const[busy,setBusy]=useState('');
  useEffect(()=>{fetch((process.env.NEXT_PUBLIC_API_BASE_URL||'http://localhost:8000')+'/v1/billing/plans').then(r=>r.json()).then(x=>{setPlans(x.plans||[]);setMode(x.billing_mode||'mock')})},[]);

  async function buy(id:string){
    if(!token()){location.href='/login?next=/pricing';return}
    setBusy(id);setMsg('');
    try{
      const r=await apiFetch('/v1/billing/checkout',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({plan_id:id})});
      const b=await r.json();
      if(!r.ok)throw new Error(b.detail||JSON.stringify(b));
      if(b.mode==='mock'){
        const done=await apiFetch('/v1/billing/mock-complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order_id:b.order_id})});
        const d=await done.json();
        if(!done.ok)throw new Error(d.detail||JSON.stringify(d));
        setMsg(`Test checkout complete: ${d.credits_added} credits added. No real money charged.`);return;
      }
      if(b.mode==='razorpay'){
        await ensureRazorpay();
        const rz=new window.Razorpay({
          key:b.key_id,
          amount:b.amount,
          currency:'INR',
          name:'BharatVideo AI',
          description:`${b.plan.name} • ${b.plan.credits} credits`,
          order_id:b.provider_order_id,
          retry:{enabled:true},
          theme:{color:'#7c5cff'},
          handler:async(resp:any)=>{
            setMsg('Payment received. Verifying capture securely…');
            const vr=await apiFetch('/v1/billing/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order_id:b.order_id,razorpay_order_id:resp.razorpay_order_id,razorpay_payment_id:resp.razorpay_payment_id,razorpay_signature:resp.razorpay_signature})});
            const vb=await vr.json();
            if(vr.ok){
              setMsg(vb.status==='already_paid'?'Payment already processed safely.':`Payment captured and verified. ${vb.credits_added} credits added.`);
            }else if(vr.status===409){
              setMsg('Payment authorised. Waiting for capture confirmation; the Razorpay webhook will activate your plan automatically.');
            }else setMsg(`Error: ${vb.detail||'Payment verification failed'}`);
          },
          modal:{ondismiss:()=>setMsg('Checkout closed. No plan change was made unless payment was captured.')}
        });
        rz.on('payment.failed',(resp:any)=>setMsg(`Payment failed: ${resp?.error?.description||'Please retry with UPI, card or net banking.'}`));
        rz.open();
      }
    }catch(e){setMsg(`Error: ${e instanceof Error?e.message:String(e)}`)}finally{setBusy('')}
  }

  return <div>
    <div className="pricingHero"><span className="eyebrow">INDIA-FIRST PRICING</span><h1>Start free. Scale when your videos scale.</h1><p>One secure checkout for UPI Intent/QR, cards and net banking when Razorpay is enabled. Premium external video models remain opt-in.</p><div className={mode==='mock'?'testMode':'liveMode'}>{mode==='mock'?'TEST BILLING • no real money is charged':'RAZORPAY SECURE CHECKOUT • UPI • CARDS • NETBANKING'}</div></div>
    {msg&&<div className={msg.startsWith('Error')||msg.startsWith('Payment failed')?'errorBox':'successBox'}>{msg}</div>}
    <div className="pricingGrid">{plans.map(p=><article key={p.id} className={`priceCard ${p.popular?'popular':''}`}>{p.popular&&<span className="popularTag">MOST POPULAR</span>}<h3>{p.name}</h3><p>{p.tagline}</p><div className="price">{p.price_inr===0?'₹0':`₹${p.price_inr}`}<small>{p.price_inr?'/ 30-day credit pack':''}</small></div><b>{p.credits} credits</b><ul>{p.features.map(f=><li key={f}>✓ {f}</li>)}</ul>{p.id==='free'?<Link className="secondaryLink priceButton" href="/register">Start free</Link>:<button className="primaryButton priceButton" disabled={busy===p.id} onClick={()=>buy(p.id)}>{busy===p.id?'Opening secure checkout…':`Choose ${p.name}`}</button>}</article>)}</div>
    <div className="panel paymentTrust"><h3>Secure payment activation</h3><p>Credits are granted only after server verification confirms the Razorpay order/payment and captured status. Duplicate callbacks or webhooks cannot add credits twice.</p><div className="paymentMethodChips"><span>UPI Intent / QR</span><span>Debit & credit cards</span><span>Net banking</span></div></div>
    <p className="pricingNote">Paid plans are currently 30-day credit packs, not auto-renew subscriptions. Start with Razorpay Test keys, configure the webhook, then switch to Live keys after your Razorpay account is ready.</p>
  </div>
}
