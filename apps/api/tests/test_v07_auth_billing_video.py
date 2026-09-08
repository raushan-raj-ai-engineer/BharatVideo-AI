from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models import CreditLedger, Project, ProjectOwner, Scene, User
from app.services.engine_plan import project_to_agentic_plan

client=TestClient(app)

def register(email='creator@example.com'):
    r=client.post('/v1/auth/register',json={'name':'Rohit Creator','email':email,'password':'strongpass123'})
    assert r.status_code in (201,409)
    if r.status_code==409:
        r=client.post('/v1/auth/login',json={'email':email,'password':'strongpass123'})
    assert r.status_code==200 or r.status_code==201
    return r.json()


def test_register_login_me_and_signup_credits():
    body=register('authv07@example.com')
    token=body['token']
    assert body['user']['credits']>=30
    me=client.get('/v1/auth/me',headers={'Authorization':f'Bearer {token}'})
    assert me.status_code==200
    assert me.json()['email']=='authv07@example.com'


def test_pricing_and_mock_checkout_adds_credits():
    body=register('billingv07@example.com'); token=body['token']; h={'Authorization':f'Bearer {token}'}
    p=client.get('/v1/billing/plans'); assert p.status_code==200
    assert any(x['id']=='creator' and x['price_inr']==299 for x in p.json()['plans'])
    before=client.get('/v1/billing/account',headers=h).json()['credits']
    order=client.post('/v1/billing/checkout',headers={**h,'Content-Type':'application/json'},json={'plan_id':'creator'})
    assert order.status_code==200 and order.json()['mode']=='mock'
    done=client.post('/v1/billing/mock-complete',headers={**h,'Content-Type':'application/json'},json={'order_id':order.json()['order_id']})
    assert done.status_code==200 and done.json()['credits_added']==250
    after=client.get('/v1/billing/account',headers=h).json()['credits']
    assert after-before==250


def test_project_is_account_scoped():
    a=register('owner-a@example.com'); b=register('owner-b@example.com')
    ha={'Authorization':f"Bearer {a['token']}",'Content-Type':'application/json'}
    hb={'Authorization':f"Bearer {b['token']}"}
    r=client.post('/v1/projects',headers=ha,json={'title':'Private Project','prompt':'private video project','duration_seconds':30})
    assert r.status_code==201
    pid=r.json()['id']
    other=client.get(f'/v1/projects/{pid}',headers=hb)
    assert other.status_code==404


def test_engine_plan_locks_comedy_cast_and_story_prop():
    db=SessionLocal()
    try:
        p=Project(title='AI Bahu',prompt='Babuji hears AI on a phone',style='kanpuri_comedy',duration_seconds=30,estimated_credits=1)
        db.add(p);db.commit();db.refresh(p)
        s=Scene(project_id=p.id,order_index=0,duration_seconds=6,dialogue='Babuji: का बे?',visual_prompt='AI phone in courtyard',generation_mode='BLENDER_3D',metadata_json={'dialogue_turns':[{'speaker':'babuji','text':'का बे?','emotion':'shock','pose':'pointing'}],'visual_characters':['babuji','guddu','bittu'],'props':['ai_phone'],'visual_action':'prop_reveal_and_recoil','blocking':[{'character':'babuji','action':'recoil','strength':1.0}],'expression_beats':[{'character':'babuji','emotion':'shock','at':0.2}],'lip_sync_mode':'viseme_ready_v07','story_prop_required':True})
        db.add(s);db.commit();db.refresh(s)
        plan=project_to_agentic_plan(p,[s])
    finally:db.close()
    scene=plan['scenes'][0]
    assert scene['visual_characters']==['babuji','guddu','bittu']
    assert 'ai_phone' in scene['props']
    assert scene['visual_action']=='mock_shock'
    assert plan['story_engine']['three_character_comedy_lock'] is True
