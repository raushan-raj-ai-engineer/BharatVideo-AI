from app.db.session import SessionLocal
from app.models import Project, Scene
from app.services.engine_plan import project_to_agentic_plan


def test_v08_comedy_plan_uses_adaptive_non_fixed_transitions():
    db = SessionLocal()
    try:
        project = Project(
            title='Continuity QA', prompt='Babuji hears a female AI voice on the phone',
            style='kanpuri_comedy', duration_seconds=30, estimated_credits=1,
        )
        db.add(project); db.commit(); db.refresh(project)
        scenes=[]
        for idx, action in enumerate(['mock_shock','snatch_phone','whisper']):
            scene=Scene(
                project_id=project.id, order_index=idx, duration_seconds=6.5,
                dialogue=f'लाइन {idx+1}', visual_prompt='AI phone courtyard', generation_mode='BLENDER_3D',
                metadata_json={
                    'location_id':'courtyard', 'beat':'scene', 'visual_action':action,
                    'dialogue_turns':[{'speaker':['babuji','guddu','bittu'][idx], 'text':f'का बे लाइन {idx+1}?', 'emotion':'confused', 'pose':'idle'}],
                    'props':['ai_phone'],
                },
            )
            db.add(scene); db.commit(); db.refresh(scene); scenes.append(scene)
        plan=project_to_agentic_plan(project, scenes)
    finally:
        db.close()
    assert plan['story_engine']['source']=='bharatvideo_ai_mvp_v0_8'
    assert plan['story_engine']['adaptive_scene_timing_v08'] is True
    assert plan['story_engine']['j_l_cut_audio_v08'] is True
    assert plan['characters']==['babuji','guddu','bittu']
    pauses=[s['dialogue'][-1]['pause_after_seconds'] for s in plan['scenes']]
    assert len(set(pauses)) > 1, pauses
    assert all(0.02 <= p <= 0.40 for p in pauses)
    assert all(s['timing_mode']=='adaptive_dialogue_v08' for s in plan['scenes'])
    assert plan['scenes'][0]['transition_after'] in {'punchline_hold','reaction_hold','continuous_dialogue'}
    assert any(s['j_cut_seconds'] > 0 for s in plan['scenes'][:-1])


def test_v08_continuous_dialogue_jcut_is_small_not_fixed_scene_silence():
    db=SessionLocal()
    try:
        project=Project(title='Fast banter',prompt='family banter',style='kanpuri_comedy',duration_seconds=20,estimated_credits=1)
        db.add(project);db.commit();db.refresh(project)
        scenes=[]
        for idx in range(2):
            sc=Scene(project_id=project.id,order_index=idx,duration_seconds=6.5,dialogue='banter',visual_prompt='courtyard',generation_mode='BLENDER_3D',metadata_json={'location_id':'courtyard','beat':'dialogue','visual_action':'dialogue','dialogue_turns':[{'speaker':'babuji' if idx==0 else 'guddu','text':'अरे सुनौ बे','emotion':'neutral','pose':'idle'}]})
            db.add(sc);db.commit();db.refresh(sc);scenes.append(sc)
        plan=project_to_agentic_plan(project,scenes)
    finally: db.close()
    first=plan['scenes'][0]
    assert first['transition_after']=='continuous_dialogue'
    assert 0.03 <= first['transition_pause_seconds'] <= 0.10
    assert 0.07 <= first['j_cut_seconds'] <= 0.15
