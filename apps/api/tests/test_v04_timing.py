from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_project():
    r = client.post('/v1/projects', json={
        'title':'Timing Test','prompt':'Babuji and Guddu argue about an AI machine in funny Kanpuriya Hindi.',
        'platform':'instagram_reel','language':'hi-IN','dialect':'kanpuriya','style':'kanpuri_comedy',
        'duration_seconds':30,'aspect_ratio':'9:16','quality':'balanced'
    })
    assert r.status_code == 201
    return r.json()['id']


def test_v04_health_and_providers():
    h=client.get('/health'); assert h.status_code==200; assert h.json()['version']=='0.8.0'
    p=client.get('/v1/providers'); assert p.status_code==200; assert 'story' in p.json(); assert 'video' in p.json()


def test_timing_report_and_autofit():
    from app.db.session import SessionLocal
    db_session = SessionLocal()
    from app.models import Project, Scene
    p=Project(title='Timing',prompt='test timing project',duration_seconds=30,estimated_credits=1)
    db_session.add(p); db_session.commit(); db_session.refresh(p)
    long_text='का बे Guddua, ई मशीनवा इतना भौकाल काहे काट रही है, हमका पूरा हिसाब अभी बताय द्यो.'
    s=Scene(project_id=p.id,order_index=0,duration_seconds=3.0,dialogue=long_text,visual_prompt='courtyard',generation_mode='BLENDER_3D',metadata_json={'dialogue_turns':[{'speaker':'babuji','text':long_text}]})
    db_session.add(s); db_session.commit()
    r=client.get(f'/v1/projects/{p.id}/timing'); assert r.status_code==200
    body=r.json(); assert body['status']=='RISK'; assert body['scenes'][0]['recommended_seconds']>3.0
    f=client.post(f'/v1/projects/{p.id}/autofit-timing'); assert f.status_code==200; assert f.json()['changed']
    r2=client.get(f'/v1/projects/{p.id}/timing'); assert r2.json()['status']=='OK'
    db_session.close()
