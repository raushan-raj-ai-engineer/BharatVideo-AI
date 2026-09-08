from app.services.scene_planner import plan_story


def test_mock_planner_creates_editable_scenes():
    story = plan_story("A funny restaurant reel", 30, "hi-IN", "hinglish", "business_funny")
    assert len(story.scenes) >= 3
    assert story.provider == "mock"
    assert all(scene.duration_seconds >= 2 for scene in story.scenes)
    assert all("dialogue_turns" in scene.metadata for scene in story.scenes)


def test_mock_planner_longform_reaches_36_shot_shape():
    story = plan_story("Long Kanpuri cartoon", 480, "hi-IN", "kanpuriya", "kanpuri_comedy")
    assert len(story.scenes) == 36
