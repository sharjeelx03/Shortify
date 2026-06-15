import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.providers import parse_ai_json, validate_clip_payload, build_prompt
from app.core.pipeline import extract_video_id, safe_filename, unique_output_path


class ProviderParsingTests(unittest.TestCase):
    def test_parse_ai_json_from_markdown_block(self):
        raw = '```json\n{"clips":[{"title":"A","start_seconds":1,"end_seconds":9}]}\n```'
        clips = parse_ai_json(raw)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]["title"], "A")

    def test_validate_clip_payload_repairs_end_time(self):
        clips = [{"title":"Short title", "hook":"Hook", "start_seconds":10, "end_seconds":5}]
        valid = validate_clip_payload(clips, 1, [8])
        self.assertEqual(valid[0]["title"], "Moment 1")
        self.assertEqual(valid[0]["end_seconds"], 18)

    def test_build_prompt_uses_transcript_limit_setting(self):
        prompt = build_prompt("a" * 100, 1, [8], {"transcript_char_limit": 3000})
        self.assertIn("first 3000 characters", prompt)
        self.assertIn("a" * 40, prompt)


class PipelineHelperTests(unittest.TestCase):
    def test_extract_video_id(self):
        self.assertEqual(extract_video_id("https://youtu.be/xcNdWUyqN2s"), "xcNdWUyqN2s")
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=xcNdWUyqN2s"), "xcNdWUyqN2s")

    def test_safe_filename(self):
        self.assertEqual(safe_filename("Hello: World!"), "hello_world")

    def test_unique_output_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "shortify_video_1.mp4"
            path.write_text("exists")
            self.assertEqual(unique_output_path(path).name, "shortify_video_1_2.mp4")


if __name__ == "__main__":
    unittest.main()
