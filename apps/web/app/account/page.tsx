'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {apiFetch,logout} from '../../lib/api';

function money(paise:number){return `₹${(Number(paise||0)/100).toLocaleString('en-IN',{minimumFractionDigits:0,maximumFractionDigits:2})}`}

export default function Account(){
  const[data,setData]=useState<any>(null);const[err,setErr]=useState('');
  useEffect(()=>{apiFetch('/v1/billing/account').then(async r=>{const b=await r.json();if(!r.ok)throw new Error(b.detail);setData(b)}).catch(e=>setErr(String(e)))},[]);
  if(err)return <div className="errorBox">{err}</div>;
  if(!data)return <div className="panel">Loading account…</div>;
  return <>
    <div className="accountHero"><div><span className="eyebrow">ACCOUNT</span><h1>{data.user.name}</h1><p>{data.user.email}</p></div><div className="accountCredits"><strong>{data.credits}</strong><span>credits</span><small>{data.user.plan_id.toUpperCase()} plan</small></div></div>
    <div className="twoCol"><section className="panel"><div className="panelTitle"><h2>Credit activity</h2></div><div className="ledgerList">{data.ledger.map((x:any)=><div key={x.id}><span><b>{x.description}</b><small>{x.kind}</small></span><strong className={x.amount>=0?'green':'red'}>{x.amount>0?'+':''}{x.amount}</strong></div>)}</div></section><section className="panel"><h2>Plan</h2><p className="lead">Upgrade when you need more renders or long-form production.</p><Link className="primaryLink" href="/pricing">View pricing</Link><button className="secondaryButton logoutBtn" onClick={logout}>Log out</button></section></div>
    <section className="panel paymentHistory"><div className="panelTitle"><div><span className="eyebrow">PAYMENTS</span><h2>Payment history</h2></div><Link href="/pricing" className="secondaryLink">Buy credits</Link></div>{(data.payments||[]).length===0?<p className="lead">No Razorpay payment attempts yet.</p>:<div className="paymentRows">{data.payments.map((x:any)=><div className="paymentRow" key={x.id}><div><b>{money(x.amount_paise)}</b><small>{(x.method||'payment').toUpperCase()} • {x.provider_payment_id||'pending id'}</small></div><span className={`paymentStatus ${x.status}`}>{x.status}</span></div>)}</div>}</section>
  </>
}
